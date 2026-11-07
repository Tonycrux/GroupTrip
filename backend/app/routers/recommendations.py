from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app import schemas
from app.db import get_session
from app.engine.aggregation import aggregate
from app.engine.conflicts import Conflict as EngineConflict
from app.engine.conflicts import detect_conflicts
from app.engine.scoring import MemberProfile, ScoredMember, profile_from_fields, score_member
from app.enums import RankingStrategy
from app.explain.base import ExplanationContext
from app.explain.llm import get_explainer
from app.models import Condition, Destination, Member, ProfileField, Rating, Trip, Veto

router = APIRouter(tags=["recommendations"])


@dataclass
class ScoredDestination:
    destination: Destination
    member_scores: list[ScoredMember]
    group_score: float
    conflicts: list[EngineConflict]
    vetoed_by: list[int]


def _grouped_by_member(rows) -> dict[int, list]:
    grouped: dict[int, list] = {}
    for row in rows:
        grouped.setdefault(row.member_id, []).append(row)
    return grouped


def score_destinations(
    session: Session, trip: Trip, strategy: RankingStrategy
) -> list[ScoredDestination]:
    members = list(session.exec(select(Member).where(Member.trip_id == trip.id)).all())
    member_ids = [m.id for m in members]
    names = {m.id: m.name for m in members}

    profiles: dict[int, MemberProfile] = {mid: MemberProfile() for mid in member_ids}
    ratings: dict[tuple[int, int], Rating] = {}
    vetoes: dict[int, list[int]] = {}

    if member_ids:
        fields = session.exec(
            select(ProfileField).where(ProfileField.member_id.in_(member_ids))
        ).all()
        grouped_fields = _grouped_by_member(fields)
        profiles = {
            mid: profile_from_fields(grouped_fields.get(mid, [])) for mid in member_ids
        }

        for rating in session.exec(
            select(Rating).where(Rating.member_id.in_(member_ids))
        ).all():
            if rating.destination_id is not None:
                ratings[(rating.member_id, rating.destination_id)] = rating

        for veto in session.exec(select(Veto).where(Veto.member_id.in_(member_ids))).all():
            vetoes.setdefault(veto.destination_id, []).append(veto.member_id)

    conditions = _grouped_by_member(
        session.exec(select(Condition).where(Condition.trip_id == trip.id)).all()
    )

    results: list[ScoredDestination] = []
    for dest in session.exec(select(Destination)).all():
        scored = [
            score_member(
                member.id,
                member.name,
                profiles[member.id],
                conditions.get(member.id, []),
                dest,
                ratings.get((member.id, dest.id)),
            )
            for member in members
        ]
        conflicts = detect_conflicts(profiles, names, dest, scored)
        group_score = aggregate([s.score for s in scored], strategy)
        vetoed_by = vetoes.get(dest.id, [])
        if vetoed_by:
            who = ", ".join(names.get(i, f"member {i}") for i in vetoed_by)
            conflicts.append(
                EngineConflict(kind="veto", member_ids=vetoed_by, summary=f"{who} vetoed this destination", severity=1.0)
            )
            group_score = 0.0
        results.append(
            ScoredDestination(
                destination=dest,
                member_scores=scored,
                group_score=round(group_score, 1),
                conflicts=conflicts,
                vetoed_by=vetoed_by,
            )
        )

    results.sort(key=lambda r: r.group_score, reverse=True)
    return results


def _to_schema(scored: ScoredDestination, strategy: RankingStrategy) -> schemas.DestinationRecommendation:
    ctx = ExplanationContext(
        destination=scored.destination,
        strategy=strategy,
        group_score=scored.group_score,
        member_scores=scored.member_scores,
        conflicts=scored.conflicts,
    )
    return schemas.DestinationRecommendation(
        destination=schemas.DestinationRead.model_validate(scored.destination),
        group_score=scored.group_score,
        strategy=strategy,
        member_scores=[
            schemas.MemberScore(
                member_id=s.member_id,
                member_name=s.member_name,
                score=s.score,
                hard_violations=s.hard_violations,
                reasons=s.reasons,
            )
            for s in scored.member_scores
        ],
        conflicts=[
            schemas.Conflict(
                kind=c.kind, member_ids=c.member_ids, summary=c.summary, severity=c.severity
            )
            for c in scored.conflicts
        ],
        vetoed_by=scored.vetoed_by,
        explanation=get_explainer().explain(ctx),
    )


def _trip_or_404(session: Session, trip_id: int) -> Trip:
    trip = session.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="trip not found")
    return trip


@router.get(
    "/trips/{trip_id}/recommendations",
    response_model=list[schemas.DestinationRecommendation],
)
def get_recommendations(
    trip_id: int,
    strategy: RankingStrategy | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[schemas.DestinationRecommendation]:
    trip = _trip_or_404(session, trip_id)
    chosen = strategy or RankingStrategy(trip.ranking_strategy)
    return [_to_schema(sd, chosen) for sd in score_destinations(session, trip, chosen)]


@router.get(
    "/trips/{trip_id}/recommendations/{destination_id}",
    response_model=schemas.DestinationRecommendation,
)
def get_recommendation(
    trip_id: int,
    destination_id: int,
    strategy: RankingStrategy | None = Query(default=None),
    session: Session = Depends(get_session),
) -> schemas.DestinationRecommendation:
    trip = _trip_or_404(session, trip_id)
    chosen = strategy or RankingStrategy(trip.ranking_strategy)
    for sd in score_destinations(session, trip, chosen):
        if sd.destination.id == destination_id:
            return _to_schema(sd, chosen)
    raise HTTPException(status_code=404, detail="destination not found")

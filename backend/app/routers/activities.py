from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db import get_session
from app.engine.activity_scoring import detect_activity_conflicts, score_activity
from app.engine.scoring import MemberProfile, profile_from_fields
from app.models import Activity, Condition, Destination, Member, ProfileField, Rating, Trip
from app.schemas import ActivityRead, ActivityScoreRead, Conflict, MemberScore

router = APIRouter(tags=["activities"])


@router.get("/destinations/{destination_id}/activities", response_model=list[ActivityRead])
def list_activities(
    destination_id: int, session: Session = Depends(get_session)
) -> list[Activity]:
    if session.get(Destination, destination_id) is None:
        raise HTTPException(status_code=404, detail="destination not found")
    return list(
        session.exec(select(Activity).where(Activity.destination_id == destination_id)).all()
    )


@router.get("/activities/{activity_id}", response_model=ActivityRead)
def get_activity(activity_id: int, session: Session = Depends(get_session)) -> Activity:
    activity = session.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="activity not found")
    return activity


@router.get("/trips/{trip_id}/activities", response_model=list[ActivityScoreRead])
def trip_activities(
    trip_id: int,
    destination_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[ActivityScoreRead]:
    """Every activity at the chosen destination, scored for each member."""
    trip = session.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="trip not found")

    chosen = destination_id if destination_id is not None else trip.selected_destination_id
    if chosen is None:
        raise HTTPException(status_code=400, detail="select a destination first")

    activities = list(
        session.exec(select(Activity).where(Activity.destination_id == chosen)).all()
    )
    members = list(session.exec(select(Member).where(Member.trip_id == trip_id)).all())
    member_ids = [m.id for m in members]

    profiles: dict[int, MemberProfile] = {}
    ratings: dict[tuple[int, int], Rating] = {}
    if member_ids:
        fields = session.exec(
            select(ProfileField).where(ProfileField.member_id.in_(member_ids))
        ).all()
        grouped: dict[int, list[ProfileField]] = {}
        for item in fields:
            grouped.setdefault(item.member_id, []).append(item)
        profiles = {mid: profile_from_fields(grouped.get(mid, [])) for mid in member_ids}

        for rating in session.exec(
            select(Rating).where(Rating.member_id.in_(member_ids))
        ).all():
            if rating.activity_id is not None:
                ratings[(rating.member_id, rating.activity_id)] = rating

    conditions_by_member: dict[int, list[Condition]] = {}
    for condition in session.exec(
        select(Condition).where(Condition.trip_id == trip_id)
    ).all():
        conditions_by_member.setdefault(condition.member_id, []).append(condition)

    names = {m.id: m.name for m in members}

    results: list[ActivityScoreRead] = []
    for act in activities:
        scored = [
            score_activity(
                m.id, m.name, profiles[m.id], act, ratings.get((m.id, act.id))
            )
            for m in members
        ]
        group = round(sum(s.score for s in scored) / len(scored), 1) if scored else 0.0
        rejected_by = [
            s.member_id
            for s in scored
            if ratings.get((s.member_id, act.id)) is not None
            and ratings[(s.member_id, act.id)].value == "not_interested"
        ]
        conflicts = detect_activity_conflicts(
            scored, act, profiles, conditions_by_member, names
        )
        results.append(
            ActivityScoreRead(
                activity=ActivityRead.model_validate(act),
                member_scores=[
                    MemberScore(
                        member_id=s.member_id,
                        member_name=s.member_name,
                        score=s.score,
                        hard_violations=s.hard_violations,
                        reasons=s.reasons,
                    )
                    for s in scored
                ],
                group_score=group,
                rejected_by=rejected_by,
                conflicts=[
                    Conflict(
                        kind=c.kind,
                        member_ids=c.member_ids,
                        summary=c.summary,
                        severity=c.severity,
                    )
                    for c in conflicts
                ],
            )
        )

    results.sort(key=lambda r: r.group_score, reverse=True)
    return results

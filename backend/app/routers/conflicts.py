from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db import get_session
from app.enums import ConflictStatus, RankingStrategy
from app.models import Conflict as ConflictRow
from app.models import Trip
from app.routers.recommendations import score_destinations
from app.schemas import ConflictRead

router = APIRouter(tags=["conflicts"])


@router.get("/trips/{trip_id}/conflicts", response_model=list[ConflictRead])
def list_conflicts(trip_id: int, session: Session = Depends(get_session)) -> list[ConflictRow]:
    if session.get(Trip, trip_id) is None:
        raise HTTPException(status_code=404, detail="trip not found")
    return list(
        session.exec(select(ConflictRow).where(ConflictRow.trip_id == trip_id)).all()
    )


@router.post("/trips/{trip_id}/conflicts/detect", response_model=list[ConflictRead])
def detect_conflicts(
    trip_id: int,
    strategy: RankingStrategy | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[ConflictRow]:
    trip = session.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="trip not found")
    chosen = strategy or RankingStrategy(trip.ranking_strategy)

    for existing in session.exec(
        select(ConflictRow).where(ConflictRow.trip_id == trip_id)
    ).all():
        session.delete(existing)
    session.commit()

    created: list[ConflictRow] = []
    for scored in score_destinations(session, trip, chosen):
        for conflict in scored.conflicts:
            row = ConflictRow(
                trip_id=trip_id,
                destination_id=scored.destination.id,
                kind=conflict.kind,
                member_ids=conflict.member_ids,
                summary=conflict.summary,
                severity=conflict.severity,
            )
            session.add(row)
            created.append(row)
    session.commit()
    for row in created:
        session.refresh(row)
    return created


@router.patch("/conflicts/{conflict_id}", response_model=ConflictRead)
def update_conflict_status(
    conflict_id: int,
    status: ConflictStatus,
    session: Session = Depends(get_session),
) -> ConflictRow:
    conflict = session.get(ConflictRow, conflict_id)
    if conflict is None:
        raise HTTPException(status_code=404, detail="conflict not found")
    conflict.status = status.value
    session.add(conflict)
    session.commit()
    session.refresh(conflict)
    return conflict

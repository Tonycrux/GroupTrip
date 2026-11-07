from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import RevisionLog, Trip
from app.schemas import RevisionCreate, RevisionRead

router = APIRouter(tags=["revisions"])


@router.post("/trips/{trip_id}/revisions", response_model=RevisionRead, status_code=201)
def create_revision(
    trip_id: int, payload: RevisionCreate, session: Session = Depends(get_session)
) -> RevisionLog:
    if session.get(Trip, trip_id) is None:
        raise HTTPException(status_code=404, detail="trip not found")
    data = payload.model_dump()
    data["change_type"] = payload.change_type.value
    revision = RevisionLog(trip_id=trip_id, **data)
    session.add(revision)
    session.commit()
    session.refresh(revision)
    return revision


@router.get("/trips/{trip_id}/revisions", response_model=list[RevisionRead])
def list_revisions(
    trip_id: int, session: Session = Depends(get_session)
) -> list[RevisionLog]:
    return list(
        session.exec(select(RevisionLog).where(RevisionLog.trip_id == trip_id)).all()
    )

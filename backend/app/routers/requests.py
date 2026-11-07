from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import ActivityRequest, Member, Trip
from app.schemas import ActivityRequestCreate, ActivityRequestRead, ActivityRequestUpdate

router = APIRouter(tags=["requests"])


@router.post("/trips/{trip_id}/requests", response_model=ActivityRequestRead, status_code=201)
def create_request(
    trip_id: int, payload: ActivityRequestCreate, session: Session = Depends(get_session)
) -> ActivityRequest:
    if session.get(Trip, trip_id) is None:
        raise HTTPException(status_code=404, detail="trip not found")
    member = session.get(Member, payload.member_id)
    if member is None or member.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="member not found in trip")
    request = ActivityRequest(trip_id=trip_id, **payload.model_dump())
    session.add(request)
    session.commit()
    session.refresh(request)
    return request


@router.get("/trips/{trip_id}/requests", response_model=list[ActivityRequestRead])
def list_requests(
    trip_id: int, session: Session = Depends(get_session)
) -> list[ActivityRequest]:
    if session.get(Trip, trip_id) is None:
        raise HTTPException(status_code=404, detail="trip not found")
    return list(
        session.exec(select(ActivityRequest).where(ActivityRequest.trip_id == trip_id)).all()
    )


@router.patch("/requests/{request_id}", response_model=ActivityRequestRead)
def update_request(
    request_id: int,
    payload: ActivityRequestUpdate,
    session: Session = Depends(get_session),
) -> ActivityRequest:
    request = session.get(ActivityRequest, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="request not found")
    request.status = payload.status.value
    session.add(request)
    session.commit()
    session.refresh(request)
    return request

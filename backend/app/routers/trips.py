from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session, select

from app.db import get_session
from app.models import Trip
from app.schemas import TripCreate, TripRead, TripUpdate

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("", response_model=TripRead, status_code=201)
def create_trip(payload: TripCreate, session: Session = Depends(get_session)) -> Trip:
    trip = Trip(**payload.model_dump())
    session.add(trip)
    session.commit()
    session.refresh(trip)
    return trip


@router.get("", response_model=list[TripRead])
def list_trips(session: Session = Depends(get_session)) -> list[Trip]:
    return list(session.exec(select(Trip)).all())


@router.get("/{trip_id}", response_model=TripRead)
def get_trip(trip_id: int, session: Session = Depends(get_session)) -> Trip:
    trip = session.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="trip not found")
    return trip


@router.patch("/{trip_id}", response_model=TripRead)
def update_trip(
    trip_id: int, payload: TripUpdate, session: Session = Depends(get_session)
) -> Trip:
    trip = session.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="trip not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(trip, key, value)
    session.add(trip)
    session.commit()
    session.refresh(trip)
    return trip


@router.delete("/{trip_id}", status_code=204)
def delete_trip(trip_id: int, session: Session = Depends(get_session)) -> Response:
    trip = session.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="trip not found")
    session.delete(trip)
    session.commit()
    return Response(status_code=204)

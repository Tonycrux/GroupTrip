from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session, select

from app.db import get_session
from app.models import Member, Trip
from app.schemas import MemberCreate, MemberRead

router = APIRouter(tags=["members"])


@router.post("/trips/{trip_id}/members", response_model=MemberRead, status_code=201)
def add_member(
    trip_id: int, payload: MemberCreate, session: Session = Depends(get_session)
) -> Member:
    if session.get(Trip, trip_id) is None:
        raise HTTPException(status_code=404, detail="trip not found")
    member = Member(trip_id=trip_id, **payload.model_dump())
    session.add(member)
    session.commit()
    session.refresh(member)
    return member


@router.get("/trips/{trip_id}/members", response_model=list[MemberRead])
def list_members(trip_id: int, session: Session = Depends(get_session)) -> list[Member]:
    return list(session.exec(select(Member).where(Member.trip_id == trip_id)).all())


@router.get("/members/{member_id}", response_model=MemberRead)
def get_member(member_id: int, session: Session = Depends(get_session)) -> Member:
    member = session.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="member not found")
    return member


@router.delete("/members/{member_id}", status_code=204)
def delete_member(member_id: int, session: Session = Depends(get_session)) -> Response:
    member = session.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="member not found")
    session.delete(member)
    session.commit()
    return Response(status_code=204)

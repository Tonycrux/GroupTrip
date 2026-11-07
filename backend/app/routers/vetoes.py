from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session, select

from app.db import get_session
from app.models import Member, Trip, Veto
from app.schemas import VetoCreate, VetoRead

router = APIRouter(tags=["vetoes"])


@router.post("/trips/{trip_id}/vetoes", response_model=VetoRead, status_code=201)
def create_veto(
    trip_id: int, payload: VetoCreate, session: Session = Depends(get_session)
) -> Veto:
    if session.get(Trip, trip_id) is None:
        raise HTTPException(status_code=404, detail="trip not found")
    member = session.get(Member, payload.member_id)
    if member is None or member.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="member not found in trip")

    existing = session.exec(
        select(Veto)
        .where(Veto.member_id == payload.member_id)
        .where(Veto.destination_id == payload.destination_id)
    ).first()
    if existing is not None:
        return existing

    veto = Veto(**payload.model_dump())
    session.add(veto)
    session.commit()
    session.refresh(veto)
    return veto


@router.get("/trips/{trip_id}/vetoes", response_model=list[VetoRead])
def list_vetoes(trip_id: int, session: Session = Depends(get_session)) -> list[Veto]:
    if session.get(Trip, trip_id) is None:
        raise HTTPException(status_code=404, detail="trip not found")
    member_ids = [
        m.id for m in session.exec(select(Member).where(Member.trip_id == trip_id)).all()
    ]
    if not member_ids:
        return []
    return list(session.exec(select(Veto).where(Veto.member_id.in_(member_ids))).all())


@router.delete("/vetoes/{veto_id}", status_code=204)
def delete_veto(veto_id: int, session: Session = Depends(get_session)) -> Response:
    veto = session.get(Veto, veto_id)
    if veto is None:
        raise HTTPException(status_code=404, detail="veto not found")
    session.delete(veto)
    session.commit()
    return Response(status_code=204)

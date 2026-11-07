from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session, select

from app.db import get_session
from app.deps import acting_member_id
from app.models import Condition, Member, Trip
from app.schemas import ConditionCreate, ConditionRead, ConditionUpdate

router = APIRouter(tags=["conditions"])


def _condition_or_404(session: Session, condition_id: int) -> Condition:
    condition = session.get(Condition, condition_id)
    if condition is None:
        raise HTTPException(status_code=404, detail="condition not found")
    return condition


@router.post("/trips/{trip_id}/conditions", response_model=ConditionRead, status_code=201)
def create_condition(
    trip_id: int, payload: ConditionCreate, session: Session = Depends(get_session)
) -> Condition:
    if session.get(Trip, trip_id) is None:
        raise HTTPException(status_code=404, detail="trip not found")
    if session.get(Member, payload.member_id) is None:
        raise HTTPException(status_code=404, detail="member not found")
    data = payload.model_dump()
    data["type"] = payload.type.value
    data["status"] = payload.status.value
    data["source"] = payload.source.value
    condition = Condition(trip_id=trip_id, **data)
    session.add(condition)
    session.commit()
    session.refresh(condition)
    return condition


@router.get("/trips/{trip_id}/conditions", response_model=list[ConditionRead])
def list_conditions(
    trip_id: int, session: Session = Depends(get_session)
) -> list[Condition]:
    return list(
        session.exec(select(Condition).where(Condition.trip_id == trip_id)).all()
    )


@router.patch("/conditions/{condition_id}", response_model=ConditionRead)
def update_condition(
    condition_id: int,
    payload: ConditionUpdate,
    acting: int = Depends(acting_member_id),
    session: Session = Depends(get_session),
) -> Condition:
    condition = _condition_or_404(session, condition_id)
    data = payload.model_dump(exclude_unset=True)

    if "status" in data and data["status"] != condition.status and condition.member_id != acting:
        raise HTTPException(
            status_code=403,
            detail="only the owner of a condition can change its status",
        )

    if data.get("status") is not None:
        data["status"] = data["status"].value
    for key, value in data.items():
        setattr(condition, key, value)
    session.add(condition)
    session.commit()
    session.refresh(condition)
    return condition


@router.post("/conditions/{condition_id}/confirm", response_model=ConditionRead)
def confirm_condition(
    condition_id: int,
    acting: int = Depends(acting_member_id),
    session: Session = Depends(get_session),
) -> Condition:
    condition = _condition_or_404(session, condition_id)
    if condition.member_id != acting:
        raise HTTPException(
            status_code=403, detail="only the owner can confirm their condition"
        )
    condition.confirmed_by_owner_at = datetime.now(timezone.utc)
    session.add(condition)
    session.commit()
    session.refresh(condition)
    return condition


@router.delete("/conditions/{condition_id}", status_code=204)
def delete_condition(
    condition_id: int, session: Session = Depends(get_session)
) -> Response:
    condition = _condition_or_404(session, condition_id)
    session.delete(condition)
    session.commit()
    return Response(status_code=204)

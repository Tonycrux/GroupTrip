from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session, select

from app.db import get_session
from app.models import Approval, Member, Trip
from app.schemas import ApprovalCreate, ApprovalRead, ApprovalStatus

router = APIRouter(tags=["approvals"])


def _member_ids(session: Session, trip_id: int) -> list[int]:
    return [
        m.id for m in session.exec(select(Member).where(Member.trip_id == trip_id)).all()
    ]


@router.get("/trips/{trip_id}/approvals", response_model=ApprovalStatus)
def get_approvals(trip_id: int, session: Session = Depends(get_session)) -> ApprovalStatus:
    if session.get(Trip, trip_id) is None:
        raise HTTPException(status_code=404, detail="trip not found")
    member_ids = _member_ids(session, trip_id)
    approved = {
        a.member_id
        for a in session.exec(select(Approval).where(Approval.trip_id == trip_id)).all()
    }
    pending = [mid for mid in member_ids if mid not in approved]
    return ApprovalStatus(
        approved_member_ids=sorted(approved & set(member_ids)),
        pending_member_ids=pending,
        fully_approved=bool(member_ids) and not pending,
    )


@router.post("/trips/{trip_id}/approvals", response_model=ApprovalRead, status_code=201)
def approve(
    trip_id: int, payload: ApprovalCreate, session: Session = Depends(get_session)
) -> Approval:
    if session.get(Trip, trip_id) is None:
        raise HTTPException(status_code=404, detail="trip not found")
    member = session.get(Member, payload.member_id)
    if member is None or member.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="member not found in trip")

    existing = session.exec(
        select(Approval)
        .where(Approval.trip_id == trip_id)
        .where(Approval.member_id == payload.member_id)
    ).first()
    if existing is not None:
        return existing

    approval = Approval(trip_id=trip_id, member_id=payload.member_id)
    session.add(approval)
    session.commit()
    session.refresh(approval)
    return approval


@router.delete("/trips/{trip_id}/approvals/{member_id}", status_code=204)
def withdraw(
    trip_id: int, member_id: int, session: Session = Depends(get_session)
) -> Response:
    approval = session.exec(
        select(Approval)
        .where(Approval.trip_id == trip_id)
        .where(Approval.member_id == member_id)
    ).first()
    if approval is None:
        raise HTTPException(status_code=404, detail="approval not found")
    session.delete(approval)
    session.commit()
    return Response(status_code=204)

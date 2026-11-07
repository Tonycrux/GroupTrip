from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import (
    ActivityRequest,
    Approval,
    Condition,
    Conflict as ConflictRow,
    Member,
    PlanItem,
    Rating,
    RevisionLog,
    Trip,
    Veto,
)
from app.routers.profile import get_profile_fields, to_profile_read
from app.schemas import (
    ApprovalStatus,
    BootstrapRead,
    PlanItemRead,
    PlanRead,
)

router = APIRouter(tags=["bootstrap"])


@router.get("/trips/{trip_id}/bootstrap", response_model=BootstrapRead)
def bootstrap(trip_id: int, session: Session = Depends(get_session)) -> BootstrapRead:
    trip = session.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="trip not found")

    members = list(session.exec(select(Member).where(Member.trip_id == trip_id)).all())
    member_ids = [m.id for m in members]

    profiles = [to_profile_read(m.id, get_profile_fields(session, m.id)) for m in members]

    conditions = list(
        session.exec(select(Condition).where(Condition.trip_id == trip_id)).all()
    )

    approved = {
        a.member_id
        for a in session.exec(select(Approval).where(Approval.trip_id == trip_id)).all()
    }
    approvals = ApprovalStatus(
        approved_member_ids=sorted(approved & set(member_ids)),
        pending_member_ids=[mid for mid in member_ids if mid not in approved],
        fully_approved=bool(member_ids) and not [mid for mid in member_ids if mid not in approved],
    )

    vetoes = (
        list(session.exec(select(Veto).where(Veto.member_id.in_(member_ids))).all())
        if member_ids
        else []
    )
    ratings = (
        list(session.exec(select(Rating).where(Rating.member_id.in_(member_ids))).all())
        if member_ids
        else []
    )

    conflicts = list(
        session.exec(select(ConflictRow).where(ConflictRow.trip_id == trip_id)).all()
    )
    revisions = list(
        session.exec(
            select(RevisionLog)
            .where(RevisionLog.trip_id == trip_id)
            .order_by(RevisionLog.id.desc())
        ).all()
    )
    items = list(
        session.exec(select(PlanItem).where(PlanItem.trip_id == trip_id)).all()
    )
    requests = list(
        session.exec(
            select(ActivityRequest)
            .where(ActivityRequest.trip_id == trip_id)
            .order_by(ActivityRequest.id.desc())
        ).all()
    )

    return BootstrapRead(
        trip=trip,
        members=members,
        profiles=profiles,
        conditions=conditions,
        approvals=approvals,
        vetoes=vetoes,
        conflicts=conflicts,
        revisions=revisions,
        plan=PlanRead(
            items=[PlanItemRead.model_validate(i) for i in items],
            unscheduled_activity_ids=[],
        ),
        ratings=ratings,
        requests=requests,
    )

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session, select

from app.db import get_session
from app.engine.scheduler import build_schedule
from app.enums import ConditionStatus
from app.models import Activity, Condition, Member, PlanItem, Rating, Trip
from app.schemas import (
    ChangePreview,
    ChangePreviewRequest,
    PlanItemRead,
    PlanItemUpdate,
    PlanRead,
)

router = APIRouter(tags=["plan"])


def _trip_or_404(session: Session, trip_id: int) -> Trip:
    trip = session.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="trip not found")
    return trip


def _plan_items(session: Session, trip_id: int) -> list[PlanItem]:
    return list(session.exec(select(PlanItem).where(PlanItem.trip_id == trip_id)).all())


@router.post("/trips/{trip_id}/plan/generate", response_model=PlanRead)
def generate_plan(trip_id: int, session: Session = Depends(get_session)) -> PlanRead:
    trip = _trip_or_404(session, trip_id)
    if trip.selected_destination_id is None:
        raise HTTPException(status_code=400, detail="select a destination first")

    activities = list(
        session.exec(
            select(Activity).where(Activity.destination_id == trip.selected_destination_id)
        ).all()
    )

    existing = _plan_items(session, trip_id)
    pinned = [(i.activity_id, i.day_index, i.start_minute) for i in existing if i.locked]

    # Anything a member has said they are not interested in is left out of the schedule.
    member_ids = [
        m.id for m in session.exec(select(Member).where(Member.trip_id == trip_id)).all()
    ]
    rejected: set[int] = set()
    if member_ids:
        for rating in session.exec(select(Rating).where(Rating.member_id.in_(member_ids))).all():
            if rating.activity_id is not None and rating.value == "not_interested":
                rejected.add(rating.activity_id)

    # Locked rows survive a rebuild; everything else is repacked around them.
    for item in existing:
        if not item.locked:
            session.delete(item)
    session.commit()

    result = build_schedule(activities, trip.days, locked=pinned, excluded=rejected)
    kept = [i for i in _plan_items(session, trip_id) if i.locked]

    created: list[PlanItem] = list(kept)
    for si in result.items:
        item = PlanItem(
            trip_id=trip_id,
            activity_id=si.activity_id,
            day_index=si.day_index,
            start_minute=si.start_minute,
        )
        session.add(item)
        created.append(item)
    session.commit()
    for item in created:
        session.refresh(item)

    return PlanRead(
        items=[PlanItemRead.model_validate(i) for i in created],
        unscheduled_activity_ids=result.unscheduled_activity_ids,
    )


@router.get("/trips/{trip_id}/plan", response_model=PlanRead)
def get_plan(trip_id: int, session: Session = Depends(get_session)) -> PlanRead:
    _trip_or_404(session, trip_id)
    return PlanRead(
        items=[PlanItemRead.model_validate(i) for i in _plan_items(session, trip_id)],
        unscheduled_activity_ids=[],
    )


@router.delete("/trips/{trip_id}/plan", status_code=204)
def clear_plan(trip_id: int, session: Session = Depends(get_session)) -> Response:
    """Drop the timetable. A plan only makes sense for the destination it was built for."""
    _trip_or_404(session, trip_id)
    for item in _plan_items(session, trip_id):
        session.delete(item)
    session.commit()
    return Response(status_code=204)


@router.patch("/plan-items/{item_id}", response_model=PlanItemRead)
def update_plan_item(
    item_id: int, payload: PlanItemUpdate, session: Session = Depends(get_session)
) -> PlanItem:
    item = session.get(PlanItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="plan item not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("status") is not None:
        data["status"] = data["status"].value
    for key, value in data.items():
        setattr(item, key, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.post("/trips/{trip_id}/changes/preview", response_model=ChangePreview)
def preview_change(
    trip_id: int, payload: ChangePreviewRequest, session: Session = Depends(get_session)
) -> ChangePreview:
    _trip_or_404(session, trip_id)

    if payload.condition_id is not None:
        condition = session.get(Condition, payload.condition_id)
        if condition is None:
            raise HTTPException(status_code=404, detail="condition not found")
        member = session.get(Member, condition.member_id)
        owner = member.name if member else f"member {condition.member_id}"
        return ChangePreview(
            affected_member_ids=[condition.member_id],
            affected_condition_ids=[condition.id],
            requires_owner_confirmation=True,
            summary=(
                f"Changing '{condition.text}' affects {owner} and requires their confirmation."
            ),
        )

    if payload.activity_id is not None:
        activity = session.get(Activity, payload.activity_id)
        if activity is None:
            raise HTTPException(status_code=404, detail="activity not found")
        ratings = list(
            session.exec(select(Rating).where(Rating.activity_id == activity.id)).all()
        )
        affected_members = {r.member_id for r in ratings}
        conditions = list(
            session.exec(select(Condition).where(Condition.trip_id == trip_id)).all()
        )
        needle = activity.name.lower()
        affected_conditions = [
            c for c in conditions if needle in c.text.lower() or activity.type.lower() in c.text.lower()
        ]
        return ChangePreview(
            affected_member_ids=sorted(affected_members),
            affected_condition_ids=[c.id for c in affected_conditions],
            requires_owner_confirmation=any(
                c.status == ConditionStatus.fixed.value for c in affected_conditions
            ),
            summary=(
                f"Changing '{activity.name}' affects {len(affected_members)} member(s) "
                f"and {len(affected_conditions)} condition(s)."
            ),
        )

    raise HTTPException(status_code=400, detail="provide activity_id or condition_id")

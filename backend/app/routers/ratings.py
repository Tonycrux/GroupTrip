from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.enums import ConditionStatus, ConditionType, RatingValue, Source
from app.models import Condition, Member, Rating
from app.schemas import RatingCreate, RatingRead

router = APIRouter(tags=["ratings"])


def _spawn_condition(session: Session, member: Member, rating: Rating, reason: str) -> Rating:
    condition = Condition(
        trip_id=member.trip_id,
        member_id=member.id,
        text=reason,
        type=(ConditionType.activity if rating.activity_id else ConditionType.other).value,
        status=ConditionStatus.flexible.value,
        source=Source.explicit.value,
        linked_plan_element=str(rating.destination_id or rating.activity_id),
    )
    session.add(condition)
    session.commit()
    session.refresh(condition)

    rating.condition_id = condition.id
    session.add(rating)
    session.commit()
    session.refresh(rating)
    return rating


@router.post("/members/{member_id}/ratings", response_model=RatingRead, status_code=201)
def upsert_rating(
    member_id: int, payload: RatingCreate, session: Session = Depends(get_session)
) -> Rating:
    member = session.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="member not found")

    query = select(Rating).where(Rating.member_id == member_id)
    if payload.destination_id is not None:
        query = query.where(Rating.destination_id == payload.destination_id)
    else:
        query = query.where(Rating.activity_id == payload.activity_id)

    rating = session.exec(query).first()
    data = payload.model_dump()
    data["value"] = payload.value.value
    if rating is None:
        rating = Rating(member_id=member_id, **data)
    else:
        for key, value in data.items():
            setattr(rating, key, value)
    session.add(rating)
    session.commit()
    session.refresh(rating)

    if (
        payload.value is RatingValue.interested_if
        and payload.reason
        and rating.condition_id is None
    ):
        rating = _spawn_condition(session, member, rating, payload.reason)

    return rating


@router.get("/members/{member_id}/ratings", response_model=list[RatingRead])
def list_ratings(member_id: int, session: Session = Depends(get_session)) -> list[Rating]:
    return list(session.exec(select(Rating).where(Rating.member_id == member_id)).all())

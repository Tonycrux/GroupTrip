from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.enums import ProfileFieldKey, Source
from app.models import Member, ProfileField
from app.schemas import ProfileFieldRead, ProfileFieldSet, ProfileRead, ProfileUpdate

router = APIRouter(tags=["profile"])


def get_profile_fields(session: Session, member_id: int) -> list[ProfileField]:
    return list(
        session.exec(select(ProfileField).where(ProfileField.member_id == member_id)).all()
    )


def to_profile_read(member_id: int, fields: list[ProfileField]) -> ProfileRead:
    read = ProfileRead(member_id=member_id)
    for item in fields:
        if item.field == "budget_max":
            read.budget_max = item.value
        elif item.field == "climates":
            read.climates = list(item.value or [])
        elif item.field == "activities":
            read.activities = list(item.value or [])
        elif item.field == "travel_time_max_hours":
            read.travel_time_max_hours = item.value
        elif item.field == "likes":
            read.likes = list(item.value or [])
        elif item.field == "dislikes":
            read.dislikes = list(item.value or [])
    read.fields = [ProfileFieldRead.model_validate(f) for f in fields]
    return read


def _upsert_field(
    session: Session,
    member_id: int,
    field: str,
    value,
    source: str,
    confidence: float | None,
) -> None:
    existing = session.exec(
        select(ProfileField)
        .where(ProfileField.member_id == member_id)
        .where(ProfileField.field == field)
    ).first()
    if existing is None:
        existing = ProfileField(member_id=member_id, field=field)
    existing.value = value
    existing.source = source
    existing.confidence = confidence
    session.add(existing)


@router.get("/members/{member_id}/profile", response_model=ProfileRead)
def get_profile(member_id: int, session: Session = Depends(get_session)) -> ProfileRead:
    if session.get(Member, member_id) is None:
        raise HTTPException(status_code=404, detail="member not found")
    return to_profile_read(member_id, get_profile_fields(session, member_id))


@router.put("/members/{member_id}/profile", response_model=ProfileRead)
def upsert_profile(
    member_id: int, payload: ProfileUpdate, session: Session = Depends(get_session)
) -> ProfileRead:
    if session.get(Member, member_id) is None:
        raise HTTPException(status_code=404, detail="member not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        _upsert_field(session, member_id, key, value, Source.explicit.value, None)
    session.commit()
    return to_profile_read(member_id, get_profile_fields(session, member_id))


@router.patch("/members/{member_id}/profile/{field}", response_model=ProfileRead)
def set_profile_field(
    member_id: int,
    field: str,
    payload: ProfileFieldSet,
    session: Session = Depends(get_session),
) -> ProfileRead:
    if session.get(Member, member_id) is None:
        raise HTTPException(status_code=404, detail="member not found")
    if field not in {k.value for k in ProfileFieldKey}:
        raise HTTPException(status_code=400, detail=f"unknown profile field '{field}'")
    _upsert_field(session, member_id, field, payload.value, payload.source.value, payload.confidence)
    session.commit()
    return to_profile_read(member_id, get_profile_fields(session, member_id))

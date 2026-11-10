from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.db import get_session
from app.deps import acting_member_id
from app.engine.aggregation import strategy_label
from app.enums import RankingStrategy, Source
from app.llm.explain import build_input, explain
from app.llm.parse import ParsedCondition, parse_conditions, profile_updates
from app.models import Condition, Member
from app.routers.profile import _upsert_field, get_profile_fields, to_profile_read
from app.routers.recommendations import _trip_or_404, score_destinations

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/trips/{trip_id}/recommendations/{destination_id}/explanation")
async def llm_explanation(
    trip_id: int,
    destination_id: int,
    strategy: RankingStrategy | None = Query(default=None),
    session: Session = Depends(get_session),
):
    trip = _trip_or_404(session, trip_id)
    chosen = strategy or RankingStrategy(trip.ranking_strategy)
    everything = score_destinations(session, trip, chosen)
    sd = next((s for s in everything if s.destination.id == destination_id), None)
    if sd is None:
        raise HTTPException(status_code=404, detail="destination not found")

    names = {s.member_id: s.member_name for s in sd.member_scores}
    inp = build_input(sd.destination, sd.member_scores, sd.conflicts,
                      sd.group_score, strategy_label(chosen), names)
    others = [s.destination.name for s in everything if s.destination.id != destination_id]
    return await explain(inp, others)


class ParseIn(BaseModel):
    text: str = Field(min_length=3, max_length=300)


@router.post("/conditions/parse")          # proposes only, saves nothing
async def parse(body: ParseIn):
    return {"conditions": [c.model_dump() for c in await parse_conditions(body.text)]}


@router.post("/trips/{trip_id}/members/{member_id}/conditions/accept")
def accept(
    trip_id: int,
    member_id: int,
    body: list[ParsedCondition],
    acting: int = Depends(acting_member_id),
    session: Session = Depends(get_session),
):
    _trip_or_404(session, trip_id)
    if session.get(Member, member_id) is None:
        raise HTTPException(status_code=404, detail="member not found")
    if acting != member_id:
        raise HTTPException(status_code=403, detail="only the owner can accept their conditions")

    current = to_profile_read(member_id, get_profile_fields(session, member_id))
    created = []
    for c in body:
        cond = Condition(
            trip_id=trip_id, member_id=member_id, text=c.text, type=c.type,
            status=c.status, source=Source.explicit.value,
            confirmed_by_owner_at=datetime.now(timezone.utc),
        )
        session.add(cond)
        created.append(cond)
        for key, value in profile_updates(c, current).items():
            _upsert_field(session, member_id, key, value, Source.explicit.value, None)
    session.commit()
    for cond in created:
        session.refresh(cond)
    return [{"id": c.id, "text": c.text, "type": c.type, "status": c.status} for c in created]
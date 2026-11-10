from typing import Literal
from pydantic import BaseModel, ValidationError
from app.llm.client import complete
from app.llm.prompts import SYS_PARSE
from app.llm.explain import _nums
import re


class ParsedCondition(BaseModel):
    type: Literal["budget", "travel_time", "activity", "climate", "other"]
    operator: Literal["<=", "avoid", "want"] | None = None
    value: float | str | None = None
    status: Literal["fixed", "flexible"]
    text: str


class ParseOut(BaseModel):
    conditions: list[ParsedCondition]


def _grounded(c: ParsedCondition, source: str) -> bool:
    if c.type in {"budget", "travel_time"}:
        try:
            return float(c.value) in _nums(source)  # number must appear in the sentence
        except (TypeError, ValueError):
            return False
    if c.type in {"activity", "climate"} and c.value:
        return str(c.value).lower() in source.lower()
    return True


async def parse_conditions(source: str) -> list[ParsedCondition]:
    try:
        text = await complete(SYS_PARSE, source, 1500)
    except Exception:
        return []
    raw = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        conds = [c for c in ParseOut.model_validate_json(raw).conditions if _grounded(c, source)]
    except ValidationError:
        return []
    for c in conds:
        if c.type in {"budget", "travel_time"}:
            c.operator = "<="  # a ceiling by definition
    return conds


def profile_updates(c: ParsedCondition, current) -> dict:
    """Make a confirmed condition visible to scoring."""
    if c.type == "budget" and c.value is not None:
        return {"budget_max": float(c.value)}
    if c.type == "travel_time" and c.value is not None:
        return {"travel_time_max_hours": float(c.value)}
    if c.type == "activity" and c.operator == "avoid" and c.value:
        return {"dislikes": sorted({*current.dislikes, str(c.value).lower()})}
    if c.type == "activity" and c.operator == "want" and c.value:
        return {"activities": sorted({*current.activities, str(c.value).lower()})}
    return {}
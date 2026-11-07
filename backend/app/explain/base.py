from dataclasses import dataclass
from typing import Protocol

from app.engine.conflicts import Conflict
from app.engine.scoring import ScoredMember
from app.enums import RankingStrategy
from app.models import Destination


@dataclass
class ExplanationContext:
    destination: Destination
    strategy: RankingStrategy
    group_score: float
    member_scores: list[ScoredMember]
    conflicts: list[Conflict]


class Explainer(Protocol):
    def explain(self, ctx: ExplanationContext) -> str: ...

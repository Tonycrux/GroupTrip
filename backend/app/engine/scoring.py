from dataclasses import dataclass, field
from typing import Optional

from app.models import Condition, Destination, ProfileField, Rating

HARD_VIOLATION_PENALTY = 35.0

RATING_ADJUSTMENT = {
    "interested": 8.0,
    "interested_if": 2.0,
    "not_interested": -12.0,
    "skipped": 0.0,
}


@dataclass
class MemberProfile:
    budget_max: Optional[float] = None
    climates: list[str] = field(default_factory=list)
    activities: list[str] = field(default_factory=list)
    travel_time_max_hours: Optional[float] = None
    likes: list[str] = field(default_factory=list)
    dislikes: list[str] = field(default_factory=list)


@dataclass
class ScoredMember:
    member_id: int
    member_name: str
    score: float
    hard_violations: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def profile_from_fields(fields: list[ProfileField]) -> MemberProfile:
    profile = MemberProfile()
    for item in fields:
        if item.field == "budget_max":
            profile.budget_max = item.value
        elif item.field == "climates":
            profile.climates = list(item.value or [])
        elif item.field == "activities":
            profile.activities = list(item.value or [])
        elif item.field == "travel_time_max_hours":
            profile.travel_time_max_hours = item.value
        elif item.field == "likes":
            profile.likes = list(item.value or [])
        elif item.field == "dislikes":
            profile.dislikes = list(item.value or [])
    return profile


def _overlap_ratio(wanted: list[str], offered: list[str]) -> Optional[float]:
    if not wanted:
        return None
    if not offered:
        return 0.0
    wanted_set = {w.lower() for w in wanted}
    offered_set = {o.lower() for o in offered}
    return len(wanted_set & offered_set) / len(wanted_set)


def _budget_component(profile: MemberProfile, dest: Destination) -> tuple[Optional[float], Optional[str]]:
    if profile.budget_max is None or profile.budget_max <= 0:
        return None, None
    if dest.est_cost <= profile.budget_max:
        return 1.0, None
    ratio = profile.budget_max / dest.est_cost
    return max(0.0, ratio) ** 1.5, f"estimated cost {dest.est_cost:.0f} exceeds budget {profile.budget_max:.0f}"


def _climate_component(profile: MemberProfile, dest: Destination) -> tuple[Optional[float], Optional[str]]:
    if not profile.climates:
        return None, None
    if dest.climate.lower() in {c.lower() for c in profile.climates}:
        return 1.0, None
    return 0.25, f"climate '{dest.climate}' is not in preferred climates"


def _activities_component(profile: MemberProfile, dest: Destination) -> tuple[Optional[float], Optional[str]]:
    ratio = _overlap_ratio(profile.activities, dest.activities)
    if ratio is None:
        return None, None
    return ratio, (None if ratio >= 0.5 else "few matching activities")


def _travel_component(profile: MemberProfile, dest: Destination) -> tuple[Optional[float], Optional[str]]:
    if profile.travel_time_max_hours is None or profile.travel_time_max_hours <= 0:
        return None, None
    if dest.travel_time_hours <= profile.travel_time_max_hours:
        return 1.0, None
    ratio = profile.travel_time_max_hours / dest.travel_time_hours
    return max(0.0, ratio), f"travel time {dest.travel_time_hours:.1f}h exceeds limit {profile.travel_time_max_hours:.1f}h"


def _taste_component(profile: MemberProfile, dest: Destination) -> tuple[Optional[float], Optional[str]]:
    if not profile.likes and not profile.dislikes:
        return None, None
    offered = {a.lower() for a in dest.activities} | {dest.dest_type.lower(), dest.climate.lower()}
    likes_hit = len({l.lower() for l in profile.likes} & offered)
    dislikes_hit = len({d.lower() for d in profile.dislikes} & offered)
    liked = {l.lower() for l in profile.likes} & offered
    disliked = sorted({d.lower() for d in profile.dislikes} & offered)
    score = 0.5 + 0.25 * likes_hit - 0.5 * dislikes_hit
    note = None
    if dislikes_hit:
        note = "matches something this member actively dislikes"
    return max(0.0, min(1.0, score)), note


def _fixed_condition_violations(
    profile: MemberProfile, conditions: list[Condition], dest: Destination
) -> list[str]:
    violations: list[str] = []
    fixed = [c for c in conditions if c.status == "fixed"]
    for cond in fixed:
        if cond.type == "budget" and profile.budget_max is not None and dest.est_cost > profile.budget_max:
            violations.append(cond.text)
        elif cond.type == "travel_time" and profile.travel_time_max_hours is not None and dest.travel_time_hours > profile.travel_time_max_hours:
            violations.append(cond.text)
        elif cond.type == "climate" and profile.climates and dest.climate.lower() not in {c.lower() for c in profile.climates}:
            violations.append(cond.text)
        elif cond.type == "activity" and profile.activities and not (
            {a.lower() for a in profile.activities} & {a.lower() for a in dest.activities}
        ):
            violations.append(cond.text)
    return violations


def _rating_note(rating: Optional[Rating]) -> tuple[float, Optional[str]]:
    if rating is None:
        return 0.0, None
    delta = RATING_ADJUSTMENT.get(rating.value, 0.0)
    if rating.value == "interested":
        return delta, "rated this card as interested"
    if rating.value == "interested_if":
        return delta, "interested only if a condition holds"
    if rating.value == "not_interested":
        return delta, "rated this card as not interested"
    return delta, None


def score_member(
    member_id: int,
    member_name: str,
    profile: MemberProfile,
    conditions: list[Condition],
    dest: Destination,
    rating: Optional[Rating] = None,
) -> ScoredMember:
    components: list[tuple[float, float]] = []
    reasons: list[str] = []

    for weight, result in (
        (2.5, _budget_component(profile, dest)),
        (1.0, _climate_component(profile, dest)),
        (1.5, _activities_component(profile, dest)),
        (1.0, _travel_component(profile, dest)),
        (1.0, _taste_component(profile, dest)),
    ):
        value, note = result
        if value is None:
            continue
        components.append((weight, value))
        if note and value < 0.7:
            reasons.append(note)

    if components:
        total_weight = sum(w for w, _ in components)
        base = sum(w * v for w, v in components) / total_weight
    else:
        base = 0.5

    rating_delta, rating_note = _rating_note(rating)
    if rating_note:
        reasons.append(rating_note)

    violations = _fixed_condition_violations(profile, conditions, dest)
    score = base * 100.0 + rating_delta - HARD_VIOLATION_PENALTY * len(violations)
    score = max(0.0, min(100.0, score))

    if violations:
        reasons.insert(0, f"violates a fixed condition: {violations[0]}")

    return ScoredMember(
        member_id=member_id,
        member_name=member_name,
        score=round(score, 1),
        hard_violations=violations,
        reasons=reasons,
    )

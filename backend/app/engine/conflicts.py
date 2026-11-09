from dataclasses import dataclass

from app.engine.scoring import MemberProfile, ScoredMember
from app.models import Destination


@dataclass
class Conflict:
    kind: str
    member_ids: list[int]
    summary: str
    severity: float


def _names(ids: list[int], names: dict[int, str]) -> str:
    return ", ".join(names.get(i, f"member {i}") for i in ids)


def detect_conflicts(
    prefs: dict[int, MemberProfile],
    names: dict[int, str],
    dest: Destination,
    scored: list[ScoredMember] | None = None,
) -> list[Conflict]:
    conflicts: list[Conflict] = []

    over = [m for m, p in prefs.items() if p.budget_max and dest.est_cost > p.budget_max]
    under = [m for m, p in prefs.items() if p.budget_max and dest.est_cost <= p.budget_max]
    if over and under:
        cheapest_limit = min(prefs[m].budget_max for m in over)
        severity = min(1.0, (dest.est_cost - cheapest_limit) / max(1.0, dest.est_cost))
        conflicts.append(
            Conflict(
                kind="budget",
                member_ids=over + under,
                summary=(
                    f"estimated cost {dest.est_cost:.0f} is over budget for "
                    f"{_names(over, names)}, but within budget for {_names(under, names)}"
                ),
                severity=round(severity, 2),
            )
        )

    for key, label in (("climate", "climate"), ("activity", "activity")):
        likers, avoiders = [], []
        for m, p in prefs.items():
            target = dest.climate.lower() if key == "climate" else None
            if key == "climate":
                if target and target in {c.lower() for c in p.climates}:
                    likers.append(m)
                if target and target in {d.lower() for d in p.dislikes}:
                    avoiders.append(m)
            else:
                hit_like = {a.lower() for a in p.likes} & {a.lower() for a in dest.activities}
                hit_dislike = {a.lower() for a in p.dislikes} & {a.lower() for a in dest.activities}
                if hit_like:
                    likers.append(m)
                if hit_dislike:
                    avoiders.append(m)
        if likers and avoiders:
            conflicts.append(
                Conflict(
                    kind=key,
                    member_ids=likers + avoiders,
                    summary=(
                        f"{_names(likers, names)} want this {label} while "
                        f"{_names(avoiders, names)} avoid it"
                    ),
                    severity=0.8,
                )
            )

    for sm in scored or []:
        if sm.hard_violations:
            conflicts.append(
                Conflict(
                    kind="fixed_condition",
                    member_ids=[sm.member_id],
                    summary=f"{sm.member_name} has a fixed condition this destination breaks: {sm.hard_violations[0]}",
                    severity=1.0,
                )
            )

    return conflicts


def conflicts_between_conditions(conditions, names: dict[int, str]) -> list[Conflict]:
    by_type: dict[str, list] = {}
    for cond in conditions:
        by_type.setdefault(cond.type, []).append(cond)

    conflicts: list[Conflict] = []
    for ctype, group in by_type.items():
        if ctype not in {"budget", "climate", "activity", "travel_time"}:
            continue
        owners = {c.member_id for c in group}
        if len(owners) > 1:
            conflicts.append(
                Conflict(
                    kind=f"competing_conditions:{ctype}",
                    member_ids=list(owners),
                    summary=(
                        f"{_names(list(owners), names)} each hold a {ctype} condition that may "
                        f"point in different directions"
                    ),
                    severity=0.5,
                )
            )
    return conflicts

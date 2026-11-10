from dataclasses import dataclass

from app.engine.scoring import MemberProfile, ScoredMember
from app.models import Destination
from dataclasses import dataclass, field


# @dataclass
# class Conflict:
#     kind: str
#     member_ids: list[int]
#     summary: str
#     severity: float

@dataclass
class Conflict:
    kind: str
    member_ids: list[int]
    summary: str
    severity: float
    subject: str | None = None
    wanted_by: list[int] = field(default_factory=list)
    avoided_by: list[int] = field(default_factory=list)


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

    # one conflict per activity, so nobody is on both sides
    for act in sorted({a.lower() for a in dest.activities}):
        likers = [m for m, p in prefs.items() if act in {x.lower() for x in p.likes}]
        avoiders = [m for m, p in prefs.items() if act in {x.lower() for x in p.dislikes}]
        if likers and avoiders:
            conflicts.append(Conflict(
                kind="activity", member_ids=likers + avoiders, severity=0.8,
                summary=f"{_names(likers, names)} want {act} while {_names(avoiders, names)} avoid it",
                subject=act, wanted_by=likers, avoided_by=avoiders))

    climate = dest.climate.lower()
    likers = [m for m, p in prefs.items() if climate in {c.lower() for c in p.climates}]
    avoiders = [m for m, p in prefs.items() if climate in {d.lower() for d in p.dislikes}]
    if likers and avoiders:
        conflicts.append(Conflict(
            kind="climate", member_ids=likers + avoiders, severity=0.8,
            summary=f"{_names(likers, names)} want {climate} weather while {_names(avoiders, names)} avoid it",
            subject=climate, wanted_by=likers, avoided_by=avoiders))

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

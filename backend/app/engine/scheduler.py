from dataclasses import dataclass, field
from typing import Optional

from app.models import Activity

DAY_START_MIN = 9 * 60
DAY_END_MIN = 21 * 60


@dataclass
class ScheduledItem:
    activity_id: int
    day_index: int
    start_minute: int


@dataclass
class ScheduleResult:
    items: list[ScheduledItem] = field(default_factory=list)
    unscheduled_activity_ids: list[int] = field(default_factory=list)


def _to_minutes(value) -> Optional[int]:
    if value is None:
        return None
    return value.hour * 60 + value.minute


def build_schedule(
    activities: list[Activity],
    days: int,
    budget: Optional[float] = None,
    locked: Optional[list[tuple[int, int, Optional[int]]]] = None,
    excluded: Optional[set[int]] = None,
) -> ScheduleResult:
    """Pack activities into days.

    ``locked`` holds (activity_id, day_index, start_minute) for rows the group has pinned.
    Those are left exactly where they are, and each day's packing starts after them.
    ``excluded`` holds activities the group has already turned down; they are never scheduled.
    """
    days = max(1, days)
    cursors = [DAY_START_MIN] * days
    result = ScheduleResult()
    total_cost = 0.0
    rejected = excluded or set()

    by_id = {a.id: a for a in activities if a.id is not None}

    skip: set[int] = set()
    for activity_id, day_index, start_minute in locked or []:
        skip.add(activity_id)
        if 0 <= day_index < days:
            act = by_id.get(activity_id)
            duration = int(round((act.duration_hours if act else 1.0) * 60))
            start = start_minute if start_minute is not None else DAY_START_MIN
            cursors[day_index] = max(cursors[day_index], start + duration)

    ordered = sorted(
        [a for a in by_id.values() if a.id not in skip and a.id not in rejected],
        key=lambda a: a.duration_hours,
        reverse=True,
    )

    for act in ordered:
        duration = int(round(act.duration_hours * 60))
        open_from = _to_minutes(act.open_from)
        open_to = _to_minutes(act.open_to)
        placed = False
        for day in range(days):
            start = max(cursors[day], open_from if open_from is not None else DAY_START_MIN)
            start += act.travel_time_min
            end = start + duration
            close = open_to if open_to is not None else DAY_END_MIN
            if end > min(close, DAY_END_MIN):
                continue
            if budget is not None and total_cost + act.est_cost > budget:
                continue
            result.items.append(ScheduledItem(act.id, day, start))
            cursors[day] = end + act.travel_time_min
            total_cost += act.est_cost
            placed = True
            break
        if not placed:
            result.unscheduled_activity_ids.append(act.id)

    return result

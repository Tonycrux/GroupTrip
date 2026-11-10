from dataclasses import dataclass, field
from typing import Optional

from app.models import Activity

DAY_START_MIN = 8 * 60
DAY_END_MIN = 23 * 60


@dataclass
class Placement:
    activity_id: int
    day_index: int
    start_minute: int


@dataclass
class Rejection:
    activity_id: int
    reason: str


@dataclass
class ScheduleResult:
    items: list[Placement] = field(default_factory=list)
    unscheduled: list[Rejection] = field(default_factory=list)
    day_spend: list[float] = field(default_factory=list)


def _to_minutes(value) -> Optional[int]:
    if value is None:
        return None
    return value.hour * 60 + value.minute


def opening_window(activity: Activity) -> Optional[tuple[int, int]]:
    """The stretch of a day this activity can actually be visited in.

    Returns None when the activity is never open while the day runs, for example a
    bar that opens at 21:00 and closes at 02:00 when the day ends at 23:00.
    """
    opens = _to_minutes(activity.open_from)
    closes = _to_minutes(activity.open_to)

    if opens is None and closes is None:
        return DAY_START_MIN, DAY_END_MIN

    if opens is not None and closes is not None and closes <= opens:
        return None  # runs past midnight, so it cannot sit inside one day

    start = max(DAY_START_MIN, opens if opens is not None else DAY_START_MIN)
    end = min(DAY_END_MIN, closes if closes is not None else DAY_END_MIN)
    if end <= start:
        return None
    return start, end


def _earliest_slot(
    busy: list[tuple[int, int]], duration: int, travel: int, window: tuple[int, int]
) -> Optional[int]:
    """First free block start, in block coordinates, that leaves room for travel + duration."""
    low, high = window
    cursor = max(DAY_START_MIN, low)

    for block_start, block_end in sorted(busy):
        if block_start <= cursor:
            cursor = max(cursor, block_end)
            continue
        if cursor + travel + duration <= min(block_start, high):
            return cursor
        cursor = max(cursor, block_end)

    if cursor + travel + duration <= high:
        return cursor
    return None


def build_schedule(
    activities: list[Activity],
    days: int,
    per_day_budget: Optional[float] = None,
    fixed: Optional[list[tuple[int, int, Optional[int]]]] = None,
    excluded: Optional[set[int]] = None,
) -> ScheduleResult:
    """Lay activities into days.

    ``fixed`` placements stay exactly where they are; everything else is packed into the
    gaps around them. ``excluded`` activities are left out entirely. Each day may spend at
    most ``per_day_budget`` on paid activities, and an activity only goes in if it fits
    inside both the day and its own opening hours.
    """
    days = max(1, days)
    by_id = {a.id: a for a in activities if a.id is not None}

    busy: list[list[tuple[int, int]]] = [[] for _ in range(days)]
    spent = [0.0] * days
    result = ScheduleResult(day_spend=[0.0] * days)
    placed: set[int] = set()

    for activity_id, day_index, start_minute in fixed or []:
        activity = by_id.get(activity_id)
        if activity is None or not (0 <= day_index < days):
            continue
        start = start_minute if start_minute is not None else DAY_START_MIN
        duration = int(round(activity.duration_hours * 60))
        block_start = max(DAY_START_MIN, start - activity.travel_time_min)
        busy[day_index].append((block_start, start + duration))
        spent[day_index] += activity.est_cost
        placed.add(activity_id)
        result.items.append(Placement(activity_id, day_index, start))

    rejected = excluded or set()
    candidates = sorted(
        [a for a in by_id.values() if a.id not in placed and a.id not in rejected],
        key=lambda a: a.duration_hours,
        reverse=True,
    )

    for activity in candidates:
        duration = int(round(activity.duration_hours * 60))
        window = opening_window(activity)
        if window is None:
            result.unscheduled.append(
                Rejection(activity.id, "opening hours never overlap the day")
            )
            continue

        budget_blocked = False
        for day in range(days):
            if per_day_budget is not None and spent[day] + activity.est_cost > per_day_budget + 1e-9:
                budget_blocked = True
                continue
            slot = _earliest_slot(busy[day], duration, activity.travel_time_min, window)
            if slot is None:
                continue
            busy[day].append((slot, slot + activity.travel_time_min + duration))
            spent[day] += activity.est_cost
            result.items.append(
                Placement(activity.id, day, slot + activity.travel_time_min)
            )
            break
        else:
            reason = (
                "does not fit what is left of the daily budget"
                if budget_blocked
                else "no free slot long enough"
            )
            result.unscheduled.append(Rejection(activity.id, reason))

    result.day_spend = [round(value, 2) for value in spent]
    return result

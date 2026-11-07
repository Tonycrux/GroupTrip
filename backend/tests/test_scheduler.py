from datetime import time

from app.engine.scheduler import (
    DAY_END_MIN,
    DAY_START_MIN,
    build_schedule,
    opening_window,
)


def activity(id_, name, hours=1.0, cost=0.0, opens=None, closes=None, travel=0):
    return type(
        "A",
        (),
        {
            "id": id_,
            "name": name,
            "duration_hours": hours,
            "est_cost": cost,
            "travel_time_min": travel,
            "open_from": time(*map(int, opens.split(":"))) if opens else None,
            "open_to": time(*map(int, closes.split(":"))) if closes else None,
        },
    )()


def test_packs_into_the_first_day_when_it_fits():
    acts = [activity(1, "Museum", hours=2)]
    result = build_schedule(acts, days=2)

    assert [i.activity_id for i in result.items] == [1]
    assert result.items[0].day_index == 0
    assert result.items[0].start_minute == DAY_START_MIN
    assert result.unscheduled == []


def test_moves_on_to_the_next_day_when_the_first_is_full():
    acts = [activity(1, "Long walk", hours=14), activity(2, "Second", hours=14)]
    result = build_schedule(acts, days=2)

    days = {i.activity_id: i.day_index for i in result.items}
    assert days == {1: 0, 2: 1}


def test_uses_the_gap_left_by_a_fixed_row():
    acts = [activity(1, "Early", hours=1), activity(2, "Afternoon", hours=1)]
    fixed = [(2, 0, 14 * 60)]  # afternoon is pinned at 14:00

    result = build_schedule(acts, days=1, fixed=fixed)

    placed = {i.activity_id: i.start_minute for i in result.items}
    assert placed[2] == 14 * 60
    assert placed[1] == DAY_START_MIN  # morning gap, not after the afternoon row


def test_activity_whose_opening_hours_miss_the_day_is_reported():
    acts = [activity(1, "Nightclub", hours=3, opens="21:00", closes="02:00")]
    result = build_schedule(acts, days=1)

    assert result.items == []
    assert result.unscheduled[0].activity_id == 1
    assert "opening hours" in result.unscheduled[0].reason


def test_opening_hours_shift_the_start():
    acts = [activity(1, "Gallery", hours=2, opens="11:00", closes="18:00")]
    result = build_schedule(acts, days=1)

    assert result.items[0].start_minute == 11 * 60


def test_daily_budget_blocks_expensive_activities():
    acts = [activity(1, "Helicopter tour", hours=2, cost=300)]
    result = build_schedule(acts, days=1, per_day_budget=100)

    assert result.items == []
    assert "budget" in result.unscheduled[0].reason


def test_free_activities_ignore_the_budget():
    acts = [activity(1, "Park", hours=2, cost=0)]
    result = build_schedule(acts, days=1, per_day_budget=0)

    assert [i.activity_id for i in result.items] == [1]


def test_day_spend_adds_up_per_day():
    acts = [activity(1, "A", hours=1, cost=20), activity(2, "B", hours=1, cost=30)]
    result = build_schedule(acts, days=2)

    assert sum(result.day_spend) == 50
    assert len(result.day_spend) == 2


def test_travel_time_is_left_between_activities():
    acts = [activity(1, "First", hours=1, travel=30), activity(2, "Second", hours=1, travel=30)]
    result = build_schedule(acts, days=1)

    first = min(result.items, key=lambda i: i.start_minute)
    second = max(result.items, key=lambda i: i.start_minute)
    assert second.start_minute - first.start_minute >= 60 + 30


def test_excluded_activities_never_appear():
    acts = [activity(1, "Rejected", hours=1), activity(2, "Wanted", hours=1)]
    result = build_schedule(acts, days=1, excluded={1})

    assert [i.activity_id for i in result.items] == [2]
    assert result.unscheduled == []


def test_opening_window_is_none_when_it_never_overlaps():
    assert opening_window(activity(1, "Club", opens="23:30", closes="03:00")) is None
    assert opening_window(activity(2, "Open all day")) == (DAY_START_MIN, DAY_END_MIN)

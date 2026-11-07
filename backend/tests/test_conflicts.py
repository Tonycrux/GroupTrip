from app.engine.conflicts import detect_conflicts
from app.engine.scoring import MemberProfile
from app.models import Destination


def test_budget_conflict_detected_between_members():
    dest = Destination(
        id=1,
        name="Bali",
        climate="tropical",
        dest_type="island",
        est_cost=1350,
        travel_time_hours=16,
        activities=["beach", "nature"],
    )
    profiles = {
        1: MemberProfile(budget_max=2000),
        2: MemberProfile(budget_max=800),
    }
    names = {1: "Ada", 2: "Ben"}
    conflicts = detect_conflicts(profiles, names, dest)
    assert any(c.kind == "budget" for c in conflicts)


def test_like_and_dislike_produces_activity_conflict():
    dest = Destination(
        id=2,
        name="Barcelona",
        climate="warm",
        dest_type="coastal city",
        est_cost=1100,
        travel_time_hours=2.5,
        activities=["beach", "culture"],
    )
    profiles = {
        1: MemberProfile(likes=["beach"]),
        2: MemberProfile(dislikes=["beach"]),
    }
    names = {1: "Ada", 2: "Ben"}
    conflicts = detect_conflicts(profiles, names, dest)
    assert any(c.kind == "activity" for c in conflicts)


def test_no_conflict_when_members_agree():
    dest = Destination(
        id=3,
        name="Prague",
        climate="continental",
        dest_type="cultural",
        est_cost=900,
        travel_time_hours=2,
        activities=["culture"],
    )
    profiles = {
        1: MemberProfile(budget_max=1200, climates=["continental"]),
        2: MemberProfile(budget_max=1500, climates=["continental"]),
    }
    names = {1: "Ada", 2: "Ben"}
    assert detect_conflicts(profiles, names, dest) == []

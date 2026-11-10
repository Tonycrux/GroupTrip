from app.engine.scoring import MemberProfile, score_member
from app.models import Condition, Destination, Rating


def make_destination(**kwargs):
    defaults = dict(
        id=1,
        name="Barcelona",
        climate="warm",
        dest_type="coastal city",
        est_cost=1100,
        travel_time_hours=2.5,
        activities=["beach", "culture", "food", "nightlife"],
    )
    defaults.update(kwargs)
    return Destination(**defaults)


def test_matching_preferences_score_high():
    profile = MemberProfile(
        budget_max=1500,
        climates=["warm"],
        activities=["beach", "food"],
        travel_time_max_hours=4,
        likes=["beach"],
    )
    scored = score_member(1, "Ada", profile, [], make_destination())
    assert scored.score > 80
    assert scored.hard_violations == []


def test_over_budget_lowers_score_and_reports_reason():
    profile = MemberProfile(budget_max=500, climates=["warm"], activities=["beach"])
    scored = score_member(2, "Ben", profile, [], make_destination())
    assert scored.score < 70
    assert any("budget" in r for r in scored.reasons)


def test_fixed_condition_violation_is_flagged():
    profile = MemberProfile(budget_max=500)
    fixed = Condition(
        id=1,
        trip_id=1,
        member_id=3,
        text="cannot spend more than 500",
        type="budget",
        status="fixed",
    )
    scored = score_member(3, "Cy", profile, [fixed], make_destination())
    assert scored.hard_violations == ["cannot spend more than 500"]
    assert scored.score <= 65


def test_flexible_condition_does_not_hard_block():
    profile = MemberProfile(budget_max=500)
    flexible = Condition(
        id=2,
        trip_id=1,
        member_id=4,
        text="prefer to keep costs low",
        type="budget",
        status="flexible",
    )
    scored = score_member(4, "Dee", profile, [flexible], make_destination())
    assert scored.hard_violations == []


def test_skipped_rating_does_not_count_as_rejection():
    profile = MemberProfile(budget_max=1500)
    baseline = score_member(1, "Ada", profile, [], make_destination())
    skipped = score_member(
        1,
        "Ada",
        profile,
        [],
        make_destination(),
        Rating(member_id=1, destination_id=1, value="skipped"),
    )
    assert skipped.score == baseline.score
    assert skipped.hard_violations == []


def test_not_interested_rating_lowers_score():
    profile = MemberProfile(budget_max=1500)
    baseline = score_member(1, "Ada", profile, [], make_destination())
    rated = score_member(
        1,
        "Ada",
        profile,
        [],
        make_destination(),
        Rating(member_id=1, destination_id=1, value="not_interested"),
    )
    assert rated.score < baseline.score


def test_interested_rating_raises_score():
    profile = MemberProfile(budget_max=900)
    baseline = score_member(1, "Ada", profile, [], make_destination())
    rated = score_member(
        1,
        "Ada",
        profile,
        [],
        make_destination(),
        Rating(member_id=1, destination_id=1, value="interested"),
    )
    assert rated.score > baseline.score

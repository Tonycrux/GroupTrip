from app.engine.aggregation import aggregate
from app.enums import RankingStrategy


def test_average_is_mean():
    assert aggregate([80.0, 60.0], RankingStrategy.average) == 70.0


def test_maximin_tracks_least_satisfied():
    assert aggregate([90.0, 40.0, 70.0], RankingStrategy.maximin) == 40.0


def test_balanced_sits_between_average_and_min():
    scores = [90.0, 50.0]
    value = aggregate(scores, RankingStrategy.balanced)
    assert 50.0 < value < 90.0


def test_avoid_dislikes_penalises_blocked_members():
    clean = aggregate([80.0, 75.0], RankingStrategy.avoid_dislikes)
    blocked = aggregate([80.0, 5.0], RankingStrategy.avoid_dislikes)
    assert blocked < clean


def test_aggregate_accepts_string_strategy():
    assert aggregate([10.0, 30.0], "maximin") == 10.0


def test_empty_scores_is_zero():
    assert aggregate([], RankingStrategy.average) == 0.0

from statistics import fmean

from app.enums import RankingStrategy


def aggregate(scores: list[float], strategy: RankingStrategy | str) -> float:
    if not scores:
        return 0.0
    strategy = RankingStrategy(strategy)

    if strategy is RankingStrategy.average:
        return fmean(scores)

    if strategy is RankingStrategy.maximin:
        return min(scores)

    if strategy is RankingStrategy.balanced:
        return 0.5 * min(scores) + 0.5 * fmean(scores)

    if strategy is RankingStrategy.avoid_dislikes:
        blocked = sum(1 for s in scores if s < 20.0)
        return fmean(scores) - 15.0 * blocked

    if strategy is RankingStrategy.complementary:
        above = sum(1 for s in scores if s >= 60.0)
        coverage = above / len(scores)
        return 0.6 * fmean(scores) + 0.4 * coverage * 100.0

    return fmean(scores)


def strategy_label(strategy: RankingStrategy | str) -> str:
    return {
        RankingStrategy.average: "favoring the highest average score",
        RankingStrategy.maximin: "giving more weight to the least-satisfied member",
        RankingStrategy.balanced: "balancing the average against the least-satisfied member",
        RankingStrategy.avoid_dislikes: "avoiding destinations anyone strongly dislikes",
        RankingStrategy.complementary: "rewarding destinations that satisfy many members at once",
    }[RankingStrategy(strategy)]

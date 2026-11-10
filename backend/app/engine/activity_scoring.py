from typing import Optional

from app.engine.conflicts import Conflict
from app.engine.scoring import MemberProfile, ScoredMember
from app.models import Activity, Condition, Rating


def score_activity(
    member_id: int,
    member_name: str,
    profile: MemberProfile,
    activity: Activity,
    rating: Optional[Rating] = None,
) -> ScoredMember:
    """How well one activity suits one person.

    Deliberately simple and deterministic, so the same inputs always give the same
    number and the reason can be read back to the group.
    """
    score = 50.0
    reasons: list[str] = []
    atype = (activity.type or "").lower()

    preferred = {a.lower() for a in profile.activities}
    likes = {l.lower() for l in profile.likes}
    dislikes = {d.lower() for d in profile.dislikes}

    if preferred:
        if atype in preferred:
            score += 25
            reasons.append("matches an activity they asked for")
        else:
            score -= 10

    if atype in likes:
        score += 10
        reasons.append("something they said they like")

    if atype in dislikes:
        score -= 30
        reasons.append("something they said they dislike")

    if rating is not None:
        if rating.value == "interested":
            score += 10
            reasons.append("said they are interested")
        elif rating.value == "not_interested":
            score -= 25
            reasons.append("said they are not interested")

    return ScoredMember(
        member_id=member_id,
        member_name=member_name,
        score=round(max(0.0, min(100.0, score)), 1),
        hard_violations=[],
        reasons=reasons,
    )


def _names(ids: list[int], names: dict[int, str]) -> str:
    return ", ".join(names.get(i, f"member {i}") for i in ids)


def detect_activity_conflicts(
    scored: list[ScoredMember],
    activity: Activity,
    profiles: dict[int, MemberProfile],
    conditions_by_member: dict[int, list[Condition]],
    names: dict[int, str],
) -> list[Conflict]:
    """Where the group splits over one activity, rather than over a whole destination."""
    conflicts: list[Conflict] = []
    atype = (activity.type or "").lower()

    if atype:
        likers = [
            s.member_id
            for s in scored
            if atype in {like.lower() for like in profiles[s.member_id].likes}
        ]
        avoiders = [
            s.member_id
            for s in scored
            if atype in {dislike.lower() for dislike in profiles[s.member_id].dislikes}
        ]
        if likers and avoiders:
            conflicts.append(
                Conflict(
                    kind="activity",
                    member_ids=likers + avoiders,
                    summary=(
                        f"{_names(likers, names)} want this, "
                        f"{_names(avoiders, names)} avoid it"
                    ),
                    severity=0.8,
                )
            )

    if len(scored) >= 2:
        keenest = max(scored, key=lambda s: s.score)
        least = min(scored, key=lambda s: s.score)
        if keenest.score - least.score >= 35:
            conflicts.append(
                Conflict(
                    kind="disagreement",
                    member_ids=[keenest.member_id, least.member_id],
                    summary=(
                        f"{keenest.member_name} rates it {round(keenest.score)}, "
                        f"{least.member_name} rates it {round(least.score)}"
                    ),
                    severity=0.6,
                )
            )

    if atype:
        for member_id, conditions in conditions_by_member.items():
            for condition in conditions:
                if condition.status == "fixed" and atype in condition.text.lower():
                    conflicts.append(
                        Conflict(
                            kind="fixed_condition",
                            member_ids=[member_id],
                            summary=(
                                f"{names.get(member_id, 'someone')} has a fixed limit "
                                f"that mentions {atype}"
                            ),
                            severity=1.0,
                        )
                    )

    return conflicts

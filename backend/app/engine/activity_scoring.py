from typing import Optional

from app.engine.scoring import MemberProfile, ScoredMember
from app.models import Activity, Rating


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

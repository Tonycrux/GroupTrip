from enum import Enum


class ConditionType(str, Enum):
    budget = "budget"
    climate = "climate"
    activity = "activity"
    travel_time = "travel_time"
    other = "other"


class ConditionStatus(str, Enum):
    fixed = "fixed"
    flexible = "flexible"


class Source(str, Enum):
    explicit = "explicit"
    inferred = "inferred"


class ProfileFieldKey(str, Enum):
    budget_max = "budget_max"
    climates = "climates"
    activities = "activities"
    travel_time_max_hours = "travel_time_max_hours"
    likes = "likes"
    dislikes = "dislikes"


class RatingValue(str, Enum):
    interested = "interested"
    interested_if = "interested_if"
    not_interested = "not_interested"
    skipped = "skipped"


class RankingStrategy(str, Enum):
    average = "average"
    maximin = "maximin"
    balanced = "balanced"
    avoid_dislikes = "avoid_dislikes"
    complementary = "complementary"


class ChangeType(str, Enum):
    activity_changed = "activity_changed"
    condition_changed = "condition_changed"
    unresolved = "unresolved"


class ConflictStatus(str, Enum):
    open = "open"
    resolved = "resolved"
    unresolved = "unresolved"


class PlanItemStatus(str, Enum):
    proposed = "proposed"
    confirmed = "confirmed"
    rejected = "rejected"


class RequestStatus(str, Enum):
    open = "open"
    addressed = "addressed"
    declined = "declined"


class InterfaceVariant(str, Enum):
    comparison = "comparison"
    conflict_aware = "conflict_aware"


class SessionStatus(str, Enum):
    planned = "planned"
    running = "running"
    completed = "completed"


class TaskStatus(str, Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"

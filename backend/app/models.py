from datetime import date, datetime, time, timezone
from typing import Any, Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.enums import (
    ChangeType,
    ConditionStatus,
    ConditionType,
    InterfaceVariant,
    PlanItemStatus,
    RankingStrategy,
    RatingValue,
    RequestStatus,
    SessionStatus,
    Source,
    TaskStatus,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Study / evaluation
# --------------------------------------------------------------------------- #


class Participant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class StudySession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    label: str
    counterbalance_order: str = "comparison_first"
    status: str = SessionStatus.planned.value
    created_at: datetime = Field(default_factory=utcnow)


class Scenario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    label: str
    description: str = ""
    injected_change: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


class TaskInstance(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="studysession.id", index=True)
    scenario_id: Optional[int] = Field(default=None, foreign_key="scenario.id")
    variant: str = InterfaceVariant.comparison.value
    order_index: int = 1
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    status: str = TaskStatus.not_started.value


class EventLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_instance_id: int = Field(foreign_key="taskinstance.id", index=True)
    member_id: Optional[int] = Field(default=None, foreign_key="member.id")
    type: str = ""
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    at: datetime = Field(default_factory=utcnow)


class SurveyResponse(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_instance_id: int = Field(foreign_key="taskinstance.id", index=True)
    participant_id: int = Field(foreign_key="participant.id", index=True)
    question_key: str = ""
    value: str = ""
    at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------- #
# Core planning
# --------------------------------------------------------------------------- #


class Trip(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_instance_id: Optional[int] = Field(default=None, foreign_key="taskinstance.id")
    name: str
    origin: str = "Toronto"
    days: int = 3
    start_date: Optional[date] = None
    ranking_strategy: str = RankingStrategy.average.value
    selected_destination_id: Optional[int] = Field(default=None, foreign_key="destination.id")
    created_at: datetime = Field(default_factory=utcnow)


class Member(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trip_id: int = Field(foreign_key="trip.id", index=True)
    participant_id: Optional[int] = Field(default=None, foreign_key="participant.id")
    name: str
    email: Optional[str] = None
    is_owner: bool = False
    joined_at: datetime = Field(default_factory=utcnow)


class ProfileField(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    member_id: int = Field(foreign_key="member.id", index=True)
    field: str
    value: Any = Field(default=None, sa_column=Column(JSON))
    source: str = Source.explicit.value
    confidence: Optional[float] = None
    updated_at: datetime = Field(default_factory=utcnow)


class Condition(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trip_id: int = Field(foreign_key="trip.id", index=True)
    member_id: int = Field(foreign_key="member.id", index=True)
    text: str
    type: str = ConditionType.other.value
    status: str = ConditionStatus.flexible.value
    source: str = Source.explicit.value
    linked_plan_element: Optional[str] = None
    confirmed_by_owner_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)


class Destination(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    region: str = ""
    country: str = ""
    climate: str = ""
    dest_type: str = ""
    est_cost: float = 0.0
    travel_time_hours: float = 0.0
    activities: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    description: str = ""
    image_url: Optional[str] = None


class Activity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    destination_id: int = Field(foreign_key="destination.id", index=True)
    name: str
    type: str = ""
    est_cost: float = 0.0
    duration_hours: float = 1.0
    open_from: Optional[time] = None
    open_to: Optional[time] = None
    travel_time_min: int = 0
    description: str = ""


class Rating(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    member_id: int = Field(foreign_key="member.id", index=True)
    destination_id: Optional[int] = Field(default=None, foreign_key="destination.id")
    activity_id: Optional[int] = Field(default=None, foreign_key="activity.id")
    value: str = RatingValue.skipped.value
    reason: Optional[str] = None
    condition_id: Optional[int] = Field(default=None, foreign_key="condition.id")
    created_at: datetime = Field(default_factory=utcnow)


class Veto(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    member_id: int = Field(foreign_key="member.id", index=True)
    destination_id: int = Field(foreign_key="destination.id", index=True)
    reason: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class Approval(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trip_id: int = Field(foreign_key="trip.id", index=True)
    member_id: int = Field(foreign_key="member.id", index=True)
    approved_at: datetime = Field(default_factory=utcnow)


class Conflict(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trip_id: int = Field(foreign_key="trip.id", index=True)
    destination_id: Optional[int] = Field(default=None, foreign_key="destination.id")
    kind: str = ""
    member_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    summary: str = ""
    severity: float = 0.0
    status: str = "open"
    detected_at: datetime = Field(default_factory=utcnow)


class PlanItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trip_id: int = Field(foreign_key="trip.id", index=True)
    activity_id: int = Field(foreign_key="activity.id")
    day_index: int = 0
    start_minute: Optional[int] = None
    locked: bool = False
    status: str = PlanItemStatus.proposed.value
    created_at: datetime = Field(default_factory=utcnow)


class ActivityRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trip_id: int = Field(foreign_key="trip.id", index=True)
    member_id: int = Field(foreign_key="member.id", index=True)
    plan_item_id: Optional[int] = Field(default=None, foreign_key="planitem.id")
    activity_id: Optional[int] = Field(default=None, foreign_key="activity.id")
    text: str = ""
    status: str = RequestStatus.open.value
    created_at: datetime = Field(default_factory=utcnow)


class RevisionLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trip_id: int = Field(foreign_key="trip.id", index=True)
    member_id: Optional[int] = Field(default=None, foreign_key="member.id")
    conflict_id: Optional[int] = Field(default=None, foreign_key="conflict.id")
    change_type: str = ChangeType.unresolved.value
    description: str = ""
    affected_member_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    affected_condition_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


class RankingSnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trip_id: int = Field(foreign_key="trip.id", index=True)
    strategy: str = RankingStrategy.average.value
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)

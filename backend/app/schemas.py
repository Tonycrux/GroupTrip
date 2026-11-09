from datetime import date, datetime, time
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, model_validator

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

ORM = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- #
# Study / evaluation
# --------------------------------------------------------------------------- #


class ParticipantCreate(BaseModel):
    name: str
    email: Optional[str] = None


class ParticipantRead(BaseModel):
    model_config = ORM
    id: int
    name: str
    email: Optional[str]


class SessionCreate(BaseModel):
    label: str
    counterbalance_order: str = "comparison_first"
    status: SessionStatus = SessionStatus.planned


class SessionUpdate(BaseModel):
    label: Optional[str] = None
    counterbalance_order: Optional[str] = None
    status: Optional[SessionStatus] = None


class SessionRead(BaseModel):
    model_config = ORM
    id: int
    label: str
    counterbalance_order: str
    status: str


class ScenarioCreate(BaseModel):
    label: str
    description: str = ""
    injected_change: dict = {}


class ScenarioRead(BaseModel):
    model_config = ORM
    id: int
    label: str
    description: str
    injected_change: dict


class TaskInstanceCreate(BaseModel):
    session_id: int
    scenario_id: Optional[int] = None
    variant: InterfaceVariant = InterfaceVariant.comparison
    order_index: int = 1


class TaskInstanceUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class TaskInstanceRead(BaseModel):
    model_config = ORM
    id: int
    session_id: int
    scenario_id: Optional[int]
    variant: str
    order_index: int
    status: str


class EventLogCreate(BaseModel):
    task_instance_id: int
    member_id: Optional[int] = None
    type: str
    payload: dict = {}


class EventLogRead(BaseModel):
    model_config = ORM
    id: int
    task_instance_id: int
    member_id: Optional[int]
    type: str
    payload: dict


class SurveyResponseCreate(BaseModel):
    task_instance_id: int
    participant_id: int
    question_key: str
    value: str


class SurveyResponseRead(BaseModel):
    model_config = ORM
    id: int
    task_instance_id: int
    participant_id: int
    question_key: str
    value: str


# --------------------------------------------------------------------------- #
# Core planning
# --------------------------------------------------------------------------- #


class TripCreate(BaseModel):
    name: str
    origin: str = "Toronto"
    days: int = 3
    start_date: Optional[date] = None
    ranking_strategy: RankingStrategy = RankingStrategy.average
    task_instance_id: Optional[int] = None


class TripUpdate(BaseModel):
    name: Optional[str] = None
    origin: Optional[str] = None
    days: Optional[int] = None
    start_date: Optional[date] = None
    ranking_strategy: Optional[RankingStrategy] = None
    selected_destination_id: Optional[int] = None
    task_instance_id: Optional[int] = None


class TripRead(BaseModel):
    model_config = ORM
    id: int
    task_instance_id: Optional[int]
    name: str
    origin: str
    days: int
    start_date: Optional[date]
    ranking_strategy: str
    selected_destination_id: Optional[int]


class MemberCreate(BaseModel):
    name: str
    email: Optional[str] = None
    is_owner: bool = False
    participant_id: Optional[int] = None


class MemberRead(BaseModel):
    model_config = ORM
    id: int
    trip_id: int
    participant_id: Optional[int]
    name: str
    email: Optional[str]
    is_owner: bool


class ProfileFieldRead(BaseModel):
    model_config = ORM
    id: int
    member_id: int
    field: str
    value: Any
    source: str
    confidence: Optional[float]


class ProfileUpdate(BaseModel):
    budget_max: Optional[float] = None
    climates: Optional[list[str]] = None
    activities: Optional[list[str]] = None
    travel_time_max_hours: Optional[float] = None
    likes: Optional[list[str]] = None
    dislikes: Optional[list[str]] = None


class ProfileFieldSet(BaseModel):
    value: Any
    source: Source = Source.explicit
    confidence: Optional[float] = None


class ProfileRead(BaseModel):
    member_id: int
    budget_max: Optional[float] = None
    climates: list[str] = []
    activities: list[str] = []
    travel_time_max_hours: Optional[float] = None
    likes: list[str] = []
    dislikes: list[str] = []
    fields: list[ProfileFieldRead] = []


class ConditionCreate(BaseModel):
    member_id: int
    text: str
    type: ConditionType = ConditionType.other
    status: ConditionStatus = ConditionStatus.flexible
    source: Source = Source.explicit
    linked_plan_element: Optional[str] = None


class ConditionUpdate(BaseModel):
    text: Optional[str] = None
    status: Optional[ConditionStatus] = None
    linked_plan_element: Optional[str] = None


class ConditionRead(BaseModel):
    model_config = ORM
    id: int
    trip_id: int
    member_id: int
    text: str
    type: str
    status: str
    source: str
    linked_plan_element: Optional[str]
    confirmed_by_owner_at: Optional[datetime] = None


class DestinationRead(BaseModel):
    model_config = ORM
    id: int
    name: str
    region: str
    country: str
    climate: str
    dest_type: str
    est_cost: float
    travel_time_hours: float
    activities: list[str]
    description: str
    image_url: Optional[str]


class ActivityRead(BaseModel):
    model_config = ORM
    id: int
    destination_id: int
    name: str
    type: str
    est_cost: float
    duration_hours: float
    open_from: Optional[time]
    open_to: Optional[time]
    travel_time_min: int
    description: str


class RatingCreate(BaseModel):
    destination_id: Optional[int] = None
    activity_id: Optional[int] = None
    value: RatingValue
    reason: Optional[str] = None
    condition_id: Optional[int] = None

    @model_validator(mode="after")
    def exactly_one_target(self) -> "RatingCreate":
        has_dest = self.destination_id is not None
        has_activity = self.activity_id is not None
        if has_dest == has_activity:
            raise ValueError("provide exactly one of destination_id or activity_id")
        return self


class RatingRead(BaseModel):
    model_config = ORM
    id: int
    member_id: int
    destination_id: Optional[int]
    activity_id: Optional[int]
    value: str
    reason: Optional[str]
    condition_id: Optional[int]


class VetoCreate(BaseModel):
    member_id: int
    destination_id: int
    reason: Optional[str] = None


class VetoRead(BaseModel):
    model_config = ORM
    id: int
    member_id: int
    destination_id: int
    reason: Optional[str]


class ApprovalCreate(BaseModel):
    member_id: int


class ApprovalRead(BaseModel):
    model_config = ORM
    id: int
    trip_id: int
    member_id: int


class ApprovalStatus(BaseModel):
    approved_member_ids: list[int]
    pending_member_ids: list[int]
    fully_approved: bool


class ConflictRead(BaseModel):
    model_config = ORM
    id: int
    trip_id: int
    destination_id: Optional[int]
    kind: str
    member_ids: list[int]
    summary: str
    severity: float
    status: str


class ActivityRequestCreate(BaseModel):
    member_id: int
    plan_item_id: Optional[int] = None
    activity_id: Optional[int] = None
    text: str = ""


class ActivityRequestUpdate(BaseModel):
    status: RequestStatus


class ActivityRequestRead(BaseModel):
    model_config = ORM
    id: int
    trip_id: int
    member_id: int
    plan_item_id: Optional[int]
    activity_id: Optional[int]
    text: str
    status: str


class MemberScore(BaseModel):
    member_id: int
    member_name: str
    score: float
    hard_violations: list[str] = []
    reasons: list[str] = []


class Conflict(BaseModel):
    kind: str
    member_ids: list[int]
    summary: str
    severity: float


class DestinationRecommendation(BaseModel):
    destination: DestinationRead
    group_score: float
    strategy: RankingStrategy
    member_scores: list[MemberScore]
    conflicts: list[Conflict]
    vetoed_by: list[int] = []
    explanation: str


class PlanItemRead(BaseModel):
    model_config = ORM
    id: int
    trip_id: int
    activity_id: int
    day_index: int
    start_minute: Optional[int]
    locked: bool
    status: str


class UnscheduledRead(BaseModel):
    activity_id: int
    reason: str


class PlanRead(BaseModel):
    items: list[PlanItemRead]
    unscheduled: list[UnscheduledRead] = []
    per_day_budget: Optional[float] = None
    day_spend: list[float] = []


class RevisionCreate(BaseModel):
    member_id: Optional[int] = None
    conflict_id: Optional[int] = None
    change_type: ChangeType = ChangeType.unresolved
    description: str = ""
    affected_member_ids: list[int] = []
    affected_condition_ids: list[int] = []


class RevisionRead(BaseModel):
    model_config = ORM
    id: int
    trip_id: int
    member_id: Optional[int]
    conflict_id: Optional[int]
    change_type: str
    description: str
    affected_member_ids: list[int]
    affected_condition_ids: list[int]


class ChangePreviewRequest(BaseModel):
    activity_id: Optional[int] = None
    condition_id: Optional[int] = None
    new_status: Optional[ConditionStatus] = None


class ChangePreview(BaseModel):
    affected_member_ids: list[int]
    affected_condition_ids: list[int]
    requires_owner_confirmation: bool
    summary: str


class PlanItemUpdate(BaseModel):
    day_index: Optional[int] = None
    start_minute: Optional[int] = None
    locked: Optional[bool] = None
    status: Optional[PlanItemStatus] = None


class ActivityScoreRead(BaseModel):
    activity: ActivityRead
    member_scores: list[MemberScore]
    group_score: float
    rejected_by: list[int] = []
    conflicts: list[Conflict] = []


class BootstrapRead(BaseModel):
    """Everything a trip screen needs, in one round trip."""

    trip: TripRead
    members: list[MemberRead]
    profiles: list[ProfileRead]
    conditions: list[ConditionRead]
    approvals: ApprovalStatus
    vetoes: list[VetoRead]
    conflicts: list[ConflictRead]
    revisions: list[RevisionRead]
    plan: PlanRead
    ratings: list[RatingRead]
    requests: list[ActivityRequestRead] = []

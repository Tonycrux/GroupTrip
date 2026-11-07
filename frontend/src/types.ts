export type RankingStrategy =
  | "average"
  | "maximin"
  | "balanced"
  | "avoid_dislikes"
  | "complementary";

export type RatingValue = "interested" | "interested_if" | "not_interested" | "skipped";
export type ConditionType = "budget" | "climate" | "activity" | "travel_time" | "other";
export type ConditionStatus = "fixed" | "flexible";
export type Source = "explicit" | "inferred";
export type ChangeType = "activity_changed" | "condition_changed" | "unresolved";
export type ConflictStatus = "open" | "resolved" | "unresolved";
export type RequestStatus = "open" | "addressed" | "declined";
export type Variant = "plain" | "conflict";
/** How the backend names the two study conditions. */
export type StudyVariant = "comparison" | "conflict_aware";
export type Tab = "compare" | "people" | "plan" | "record";

export interface Trip {
  id: number;
  task_instance_id: number | null;
  name: string;
  origin: string;
  days: number;
  start_date: string | null;
  ranking_strategy: RankingStrategy;
  selected_destination_id: number | null;
}

export interface Member {
  id: number;
  trip_id: number;
  participant_id: number | null;
  name: string;
  email: string | null;
  is_owner: boolean;
}

export interface ProfileField {
  id: number;
  member_id: number;
  field: string;
  value: unknown;
  source: Source;
  confidence: number | null;
}

export interface Profile {
  member_id: number;
  budget_max: number | null;
  climates: string[];
  activities: string[];
  travel_time_max_hours: number | null;
  likes: string[];
  dislikes: string[];
  fields: ProfileField[];
}

export interface Condition {
  id: number;
  trip_id: number;
  member_id: number;
  text: string;
  type: ConditionType;
  status: ConditionStatus;
  source: Source;
  linked_plan_element: string | null;
  confirmed_by_owner_at: string | null;
}

export interface Destination {
  id: number;
  name: string;
  region: string;
  country: string;
  climate: string;
  dest_type: string;
  est_cost: number;
  travel_time_hours: number;
  activities: string[];
  description: string;
  image_url: string | null;
}

export interface Activity {
  id: number;
  destination_id: number;
  name: string;
  type: string;
  est_cost: number;
  duration_hours: number;
  open_from: string | null;
  open_to: string | null;
  travel_time_min: number;
  description: string;
}

export interface MemberScore {
  member_id: number;
  member_name: string;
  score: number;
  hard_violations: string[];
  reasons: string[];
}

export interface Conflict {
  kind: string;
  member_ids: number[];
  summary: string;
  severity: number;
}

export interface Recommendation {
  destination: Destination;
  group_score: number;
  strategy: RankingStrategy;
  member_scores: MemberScore[];
  conflicts: Conflict[];
  vetoed_by: number[];
  explanation: string;
}

export interface ActivityScore {
  activity: Activity;
  member_scores: MemberScore[];
  group_score: number;
  rejected_by: number[];
}

export interface Rating {
  id: number;
  member_id: number;
  destination_id: number | null;
  activity_id: number | null;
  value: RatingValue;
  reason: string | null;
  condition_id: number | null;
}

export interface Veto {
  id: number;
  member_id: number;
  destination_id: number;
  reason: string | null;
}

export interface ApprovalStatus {
  approved_member_ids: number[];
  pending_member_ids: number[];
  fully_approved: boolean;
}

export interface PersistedConflict {
  id: number;
  trip_id: number;
  destination_id: number | null;
  kind: string;
  member_ids: number[];
  summary: string;
  severity: number;
  status: ConflictStatus;
}

export interface PlanItem {
  id: number;
  trip_id: number;
  activity_id: number;
  day_index: number;
  start_minute: number | null;
  locked: boolean;
  status: string;
}

export interface Plan {
  items: PlanItem[];
  unscheduled_activity_ids: number[];
}

export interface ActivityRequest {
  id: number;
  trip_id: number;
  member_id: number;
  plan_item_id: number | null;
  activity_id: number | null;
  text: string;
  status: RequestStatus;
}

export interface ChangePreview {
  affected_member_ids: number[];
  affected_condition_ids: number[];
  requires_owner_confirmation: boolean;
  summary: string;
}

export interface Revision {
  id: number;
  trip_id: number;
  member_id: number | null;
  conflict_id: number | null;
  change_type: ChangeType;
  description: string;
  affected_member_ids: number[];
  affected_condition_ids: number[];
}

export interface Bootstrap {
  trip: Trip;
  members: Member[];
  profiles: Profile[];
  conditions: Condition[];
  approvals: ApprovalStatus;
  vetoes: Veto[];
  conflicts: PersistedConflict[];
  revisions: Revision[];
  plan: Plan;
  ratings: Rating[];
  requests: ActivityRequest[];
}

export interface TaskInstance {
  id: number;
  session_id: number;
  scenario_id: number | null;
  variant: StudyVariant;
  order_index: number;
  status: string;
}

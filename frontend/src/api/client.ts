import type {
  Activity,
  ActivityRequest,
  ActivityScore,
  ApprovalStatus,
  Bootstrap,
  ChangePreview,
  Condition,
  ConditionStatus,
  Destination,
  Member,
  PersistedConflict,
  Plan,
  PlanItem,
  Profile,
  RankingStrategy,
  Rating,
  Recommendation,
  Revision,
  TaskInstance,
  Trip,
  Veto,
} from "../types";

export type LlmExplanation = {
  source: "llm" | "template";
  errors: string[];
  headline: string;
  per_member: { member: string; line: string }[];
};

export type ParsedCondition = {
  type: string;
  operator: string | null;
  value: number | string | null;
  status: "fixed" | "flexible";
  text: string;
};

const BASE = "/api";

let actorId: number | null = null;

export function setActor(id: number | null): void {
  actorId = id;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (actorId !== null) headers["X-Member-Id"] = String(actorId);

  const res = await fetch(`${BASE}${path}`, { headers, ...init });
  if (!res.ok) {
    let detail = res.statusText || `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* keep status text */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const post = (body: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(body) });
const patch = (body: unknown): RequestInit => ({ method: "PATCH", body: JSON.stringify(body) });
const put = (body: unknown): RequestInit => ({ method: "PUT", body: JSON.stringify(body) });

export const api = {
  /* trips */
  listTrips: () => request<Trip[]>("/trips"),
  createTrip: (body: Partial<Trip>) => request<Trip>("/trips", post(body)),
  getTrip: (id: number) => request<Trip>(`/trips/${id}`),
  updateTrip: (id: number, body: Partial<Trip>) => request<Trip>(`/trips/${id}`, patch(body)),

  /* one round trip for a whole trip screen */
  bootstrap: (id: number) => request<Bootstrap>(`/trips/${id}/bootstrap`),

  /* members */
  listMembers: (tripId: number) => request<Member[]>(`/trips/${tripId}/members`),
  addMember: (tripId: number, body: { name: string; is_owner?: boolean }) =>
    request<Member>(`/trips/${tripId}/members`, post(body)),
  deleteMember: (memberId: number) =>
    request<void>(`/members/${memberId}`, { method: "DELETE" }),

  /* profile */
  getProfile: (memberId: number) => request<Profile>(`/members/${memberId}/profile`),
  saveProfile: (memberId: number, body: Partial<Profile>) =>
    request<Profile>(`/members/${memberId}/profile`, put(body)),
  setProfileField: (memberId: number, field: string, value: unknown, source = "explicit") =>
    request<Profile>(`/members/${memberId}/profile/${field}`, patch({ value, source })),

  /* conditions */
  listConditions: (tripId: number) => request<Condition[]>(`/trips/${tripId}/conditions`),
  createCondition: (
    tripId: number,
    body: { member_id: number; text: string; type: string; status: string },
  ) => request<Condition>(`/trips/${tripId}/conditions`, post(body)),
  updateCondition: (conditionId: number, body: { status?: ConditionStatus; text?: string }) =>
    request<Condition>(`/conditions/${conditionId}`, patch(body)),
  confirmCondition: (conditionId: number) =>
    request<Condition>(`/conditions/${conditionId}/confirm`, { method: "POST" }),
  deleteCondition: (conditionId: number) =>
    request<void>(`/conditions/${conditionId}`, { method: "DELETE" }),

  /* catalogue */
  listDestinations: () => request<Destination[]>("/destinations"),
  listActivities: (destinationId: number) =>
    request<Activity[]>(`/destinations/${destinationId}/activities`),
  activityScores: (tripId: number) =>
    request<ActivityScore[]>(`/trips/${tripId}/activities`),

  /* ratings */
  rate: (
    memberId: number,
    body: { destination_id?: number; activity_id?: number; value: string; reason?: string },
  ) => request<Rating>(`/members/${memberId}/ratings`, post(body)),
  listRatings: (memberId: number) => request<Rating[]>(`/members/${memberId}/ratings`),

  /* recommendations */
  recommendations: (tripId: number, strategy?: RankingStrategy) =>
    request<Recommendation[]>(
      `/trips/${tripId}/recommendations${strategy ? `?strategy=${strategy}` : ""}`,
    ),

  /* llm */
  llmExplanation: (tripId: number, destinationId: number, strategy?: string) =>
    request<LlmExplanation>(
      `/llm/trips/${tripId}/recommendations/${destinationId}/explanation${strategy ? `?strategy=${strategy}` : ""}`,
    ),
  llmParseCondition: (text: string) =>
    request<{ conditions: ParsedCondition[] }>("/llm/conditions/parse", post({ text })),
  llmAcceptConditions: (tripId: number, memberId: number, conditions: ParsedCondition[]) =>
    request<unknown>(`/llm/trips/${tripId}/members/${memberId}/conditions/accept`, post(conditions)),

  /* vetoes */
  createVeto: (tripId: number, body: { member_id: number; destination_id: number; reason?: string }) =>
    request<Veto>(`/trips/${tripId}/vetoes`, post(body)),
  listVetoes: (tripId: number) => request<Veto[]>(`/trips/${tripId}/vetoes`),
  deleteVeto: (vetoId: number) => request<void>(`/vetoes/${vetoId}`, { method: "DELETE" }),

  /* approvals */
  getApprovals: (tripId: number) => request<ApprovalStatus>(`/trips/${tripId}/approvals`),
  approve: (tripId: number, memberId: number) =>
    request<unknown>(`/trips/${tripId}/approvals`, post({ member_id: memberId })),
  withdrawApproval: (tripId: number, memberId: number) =>
    request<void>(`/trips/${tripId}/approvals/${memberId}`, { method: "DELETE" }),

  /* conflicts */
  detectConflicts: (tripId: number) =>
    request<PersistedConflict[]>(`/trips/${tripId}/conflicts/detect`, { method: "POST" }),
  listConflicts: (tripId: number) => request<PersistedConflict[]>(`/trips/${tripId}/conflicts`),
  setConflictStatus: (conflictId: number, status: string) =>
    request<PersistedConflict>(`/conflicts/${conflictId}?status=${encodeURIComponent(status)}`, {
      method: "PATCH",
    }),

  /* plan */
  getPlan: (tripId: number) => request<Plan>(`/trips/${tripId}/plan`),
  clearPlan: (tripId: number) =>
    request<void>(`/trips/${tripId}/plan`, { method: "DELETE" }),
  generatePlan: (tripId: number) =>
    request<Plan>(`/trips/${tripId}/plan/generate`, { method: "POST" }),
  replan: (tripId: number) =>
    request<Plan>(`/trips/${tripId}/plan/replan`, { method: "POST" }),
  updatePlanItem: (itemId: number, body: Partial<PlanItem>) =>
    request<PlanItem>(`/plan-items/${itemId}`, patch(body)),

  /* activity requests */
  listRequests: (tripId: number) => request<ActivityRequest[]>(`/trips/${tripId}/requests`),
  createRequest: (
    tripId: number,
    body: { member_id: number; plan_item_id?: number; activity_id?: number; text?: string },
  ) => request<ActivityRequest>(`/trips/${tripId}/requests`, post(body)),
  updateRequest: (requestId: number, status: string) =>
    request<ActivityRequest>(`/requests/${requestId}`, patch({ status })),

  /* change preview */
  previewChange: (tripId: number, body: { activity_id?: number; condition_id?: number }) =>
    request<ChangePreview>(`/trips/${tripId}/changes/preview`, post(body)),

  /* revisions */
  listRevisions: (tripId: number) => request<Revision[]>(`/trips/${tripId}/revisions`),
  createRevision: (tripId: number, body: Partial<Revision>) =>
    request<Revision>(`/trips/${tripId}/revisions`, post(body)),

  /* study */
  getTask: (taskId: number) => request<TaskInstance>(`/tasks/${taskId}`),
  taskTrip: (taskId: number) => request<Trip>(`/tasks/${taskId}/trip`),
  logEvent: (body: {
    task_instance_id: number;
    member_id?: number | null;
    type: string;
    payload?: Record<string, unknown>;
  }) => request<unknown>("/events", post(body)),
  submitSurvey: (body: {
    task_instance_id: number;
    participant_id: number;
    question_key: string;
    value: string;
  }) => request<unknown>("/surveys", post(body)),
};

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";

import { api, ApiError, setActor } from "../api/client";
import type {
  Bootstrap,
  ChangePreview,
  ConditionStatus,
  Member,
  PlanItem,
  Profile,
  RankingStrategy,
  RatingValue,
  Recommendation,
  Revision,
  TaskInstance,
  Variant,
} from "../types";

const VIEW_KEY = "grouptrip.variant";

interface AppCtx {
  ready: boolean;
  tripId: number | null;

  bundle: Bootstrap | null;
  recs: Recommendation[];
  loading: boolean;
  error: string | null;
  clearError: () => void;
  reload: () => Promise<void>;

  actorId: number | null;
  actor: Member | null;
  setActorId: (id: number) => void;

  variant: Variant;
  setVariant: (v: Variant) => void;
  conflict: boolean;

  strategy: RankingStrategy;
  setStrategy: (s: RankingStrategy) => Promise<void>;

  task: TaskInstance | null;

  addMember: (name: string) => Promise<void>;
  rateDestination: (destinationId: number, value: RatingValue, reason?: string) => Promise<void>;
  veto: (destinationId: number) => Promise<void>;
  unveto: (destinationId: number) => Promise<void>;
  approve: (memberId: number) => Promise<void>;
  withdraw: (memberId: number) => Promise<void>;
  saveProfile: (memberId: number, fields: Partial<Profile>) => Promise<void>;
  addCondition: (body: { text: string; type: string; status: ConditionStatus }) => Promise<void>;
  setConditionStatus: (id: number, status: ConditionStatus) => Promise<void>;
  chooseDestination: (id: number) => Promise<void>;
  generatePlan: () => Promise<void>;
  toggleLock: (item: PlanItem) => Promise<void>;
  rateActivity: (activityId: number, value: RatingValue) => Promise<void>;
  requestAlternative: (activityId: number, text: string) => Promise<void>;
  previewCondition: (conditionId: number) => Promise<ChangePreview>;
  detectConflicts: () => Promise<void>;
  resolveConflict: (id: number) => Promise<void>;
  logRevision: (body: Partial<Revision>) => Promise<void>;
  survey: (question: string, value: string) => Promise<void>;
}

const Ctx = createContext<AppCtx | null>(null);

const initialVariant = (): Variant =>
  localStorage.getItem(VIEW_KEY) === "plain" ? "plain" : "conflict";

const taskFromUrl = (): number | null => {
  const param = new URLSearchParams(window.location.search).get("task");
  return param ? Number(param) : null;
};

export function AppProvider({
  tripId: tripIdProp,
  children,
}: {
  tripId: number;
  children: ReactNode;
}) {
  // The URL owns which trip is open; the rest of the app only reads it.
  const tripId: number | null = tripIdProp;
  const navigate = useNavigate();

  const [bundle, setBundle] = useState<Bootstrap | null>(null);
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  const [actorId, setActorIdState] = useState<number | null>(null);
  const [variant, setVariantState] = useState<Variant>(initialVariant);
  const [strategy, setStrategyState] = useState<RankingStrategy>("average");
  const [task, setTask] = useState<TaskInstance | null>(null);

  const strategyRef = useRef<RankingStrategy>("average");
  strategyRef.current = strategy;

  const fail = useCallback((e: unknown) => {
    setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Something went wrong");
  }, []);

  const load = useCallback(async (id: number, strat: RankingStrategy) => {
    const [b, r] = await Promise.all([api.bootstrap(id), api.recommendations(id, strat)]);
    setBundle(b);
    setRecs(r);
    setStrategyState(b.trip.ranking_strategy);
    return b;
  }, []);

  const reload = useCallback(async () => {
    if (tripId === null) {
      setBundle(null);
      setRecs([]);
      setReady(true);
      return;
    }
    setLoading(true);
    try {
      await load(tripId, strategyRef.current);
      setError(null);
    } catch (e) {
      // A trip that no longer exists sends you back to the trip list, rather than
      // leaving the screen stuck on a spinner.
      if (e instanceof ApiError && e.status === 404) {
        navigate("/");
      }
      fail(e);
    } finally {
      setLoading(false);
      setReady(true);
    }
  }, [tripId, load, fail, navigate]);

  /* boot: load the trip, then any study task attached via ?task= */
  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    const id = taskFromUrl();
    if (!id) return;
    api
      .getTask(id)
      .then((t) => {
        setTask(t);
        setVariantState(t.variant === "conflict_aware" ? "conflict" : "plain");
      })
      .catch(() => {
        /* a stale task link shouldn't block the trip */
      });
  }, []);

  /* sync the acting member */
  useEffect(() => {
    if (bundle && actorId === null && bundle.members.length > 0) {
      setActorIdState(bundle.members[0].id);
    }
  }, [bundle, actorId]);

  useEffect(() => {
    setActor(actorId);
  }, [actorId]);

  useEffect(() => {
    localStorage.setItem(VIEW_KEY, variant);
  }, [variant]);

  const logEvent = useCallback(
    (type: string, payload: Record<string, unknown> = {}) => {
      if (!task) return;
      void api
        .logEvent({ task_instance_id: task.id, member_id: actorId, type, payload })
        .catch(() => undefined);
    },
    [task, actorId],
  );

  const run = useCallback(
    async (action: () => Promise<unknown>, event?: string, payload?: Record<string, unknown>) => {
      try {
        await action();
        if (event) logEvent(event, payload);
        await reload();
      } catch (e) {
        fail(e);
      }
    },
    [reload, fail, logEvent],
  );

  /* ── actions ─────────────────────────────────────────── */
  const addMember = useCallback(
    (name: string) =>
      run(() => api.addMember(tripId as number, { name, is_owner: !bundle?.members.length }), "member added", {
        name,
      }),
    [run, tripId, bundle],
  );

  const rateDestination = useCallback(
    (destinationId: number, value: RatingValue, reason?: string) =>
      run(
        () => api.rate(actorId as number, { destination_id: destinationId, value, reason }),
        "rating",
        { destination_id: destinationId, value },
      ),
    [run, actorId],
  );

  const veto = useCallback(
    (destinationId: number) =>
      run(
        () =>
          api.createVeto(tripId as number, {
            member_id: actorId as number,
            destination_id: destinationId,
          }),
        "veto",
        { destination_id: destinationId },
      ),
    [run, tripId, actorId],
  );

  const unveto = useCallback(
    (destinationId: number) => {
      const found = bundle?.vetoes.find(
        (v) => v.member_id === actorId && v.destination_id === destinationId,
      );
      if (!found) return Promise.resolve();
      return run(() => api.deleteVeto(found.id), "veto withdrawn", { destination_id: destinationId });
    },
    [bundle, actorId, run],
  );

  const approve = useCallback(
    (memberId: number) => run(() => api.approve(tripId as number, memberId), "approved"),
    [run, tripId],
  );

  const withdraw = useCallback(
    (memberId: number) => run(() => api.withdrawApproval(tripId as number, memberId), "approval withdrawn"),
    [run, tripId],
  );

  const saveProfile = useCallback(
    (memberId: number, fields: Partial<Profile>) =>
      run(() => api.saveProfile(memberId, fields), "profile updated"),
    [run],
  );

  const addCondition = useCallback(
    (body: { text: string; type: string; status: ConditionStatus }) =>
      run(
        () => api.createCondition(tripId as number, { ...body, member_id: actorId as number }),
        "condition added",
        body,
      ),
    [run, tripId, actorId],
  );

  const setConditionStatus = useCallback(
    (id: number, status: ConditionStatus) =>
      run(() => api.updateCondition(id, { status }), "condition changed", { status }),
    [run],
  );

  const chooseDestination = useCallback(
    (id: number) =>
      run(
        async () => {
          // A timetable belongs to one destination, so switching throws it away
          // rather than leaving rows that point at places elsewhere.
          const current = bundle?.trip.selected_destination_id ?? null;
          if (current !== id) await api.clearPlan(tripId as number);
          await api.updateTrip(tripId as number, { selected_destination_id: id });
        },
        "destination chosen",
        { destination_id: id },
      ),
    [run, tripId, bundle],
  );

  const generatePlan = useCallback(
    () => run(() => api.generatePlan(tripId as number), "plan generated"),
    [run, tripId],
  );

  const toggleLock = useCallback(
    (item: PlanItem) =>
      run(() => api.updatePlanItem(item.id, { locked: !item.locked }), "plan item toggled", {
        plan_item_id: item.id,
      }),
    [run],
  );

  const rateActivity = useCallback(
    (activityId: number, value: RatingValue) =>
      run(() => api.rate(actorId as number, { activity_id: activityId, value }), "activity rating", {
        activity_id: activityId,
        value,
      }),
    [run, actorId],
  );

  const requestAlternative = useCallback(
    (activityId: number, text: string) =>
      run(
        () => api.createRequest(tripId as number, { member_id: actorId as number, activity_id: activityId, text }),
        "alternative requested",
        { activity_id: activityId },
      ),
    [run, tripId, actorId],
  );

  const previewCondition = useCallback(
    (conditionId: number) => api.previewChange(tripId as number, { condition_id: conditionId }),
    [tripId],
  );

  const detectConflicts = useCallback(
    () => run(() => api.detectConflicts(tripId as number), "conflicts detected"),
    [run, tripId],
  );

  const resolveConflict = useCallback(
    (id: number) =>
      run(() => api.setConflictStatus(id, "resolved"), "conflict resolved", { conflict_id: id }),
    [run],
  );

  const logRevision = useCallback(
    (body: Partial<Revision>) =>
      run(
        () => api.createRevision(tripId as number, { member_id: actorId, ...body }),
        "revision logged",
      ),
    [run, tripId, actorId],
  );

  const survey = useCallback(
    async (question: string, value: string) => {
      if (!task) return;
      const participant = bundle?.members.find((m) => m.id === actorId)?.participant_id;
      if (!participant) return;
      try {
        await api.submitSurvey({
          task_instance_id: task.id,
          participant_id: participant,
          question_key: question,
          value,
        });
      } catch (e) {
        fail(e);
      }
    },
    [task, bundle, actorId, fail],
  );

  const setStrategy = useCallback(
    async (s: RankingStrategy) => {
      setStrategyState(s);
      if (tripId === null) return;
      try {
        await api.updateTrip(tripId, { ranking_strategy: s });
        setRecs(await api.recommendations(tripId, s));
        setBundle(await api.bootstrap(tripId));
        logEvent("strategy changed", { strategy: s });
      } catch (e) {
        fail(e);
      }
    },
    [tripId, logEvent, fail],
  );

  const actor = useMemo(
    () => bundle?.members.find((m) => m.id === actorId) ?? null,
    [bundle, actorId],
  );

  const value = useMemo<AppCtx>(
    () => ({
      ready,
      tripId,
      bundle,
      recs,
      loading,
      error,
      clearError: () => setError(null),
      reload,
      actorId,
      actor,
      setActorId: setActorIdState,
      variant,
      setVariant: setVariantState,
      conflict: variant === "conflict",
      strategy,
      setStrategy,
      task,
      addMember,
      rateDestination,
      veto,
      unveto,
      approve,
      withdraw,
      saveProfile,
      addCondition,
      setConditionStatus,
      chooseDestination,
      generatePlan,
      toggleLock,
      rateActivity,
      requestAlternative,
      previewCondition,
      detectConflicts,
      resolveConflict,
      logRevision,
      survey,
    }),
    [
      ready, tripId, bundle, recs, loading, error, reload, actorId, actor, variant,
      strategy, setStrategy, task, addMember, rateDestination, veto, unveto, approve,
      withdraw, saveProfile, addCondition, setConditionStatus, chooseDestination, generatePlan,
      toggleLock, rateActivity, requestAlternative, previewCondition, detectConflicts,
      resolveConflict, logRevision, survey,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useApp must be used inside AppProvider");
  return ctx;
}

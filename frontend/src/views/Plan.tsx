import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { useApp } from "../state/AppState";
import { useDialog } from "../components/DialogProvider";
import type { ActivityScore, ChangePreview, PlanItem, RatingValue } from "../types";
import { Banner, Empty, Skeleton, bandColor, initials } from "../components/ui";

const time = (m: number | null) => {
  if (m == null) return "--:--";
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
};

export default function Plan() {
  const {
    bundle,
    recs,
    actorId,
    tripId,
    conflict,
    generatePlan,
    toggleLock,
    rateActivity,
    requestAlternative,
    reload,
  } = useApp();
  const { promptText } = useDialog();
  const navigate = useNavigate();

  const [scores, setScores] = useState<ActivityScore[]>([]);
  const [actLoading, setActLoading] = useState(false);
  const [preview, setPreview] = useState<{ item: PlanItem; info: ChangePreview } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const destId = bundle?.trip.selected_destination_id ?? null;

  const loadScores = useCallback(async () => {
    if (tripId == null || destId == null) {
      setScores([]);
      return;
    }
    setActLoading(true);
    try {
      setScores(await api.activityScores(tripId));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load activities");
    } finally {
      setActLoading(false);
    }
    // Runs again whenever the trip bundle changes, so a fresh vote updates the numbers.
  }, [tripId, destId, bundle]);

  useEffect(() => {
    void loadScores();
  }, [loadScores]);

  const byId = useMemo(
    () => new Map(scores.map((s) => [s.activity.id, s.activity])),
    [scores],
  );
  const rec = recs.find((r) => r.destination.id === destId) ?? null;

  if (!bundle) return null;

  if (destId == null) {
    return (
      <div className="card">
        <Empty
          title="No destination yet"
          note="Pick somewhere in Compare and the plan opens here."
          action={
            <button
              type="button"
              className="btn go"
              onClick={() => navigate(`/trips/${tripId}/compare`)}
            >
              Go to Compare
            </button>
          }
        />
      </div>
    );
  }

  const items = bundle.plan.items;
  const days = Math.max(bundle.trip.days, 1);
  const unscheduled = new Set(bundle.plan.unscheduled_activity_ids);

  // Rows whose activity isn't at the current destination are leftovers from an older
  // plan. Never render them as bare numbers; say so instead.
  const knownItems = items.filter((i) => byId.has(i.activity_id));
  const staleCount = actLoading ? 0 : items.length - knownItems.length;

  // A change is blocked only when it touches a fixed limit that belongs to somebody
  // else. If the limit is your own, confirming the change is your call to make.
  const blocking = preview
    ? preview.info.affected_condition_ids
        .map((id) => bundle.conditions.find((c) => c.id === id))
        .filter((c) => c !== undefined && c.status === "fixed" && c.member_id !== actorId)
    : [];
  const blockerNames = Array.from(
    new Set(blocking.map((c) => bundle.members.find((m) => m.id === c!.member_id)?.name ?? "someone")),
  );

  const askPreview = async (item: PlanItem) => {
    if (tripId == null) return;
    try {
      const info = await api.previewChange(tripId, { activity_id: item.activity_id });
      setPreview({ item, info });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not preview");
    }
  };

  const applyRemoval = async () => {
    if (!preview || tripId == null) return;
    const name = byId.get(preview.item.activity_id)?.name ?? "activity";
    try {
      await api.updatePlanItem(preview.item.id, { status: "rejected" });
      await api.createRevision(tripId, {
        member_id: actorId,
        change_type: "activity_changed",
        description: `Removed ${name}`,
        affected_member_ids: preview.info.affected_member_ids,
        affected_condition_ids: preview.info.affected_condition_ids,
      });
      setPreview(null);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not apply the change");
    }
  };

  const rate = (activityId: number, value: RatingValue) => void rateActivity(activityId, value);

  // Manual reshuffle: drop a row onto another day and put it after whatever is already there.
  const moveToDay = async (item: PlanItem, day: number) => {
    if (tripId == null) return;
    const DAY_START = 9 * 60;
    const others = bundle.plan.items.filter(
      (i) => i.id !== item.id && i.day_index === day && i.status !== "rejected",
    );
    const start = others.reduce((latest, i) => {
      const a = byId.get(i.activity_id);
      const minutes = a ? Math.round(a.duration_hours * 60) : 60;
      return Math.max(latest, (i.start_minute ?? DAY_START) + minutes + (a?.travel_time_min ?? 0));
    }, DAY_START);
    try {
      await api.updatePlanItem(item.id, { day_index: day, start_minute: start });
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not move that activity");
    }
  };

  return (
    <>
      <div className="toolbar">
        <div>
          <h1 className="h1">Plan</h1>
          <div className="sub">
            {rec?.destination.name ?? "Selected destination"} · {days} days
          </div>
        </div>
        <div className="hstack" style={{ marginLeft: "auto" }}>
          <button
            type="button"
            className="btn"
            onClick={() => navigate(`/trips/${tripId}/compare`)}
          >
            Change destination
          </button>
          <button type="button" className="btn go" onClick={() => void generatePlan()}>
            {items.length ? "Rebuild plan" : "Build plan"}
          </button>
        </div>
      </div>

      {(error || unscheduled.size > 0) && (
        <Banner
          tone={error ? "bad" : "info"}
          title={error ? "Something failed." : "Some activities didn't fit."}
          note={error ?? `${unscheduled.size} left out of the timetable.`}
        />
      )}

      {staleCount > 0 && (
        <Banner
          tone="info"
          title="This timetable was built for a different destination."
          note={`${staleCount} row(s) belong somewhere else and are hidden. Rebuild the plan for the place you picked.`}
        />
      )}

      {preview && (
        <div className="note note-warn" style={{ marginBottom: 14 }}>
          <strong>Before you apply this</strong>
          <div style={{ marginTop: 6 }}>{preview.info.summary}</div>
          <div className="chipset" style={{ marginTop: 8 }}>
            <span className="hint">
              {blocking.length > 0
                ? `This touches a fixed limit set by ${blockerNames.join(" and ")}. Only they can confirm it.`
                : preview.info.requires_owner_confirmation
                  ? "This touches your own fixed limit, so it is yours to confirm."
                  : `${preview.info.affected_member_ids.length} member(s) affected.`}
            </span>
          </div>
          <div className="chipset" style={{ marginTop: 8 }}>
            <button
              type="button"
              className="btn sm go"
              disabled={blocking.length > 0}
              onClick={() => void applyRemoval()}
            >
              {preview.info.requires_owner_confirmation ? "Confirm and apply" : "Apply"}
            </button>
            <button type="button" className="btn sm" onClick={() => setPreview(null)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-pad">
          <h3 className="sec">Timetable</h3>
          {actLoading ? (
            <p className="hint">Loading activities…</p>
          ) : items.length === 0 ? (
            <p className="hint">No plan yet. Build one from the activities below.</p>
          ) : (
            Array.from({ length: days }).map((_, day) => {
              const dayItems = knownItems
                .filter((i) => i.day_index === day && i.status !== "rejected")
                .sort((a, b) => (a.start_minute ?? 0) - (b.start_minute ?? 0));
              return (
                <div key={day} className="dayblock">
                  <div className="dayhead">Day {day + 1}</div>
                  {dayItems.length === 0 ? (
                    <p className="hint">Nothing scheduled.</p>
                  ) : (
                    dayItems.map((i) => {
                      const a = byId.get(i.activity_id);
                      return (
                        <div className="planrow" key={i.id}>
                          <span className="planrow-time n">{time(i.start_minute)}</span>
                          <span className="planrow-name">{a?.name ?? "Unknown activity"}</span>
                          {a && (
                            <span className="meta">
                              <span className="planrow-type">{a.type}</span>
                              <span>·</span>
                              <span className="n">${Math.round(a.est_cost)}</span>
                              <span>·</span>
                              <span className="n">{a.duration_hours}h</span>
                              <span>·</span>
                              <span className="n">{a.travel_time_min}m</span>
                            </span>
                          )}
                          <span className="planrow-actions">
                            <select
                              className="daypick"
                              aria-label={`Move ${a?.name ?? "this activity"} to another day`}
                              value={i.day_index}
                              onChange={(e) => void moveToDay(i, Number(e.target.value))}
                            >
                              {Array.from({ length: days }).map((_, d) => (
                                <option key={d} value={d}>
                                  Day {d + 1}
                                </option>
                              ))}
                            </select>
                            <button
                              type="button"
                              className="btn sm"
                              title="A locked row stays put when the plan is rebuilt"
                              onClick={() => void toggleLock(i)}
                            >
                              {i.locked ? "Unlock" : "Lock"}
                            </button>
                            <button type="button" className="btn sm stop" onClick={() => void askPreview(i)}>
                              Remove
                            </button>
                          </span>
                        </div>
                      );
                    })
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="card-pad">
          <h3 className="sec">Activities here</h3>
          {actLoading ? (
            <div className="stack-8">
              <Skeleton w="70%" />
              <Skeleton w="55%" />
              <Skeleton w="62%" />
            </div>
          ) : scores.length === 0 ? (
            <p className="hint">No activities for this destination.</p>
          ) : (
            scores.map((row) => {
              const a = row.activity;
              const mine = bundle.ratings.find(
                (r) => r.member_id === actorId && r.activity_id === a.id,
              );
              const rejectedNames = row.rejected_by
                .map((id) => bundle.members.find((m) => m.id === id)?.name)
                .filter(Boolean)
                .join(", ");
              return (
                <div
                  className={`actrow${row.rejected_by.length ? " actrow-out" : ""}`}
                  key={a.id}
                >
                  <div className="actrow-main">
                    <span className="actrow-name">{a.name}</span>
                    <span className="meta">
                      <span>{a.type}</span>
                      <span>·</span>
                      <span className="n">${Math.round(a.est_cost)}</span>
                      <span>·</span>
                      <span className="n">{a.duration_hours}h</span>
                      <span>·</span>
                      <span className="n">{a.travel_time_min}m</span>
                      {unscheduled.has(a.id) && <span className="chip chip-mid">didn't fit</span>}
                      {row.rejected_by.length > 0 && (
                        <span
                          className="chip chip-bad"
                          title={`${rejectedNames} said no, so it is left out of the plan`}
                        >
                          left out
                        </span>
                      )}
                    </span>
                    {conflict && (
                      <span className="actrow-scores">
                        {row.member_scores.map((m) => (
                          <span
                            className="mini"
                            key={m.member_id}
                            title={`${m.member_name}: ${Math.round(m.score)}/100${
                              m.reasons.length ? ` — ${m.reasons[0]}` : ""
                            }`}
                          >
                            <span className="mini-i">{initials(m.member_name)}</span>
                            <span className="mini-v" style={{ color: bandColor(m.score) }}>
                              {Math.round(m.score)}
                            </span>
                          </span>
                        ))}
                      </span>
                    )}
                  </div>
                  <div className="chipset">
                    <button
                      type="button"
                      className={`btn sm${mine?.value === "interested" ? " go" : ""}`}
                      onClick={() => rate(a.id, "interested")}
                    >
                      In
                    </button>
                    <button
                      type="button"
                      className={`btn sm${mine?.value === "not_interested" ? " go" : ""}`}
                      onClick={() => rate(a.id, "not_interested")}
                    >
                      Out
                    </button>
                    <button
                      type="button"
                      className="btn sm"
                      onClick={async () => {
                        const text = await promptText({
                          title: "Ask for something else",
                          label: `What would you rather do than ${a.name}?`,
                          placeholder: "e.g. a walk along the water instead",
                          help: "This is saved as a suggestion the group can see. It does not change the plan by itself.",
                          confirmLabel: "Send suggestion",
                          multiline: true,
                        });
                        if (text) void requestAlternative(a.id, text);
                      }}
                    >
                      Alt
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {conflict && (
        <p className="hint" style={{ marginTop: 12 }}>
          Removing a plan item records whether the conflict was resolved by changing the plan.
        </p>
      )}
    </>
  );
}

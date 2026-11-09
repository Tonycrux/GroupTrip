import { useEffect, useMemo, useState } from "react";

import { useApp } from "../state/AppState";
import { useDialog } from "../components/DialogProvider";
import type { ConditionStatus, ConditionType } from "../types";
import { Avatar, Chip, Empty } from "../components/ui";
import MultiSelect from "../components/MultiSelect";

const TYPES: ConditionType[] = ["budget", "climate", "activity", "travel_time", "other"];

export default function People() {
  const { bundle, recs, actorId, saveProfile, addCondition, setConditionStatus, addMember } = useApp();
  const { promptText } = useDialog();

  const actorProfile = bundle?.profiles.find((p) => p.member_id === actorId) ?? null;

  const [budget, setBudget] = useState("");
  const [travel, setTravel] = useState("");
  const [climates, setClimates] = useState<string[]>([]);
  const [activities, setActivities] = useState<string[]>([]);
  const [text, setText] = useState("");
  const [type, setType] = useState<ConditionType>("budget");
  const [status, setStatus] = useState<ConditionStatus>("fixed");

  // Sync only when the acting member changes, so a background reload can't
  // wipe what someone is typing.
  useEffect(() => {
    setBudget(actorProfile?.budget_max != null ? String(actorProfile.budget_max) : "");
    setTravel(
      actorProfile?.travel_time_max_hours != null ? String(actorProfile.travel_time_max_hours) : "",
    );
    setClimates(actorProfile?.climates ?? []);
    setActivities(actorProfile?.activities ?? []);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [actorProfile?.member_id]);

  const range = useMemo(() => {
    const costs = recs.map((r) => r.destination.est_cost);
    if (!costs.length) return { lo: 0, hi: 0 };
    return { lo: Math.min(...costs), hi: Math.max(...costs) };
  }, [recs]);

  // The choices come from the dataset itself, so they always match the words the
  // scoring engine actually compares against.
  const climateOptions = useMemo(() => {
    const found = new Set(recs.map((r) => r.destination.climate).filter(Boolean));
    (actorProfile?.climates ?? []).forEach((c) => found.add(c));
    return [...found].sort();
  }, [recs, actorProfile?.climates]);

  const activityOptions = useMemo(() => {
    const found = new Set(recs.flatMap((r) => r.destination.activities));
    (actorProfile?.activities ?? []).forEach((a) => found.add(a));
    return [...found].sort();
  }, [recs, actorProfile?.activities]);

  if (!bundle) return null;

  if (bundle.members.length === 0) {
    return (
      <div className="card">
        <Empty
          title="No travellers yet"
          note="Add someone to start collecting preferences."
          action={
            <button
              type="button"
              className="btn go"
              onClick={async () => {
                const name = await promptText({
                  title: "Add a traveller",
                  label: "Their name",
                  placeholder: "e.g. Ada",
                  help: "Everyone keeps their own budget, preferences and limits.",
                  confirmLabel: "Add traveller",
                });
                if (name) void addMember(name);
              }}
            >
              Add a traveller
            </button>
          }
        />
      </div>
    );
  }

  const myConditions = bundle.conditions.filter((c) => c.member_id === actorId);

  return (
    <>
      <div className="toolbar">
        <div>
          <h1 className="h1">People</h1>
          <div className="sub">Each traveller keeps their own model. Nothing is averaged here.</div>
        </div>
        <button
          type="button"
          className="btn"
          style={{ marginLeft: "auto" }}
          onClick={async () => {
            const name = await promptText({
              title: "Add a traveller",
              label: "Their name",
              placeholder: "e.g. Ada",
              help: "They get their own card, their own budget, and their own limits.",
              confirmLabel: "Add traveller",
            });
            if (name) void addMember(name);
          }}
        >
          Add traveller
        </button>
      </div>

      <div className="grid">
        {bundle.members.map((m) => {
          const profile = bundle.profiles.find((p) => p.member_id === m.id);
          const over = profile?.budget_max
            ? recs.filter((r) => r.destination.est_cost > (profile.budget_max as number)).length
            : 0;
          const within = recs.length ? Math.round(100 * (1 - over / recs.length)) : 100;
          const limits = bundle.conditions.filter((c) => c.member_id === m.id);
          return (
            <div className="card pcard" key={m.id}>
              <div className="pcard-top">
                <Avatar member={m} size="lg" />
                <div>
                  <div className="nm">{m.name}</div>
                  <div className="sub">
                    {profile?.budget_max != null ? `$${profile.budget_max} budget` : "no budget set"}
                  </div>
                </div>
              </div>

              <div className="meter-labels">
                <span>${Math.round(range.lo)}</span>
                <span>${Math.round(range.hi)}</span>
              </div>
              <div className={`meter${over ? " meter-over" : ""}`}>
                <i style={{ width: `${within}%` }} />
              </div>
              <div className={`hint ${over ? "hint-bad" : "hint-good"}`}>
                {over ? `${over} over budget` : "All within budget"}
              </div>

              <h3 className="sec">Wants</h3>
              <div className="chipset">
                {(profile?.climates ?? []).map((c) => (
                  <Chip key={`c-${c}`}>{c}</Chip>
                ))}
                {(profile?.activities ?? []).map((a) => (
                  <Chip key={`a-${a}`} tone="good">
                    {a}
                  </Chip>
                ))}
                {!profile?.climates?.length && !profile?.activities?.length && (
                  <span className="hint">Nothing set</span>
                )}
              </div>

              <h3 className="sec">Limits</h3>
              <div className="chipset">
                {limits.length === 0 && <span className="hint">No conditions</span>}
                {limits.map((c) => (
                  <span key={c.id} className={`tag${c.status === "fixed" ? " tag-fixed" : ""}`}>
                    {c.text}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {actorProfile && (
        <div className="card" style={{ marginTop: 14 }}>
          <div className="card-pad">
            <h3 className="sec">My preferences</h3>
            <div className="form-grid">
              <label>
                Budget max
                <input
                  type="number"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  onBlur={() => void saveProfile(actorProfile.member_id, { budget_max: Number(budget) || null })}
                />
              </label>
              <label>
                Travel max (h)
                <input
                  type="number"
                  value={travel}
                  onChange={(e) => setTravel(e.target.value)}
                  onBlur={() =>
                    void saveProfile(actorProfile.member_id, {
                      travel_time_max_hours: Number(travel) || null,
                    })
                  }
                />
              </label>
              <MultiSelect
                label="Climates"
                options={climateOptions}
                value={climates}
                placeholder="Choose one or more"
                onChange={(next) => {
                  setClimates(next);
                  void saveProfile(actorProfile.member_id, { climates: next });
                }}
              />
              <MultiSelect
                label="Activities"
                options={activityOptions}
                value={activities}
                placeholder="Choose one or more"
                onChange={(next) => {
                  setActivities(next);
                  void saveProfile(actorProfile.member_id, { activities: next });
                }}
              />
            </div>

            <h3 className="sec">My conditions</h3>
            <div className="chipset">
              {myConditions.length === 0 && <span className="hint">None yet</span>}
              {myConditions.map((c) => (
                <span key={c.id} className={`tag${c.status === "fixed" ? " tag-fixed" : ""}`}>
                  <span>{c.text}</span>
                  <button
                    type="button"
                    className="btn sm"
                    onClick={() =>
                      void setConditionStatus(c.id, c.status === "fixed" ? "flexible" : "fixed")
                    }
                  >
                    {c.status === "fixed" ? "Mark flexible" : "Mark fixed"}
                  </button>
                </span>
              ))}
            </div>

            <div className="hstack" style={{ marginTop: 10 }}>
              <input
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="e.g. No more than $900 pp"
                style={{ flex: 1, minWidth: 180 }}
              />
              <select value={type} onChange={(e) => setType(e.target.value as ConditionType)}>
                {TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <select value={status} onChange={(e) => setStatus(e.target.value as ConditionStatus)}>
                <option value="fixed">fixed</option>
                <option value="flexible">flexible</option>
              </select>
              <button
                type="button"
                className="btn go"
                disabled={!text.trim()}
                onClick={async () => {
                  await addCondition({ text: text.trim(), type, status });
                  setText("");
                }}
              >
                Add
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

import { useState } from "react";

import { useApp } from "../state/AppState";
import { Avatar, Chip, Empty } from "../components/ui";

const QUESTIONS = [
  { key: "felt_heard", label: "I felt heard" },
  { key: "control", label: "I had control" },
  { key: "fairness", label: "The decision was fair" },
];

const LABELS: Record<string, string> = {
  activity_changed: "Plan changed",
  condition_changed: "Condition changed",
  unresolved: "Unresolved",
};

export default function Record() {
  const { bundle, detectConflicts, resolveConflict, task, actorId, survey } = useApp();
  const [answers, setAnswers] = useState<Record<string, string>>({});

  if (!bundle) return null;

  const name = (id: number | null) => bundle.members.find((m) => m.id === id)?.name ?? "Someone";

  return (
    <>
      <div className="toolbar">
        <div>
          <h1 className="h1">Record</h1>
          <div className="sub">What the group did, and how each conflict was settled.</div>
        </div>
        <button
          type="button"
          className="btn"
          style={{ marginLeft: "auto" }}
          onClick={() => void detectConflicts()}
        >
          Detect conflicts
        </button>
      </div>

      <div className="card">
        <div className="card-pad">
          <h3 className="sec">Open conflicts</h3>
          {bundle.conflicts.length === 0 ? (
            <p className="hint">Nothing recorded yet. Run Detect conflicts to snapshot them.</p>
          ) : (
            bundle.conflicts.map((c) => (
              <div className="recordrow" key={c.id}>
                <span className="stack-dots">
                  {c.member_ids.map((id) => {
                    const m = bundle.members.find((x) => x.id === id);
                    return m ? <Avatar key={id} member={m} size="sm" /> : null;
                  })}
                </span>
                <span className="recordrow-main">{c.summary}</span>
                <Chip tone={c.status === "resolved" ? "good" : "bad"}>{c.status}</Chip>
                {c.status !== "resolved" && (
                  <button type="button" className="btn sm" onClick={() => void resolveConflict(c.id)}>
                    Resolve
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="card-pad">
          <h3 className="sec">Revisions</h3>
          {bundle.revisions.length === 0 ? (
            <Empty title="Nothing recorded yet" note="Votes, vetoes and resolutions land here." />
          ) : (
            <div className="tl">
              {bundle.revisions.map((r) => (
                <div className={`ev${r.change_type === "activity_changed" ? " ev-bad" : ""}`} key={r.id}>
                  <span className="ev-dot" />
                  <span className="ev-main">
                    <strong>{LABELS[r.change_type] ?? r.change_type}</strong>
                    {r.description ? ` — ${r.description}` : ""}
                  </span>
                  <span className="meta">
                    <span>{name(r.member_id)}</span>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid" style={{ marginTop: 14 }}>
        <div className="card pcard">
          <h3 className="sec">Vetoes</h3>
          {bundle.vetoes.length === 0 ? (
            <p className="hint">None.</p>
          ) : (
            bundle.vetoes.map((v) => (
              <div className="recordrow" key={v.id}>
                <Avatar member={bundle.members.find((m) => m.id === v.member_id)} size="sm" />
                <span className="recordrow-main">
                  {name(v.member_id)} vetoed destination #{v.destination_id}
                </span>
              </div>
            ))
          )}
        </div>

        <div className="card pcard">
          <h3 className="sec">Approval</h3>
          <p className="hint">
            {bundle.approvals.approved_member_ids.length} of {bundle.members.length} approved
            {bundle.approvals.fully_approved ? " — everyone in." : "."}
          </p>
          <div className="chipset">
            {bundle.members.map((m) => (
              <Chip
                key={m.id}
                tone={bundle.approvals.approved_member_ids.includes(m.id) ? "good" : "ghost"}
              >
                {m.name}
              </Chip>
            ))}
          </div>
        </div>

        <div className="card pcard">
          <h3 className="sec">Suggestions</h3>
          {bundle.requests.length === 0 ? (
            <p className="hint">None. Use Alt next to an activity to ask for something else.</p>
          ) : (
            bundle.requests.map((r) => (
              <div className="recordrow" key={r.id}>
                <Avatar member={bundle.members.find((m) => m.id === r.member_id)} size="sm" />
                <span className="recordrow-main">
                  <strong>{name(r.member_id)}</strong> wants an alternative: “{r.text}”
                </span>
                <Chip tone={r.status === "open" ? "mid" : "good"}>{r.status}</Chip>
              </div>
            ))
          )}
        </div>

        {task && (
          <div className="card pcard">
            <h3 className="sec">After this task</h3>
            {!bundle.members.find((m) => m.id === actorId)?.participant_id ? (
              <p className="hint">
                This member has no participant link, so answers can't be attributed. Set
                <code> participant_id </code> on the member first.
              </p>
            ) : (
              <>
                {QUESTIONS.map((q) => (
                  <div className="surveyq" key={q.key}>
                    <span>{q.label}</span>
                    <span className="chipset">
                      {[1, 2, 3, 4, 5].map((n) => {
                        const value = String(n);
                        const on = answers[q.key] === value;
                        return (
                          <button
                            key={n}
                            type="button"
                            className={`btn sm${on ? " go" : ""}`}
                            aria-pressed={on}
                            onClick={() => {
                              setAnswers((a) => ({ ...a, [q.key]: value }));
                              void survey(q.key, value);
                            }}
                          >
                            {n}
                          </button>
                        );
                      })}
                    </span>
                  </div>
                ))}
                <p className="hint">Saved against participant {actorId ?? "—"}.</p>
              </>
            )}
          </div>
        )}
      </div>
    </>
  );
}

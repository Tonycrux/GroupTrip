import { useEffect, useRef, useState } from "react";

import { useApp } from "../state/AppState";
import { useDialog } from "./DialogProvider";
import type { Condition, RatingValue, Recommendation } from "../types";
import { Avatar, AvatarStack, Chip, Ring, bandColor } from "./ui";

import { api } from "../api/client";
import type { ParsedCondition } from "../api/client";
import LlmExplanation from "./LlmExplanation";

const RATINGS: { value: RatingValue; label: string }[] = [
  { value: "interested", label: "Interested" },
  { value: "interested_if", label: "If…" },
  { value: "not_interested", label: "No" },
  { value: "skipped", label: "Skip" },
];

export default function DestinationDrawer({
  recommendation,
  onClose,
}: {
  recommendation: Recommendation | null;
  onClose: () => void;
}) {
  const {
    bundle,
    recs,
    actorId,
    actor,
    conflict,
    rateDestination,
    veto,
    unveto,
    approve,
    withdraw,
    setConditionStatus,
    previewCondition,
    logRevision,
    chooseDestination,
    refresh,
  } = useApp();
  const { promptText } = useDialog();

  const [preview, setPreview] = useState<{ condition: Condition; summary: string } | null>(null);

  const [proposal, setProposal] = useState<{ source: string; conditions: ParsedCondition[] } | null>(null);
  const [parsing, setParsing] = useState(false);
  const [proposalError, setProposalError] = useState<string | null>(null);

  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setProposal(null);
    setProposalError(null);
  }, [recommendation?.destination.id]);

  useEffect(() => {
    if (!recommendation) return;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [recommendation, onClose]);

  if (!recommendation || !bundle) return null;

  const dest = recommendation.destination;
  const members = bundle.members;
  const actorVeto = bundle.vetoes.find(
    (v) => v.member_id === actorId && v.destination_id === dest.id,
  );
  const vetoed = Boolean(actorVeto) || recommendation.vetoed_by.length > 0;
  const myRating = bundle.ratings.find(
    (r) => r.member_id === actorId && r.destination_id === dest.id,
  );
  const myConditions = bundle.conditions.filter((c) => c.member_id === actorId);
  const approvedCount = bundle.approvals.approved_member_ids.length;
  const alreadyChosen = bundle.trip.selected_destination_id === dest.id;

  const relax = async (condition: Condition) => {
    const p = await previewCondition(condition.id);
    setPreview({ condition, summary: p.summary });
  };

  const vote = async (value: RatingValue) => {
    if (value === "interested_if") {
      const reason = await promptText({
        title: "Interested if…",
        label: "What would have to be true?",
        placeholder: "e.g. only if it stays under $700",
        help: "This is saved as a condition in your name, so the group can see what it would take to win you over.",
        confirmLabel: "Save condition",
        allowEmpty: true,
      });

      let parsed: ParsedCondition[] = [];
      if (conflict && reason && reason.trim()) {
        setParsing(true);
        setProposalError(null);
        try {
          parsed = (await api.llmParseCondition(reason.trim())).conditions;
        } catch {
          parsed = [];
        } finally {
          setParsing(false);
        }
      }

      if (parsed.length > 0) {
        void rateDestination(dest.id, value); // record the choice; the member confirms the limits below
        setProposal({ source: reason!.trim(), conditions: parsed });
      } else {
        void rateDestination(dest.id, value, reason || undefined); // original behaviour
      }
      return;
    }
    void rateDestination(dest.id, value);
  };

  const confirmRelax = async (condition: Condition) => {
    await setConditionStatus(condition.id, "flexible");
    await logRevision({
      change_type: "condition_changed",
      description: `Relaxed "${condition.text}"`,
      affected_member_ids: [condition.member_id],
      affected_condition_ids: [condition.id],
    });
    setPreview(null);
  };

    const toggleStatus = (i: number) =>
    setProposal((p) =>
      p
        ? {
            ...p,
            conditions: p.conditions.map((c, j) =>
              j === i ? { ...c, status: c.status === "fixed" ? "flexible" : "fixed" } : c,
            ),
          }
        : p,
    );

  const acceptProposal = async () => {
    if (!proposal || actorId == null) return;
    setParsing(true);
    setProposalError(null);
    try {
      await api.llmAcceptConditions(bundle.trip.id, actorId, proposal.conditions);
      setProposal(null);
      await refresh();
    } catch (e) {
      setProposalError(e instanceof Error ? e.message : "Could not save those limits");
    } finally {
      setParsing(false);
    }
  };

  return (
    <>
      <div className="veil on" onClick={onClose} aria-hidden="true" />
      <aside className="drawer on" role="dialog" aria-modal="true" aria-label={`${dest.name} detail`}>
        <div className="dhead">
          {dest.image_url ? <img className="thumb" src={dest.image_url} alt="" /> : <span className="thumb" />}
          <div className="dhead-text">
            <div className="nm">{dest.name}</div>
            <div className="meta">
              <span>{dest.country}</span>
              <span>·</span>
              <span className="n">${Math.round(dest.est_cost)}</span>
              <span>·</span>
              <span className="n">{dest.travel_time_hours}h</span>
            </div>
          </div>
          <button ref={closeRef} className="btn sm" type="button" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <div className="dbody">
          {conflict && (
            <>
              <h3 className="sec">Fit per person</h3>
              {members.map((m) => {
                const ms = recommendation.member_scores.find((s) => s.member_id === m.id);
                if (!ms) return null;
                const violation = ms.hard_violations[0];
                const reason = violation ?? ms.reasons[0] ?? "well served";
                return (
                  <div className="fitrow" key={m.id} title={reason}>
                    <Avatar member={m} size="sm" />
                    <div>
                      <div className="fitrow-name">{m.name}</div>
                      <div className="t">
                        <i
                          style={{
                            width: `${Math.max(2, Math.min(100, ms.score))}%`,
                            background: bandColor(ms.score),
                          }}
                        />
                      </div>
                    </div>
                    <span className="fitrow-v n" style={{ color: bandColor(ms.score) }}>
                      {violation ? "!" : ""}
                      {Math.round(ms.score)}
                    </span>
                  </div>
                );
              })}

              <h3 className="sec">In the way</h3>
              {recommendation.conflicts.length === 0 ? (
                <p className="note">Nothing in the way.</p>
              ) : (
                recommendation.conflicts.map((c, i) => (
                  <div className="note note-bad" key={i}>
                    <div className="note-head">
                      <AvatarStack members={c.member_ids.map((id) => members.find((m) => m.id === id)!).filter(Boolean)} />
                      <Chip tone="bad">{c.kind.replace(/_/g, " ")}</Chip>
                    </div>
                    <span>{c.summary}</span>
                  </div>
                ))
              )}

              <h3 className="sec">Why it sits here</h3>
              <LlmExplanation
                tripId={bundle.trip.id}
                destinationId={dest.id}
                fallback={recommendation.explanation}
                refreshKey={recommendation.member_scores.map((s) => s.score).join(",")}
              />
            </>
          )}

          <h3 className="sec">My call</h3>
          <div className="chipset">
            {RATINGS.map((r) => (
              <button
                key={r.value}
                type="button"
                className={`btn sm${myRating?.value === r.value ? " go" : ""}`}
                aria-pressed={myRating?.value === r.value}
                onClick={() => vote(r.value)}
              >
                {r.label}
              </button>
            ))}
          </div>
          {myRating?.condition_id && (
            <p className="hint">Your condition was recorded from that choice.</p>
          )}

          <h3 className="sec">My limits</h3>
          {myConditions.length === 0 ? (
            <p className="hint">No conditions yet.</p>
          ) : (
            <div className="chipset">
              {myConditions.map((c) => (
                <span key={c.id} className={`tag${c.status === "fixed" ? " tag-fixed" : ""}`}>
                  <span>{c.text}</span>
                  {c.status === "fixed" && (
                    <button type="button" className="btn sm" onClick={() => relax(c)}>
                      Relax
                    </button>
                  )}
                </span>
              ))}
            </div>
          )}

          {(parsing || proposal || proposalError) && (
            <div className="note note-warn">
              {parsing && !proposal && <div>Reading your condition…</div>}
              {proposal && (
                <>
                  <div>
                    Is this what you meant? <span className="hint">“{proposal.source}”</span>
                  </div>
                  {proposal.conditions.map((c, i) => (
                    <div key={i} className="chipset" style={{ marginTop: 8 }}>
                      <span className={`chip ${c.status === "fixed" ? "bad" : "ghost"}`}>{c.status}</span>
                      <span>{c.text}</span>
                      <button type="button" className="btn sm" onClick={() => toggleStatus(i)}>
                        {c.status === "fixed" ? "Make flexible" : "Make fixed"}
                      </button>
                    </div>
                  ))}
                  <div className="chipset" style={{ marginTop: 8 }}>
                    <button type="button" className="btn sm go" disabled={parsing} onClick={acceptProposal}>
                      Confirm
                    </button>
                    <button type="button" className="btn sm" onClick={() => setProposal(null)}>
                      Discard
                    </button>
                  </div>
                </>
              )}
              {proposalError && <div>{proposalError}</div>}
            </div>
          )}

          {preview && (
            <div className="note note-warn">
              <div>{preview.summary}</div>
              <div className="chipset" style={{ marginTop: 8 }}>
                <button
                  type="button"
                  className="btn sm go"
                  onClick={() => confirmRelax(preview.condition)}
                >
                  Confirm change
                </button>
                <button type="button" className="btn sm" onClick={() => setPreview(null)}>
                  Cancel
                </button>
              </div>
            </div>
          )}

          <h3 className="sec">Approval</h3>
          <div className="appr-top">
            <Ring done={approvedCount} total={members.length} />
            <span className="hint">
              {approvedCount === members.length ? "Everyone in." : "A score isn't approval."}
            </span>
          </div>
          {members.map((m) => {
            const on = bundle.approvals.approved_member_ids.includes(m.id);
            return (
              <div className="appr" key={m.id}>
                <Avatar member={m} size="sm" />
                <span className="appr-name">{m.name}</span>
                <button
                  type="button"
                  className="sw"
                  aria-pressed={on}
                  aria-label={`${m.name} approves`}
                  onClick={() => (on ? withdraw(m.id) : approve(m.id))}
                />
              </div>
            );
          })}
        </div>

        <div className="dfoot">
          <button
            type="button"
            className="btn go"
            disabled={vetoed || alreadyChosen}
            onClick={() => {
              void chooseDestination(dest.id);
              onClose();
            }}
          >
            {alreadyChosen ? "Chosen" : "Choose this"}
          </button>
          {actorVeto ? (
            <button type="button" className="btn" onClick={() => unveto(dest.id)}>
              Withdraw veto
            </button>
          ) : (
            <button type="button" className="btn stop" disabled={vetoed} onClick={() => veto(dest.id)}>
              Veto
            </button>
          )}
          {recs.length === 0 && <span className="hint">Loading…</span>}
        </div>
        <span className="sr">Acting as {actor?.name ?? "nobody"}</span>
      </aside>
    </>
  );
}

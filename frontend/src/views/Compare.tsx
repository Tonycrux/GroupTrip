import { useNavigate } from "react-router-dom";

import { useApp } from "../state/AppState";
import { useDialog } from "../components/DialogProvider";
import type { Recommendation } from "../types";
import { Avatar, Banner, Chip, Empty, ScoreBar, Skeleton, Spread, bandColor } from "../components/ui";

const spreadOf = (r: Recommendation) => {
  const s = r.member_scores.map((m) => m.score);
  return Math.max(...s) - Math.min(...s);
};

export default function Compare({ onPick }: { onPick: (name: string) => void }) {
  const { bundle, recs, tripId, loading, error, conflict, clearError, reload, actorId, addMember } =
    useApp();
  const { promptText } = useDialog();
  const navigate = useNavigate();

  if (!bundle) {
    return (
      <div className="card">
        <div className="empty">
          <Skeleton w="60%" h={14} />
        </div>
      </div>
    );
  }

  if (bundle.members.length === 0) {
    return (
      <div className="card">
        <Empty
          title="No travellers yet"
          note="Add the people you're travelling with. Each keeps their own limits, and scores appear once there's a group."
          action={
            <button
              type="button"
              className="btn go"
              onClick={async () => {
                const name = await promptText({
                  title: "Add a traveller",
                  label: "Their name",
                  placeholder: "e.g. Ada",
                  help: "Everyone keeps their own budget, preferences and limits. Nothing gets averaged away.",
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

  const chosenId = bundle.trip.selected_destination_id;

  return (
    <>
      <div className="toolbar">
        <div>
          <h1 className="h1">Where should we go?</h1>
          <div className="sub">
            {bundle.trip.origin} · {bundle.trip.days} days · {bundle.members.length} travellers
          </div>
        </div>
        <div className="legend">
          <span>
            <i style={{ background: "var(--green)" }} />
            fits
          </span>
          <span>
            <i style={{ background: "var(--amber)" }} />
            compromise
          </span>
          <span>
            <i style={{ background: "var(--salmon)" }} />
            {conflict ? "conflict" : "weak fit"}
          </span>
        </div>
      </div>

      {error && (
        <Banner
          tone="bad"
          title="Couldn't refresh."
          note={error}
          action={
            <button
              type="button"
              className="btn sm"
              onClick={() => {
                clearError();
                void reload();
              }}
            >
              Try again
            </button>
          }
        />
      )}

      <div className="card">
        <div className="scroller">
          <table>
            <thead>
              <tr>
                <th>Where</th>
                {conflict &&
                  bundle.members.map((m) => (
                    <th key={m.id} className="m">
                      <Avatar member={m} size="sm" />
                    </th>
                  ))}
                <th>Group</th>
                {conflict && <th>Friction</th>}
                {conflict && <th>Disagreement</th>}
                <th>
                  <span className="sr">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {loading && recs.length === 0
                ? Array.from({ length: 6 }).map((_, i) => (
                    <tr key={`sk-${i}`} className="row">
                      <td>
                        <div className="dwrap">
                          <Skeleton w="38px" h={38} r={11} />
                          <div>
                            <Skeleton w="120px" />
                            <div style={{ marginTop: 6 }}>
                              <Skeleton w="80px" />
                            </div>
                          </div>
                        </div>
                      </td>
                      {conflict && bundle.members.map((m) => (
                        <td key={m.id}>
                          <Skeleton w="36px" />
                        </td>
                      ))}
                      <td>
                        <Skeleton w="28px" />
                      </td>
                      {conflict && <td><Skeleton w="110px" /></td>}
                      {conflict && <td><Skeleton w="96px" /></td>}
                      <td><Skeleton w="60px" /></td>
                    </tr>
                  ))
                : recs.map((r, i) => {
                    const vetoed = r.vetoed_by.length > 0;
                    const chosen = r.destination.id === chosenId;
                    const worst = [...r.conflicts].sort((a, b) => b.severity - a.severity)[0];
                    const wide = spreadOf(r) >= 35;
                    return (
                      <tr
                        key={r.destination.id}
                        className={`row${vetoed ? " out" : ""}${chosen ? " chosen" : ""}`}
                        tabIndex={0}
                        onClick={() => onPick(r.destination.name)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            onPick(r.destination.name);
                          }
                        }}
                      >
                        <td>
                          <div className="dwrap">
                            <span className="rank n">{i + 1}</span>
                            {r.destination.image_url ? (
                              <img className="thumb" src={r.destination.image_url} alt="" loading="lazy" />
                            ) : (
                              <span className="thumb" />
                            )}
                            <span>
                              <span className="nm">{r.destination.name}</span>
                              {chosen && (
                                <span className="chip chip-good" style={{ marginLeft: 8 }}>
                                  Chosen
                                </span>
                              )}
                              <span className="meta">
                                <span>{r.destination.climate}</span>
                                <span>·</span>
                                <span className="n">${Math.round(r.destination.est_cost)}</span>
                                <span>·</span>
                                <span className="n">{r.destination.travel_time_hours}h</span>
                              </span>
                            </span>
                          </div>
                        </td>
                        {conflict &&
                          bundle.members.map((m) => {
                            const ms = r.member_scores.find((s) => s.member_id === m.id);
                            return (
                              <td key={m.id}>
                                {ms ? <ScoreBar value={ms.score} /> : <span className="hint">–</span>}
                              </td>
                            );
                          })}
                        <td>
                          <span
                            className="g n"
                            style={{ color: vetoed ? "var(--ink-3)" : bandColor(r.group_score) }}
                          >
                            {vetoed ? "—" : Math.round(r.group_score)}
                          </span>
                        </td>
                        {conflict && (
                          <td>
                            {vetoed ? (
                              <Chip tone="bad">Vetoed</Chip>
                            ) : worst ? (
                              <span className="friction">
                                <span className="stack-dots">
                                  {worst.member_ids.map((id) => {
                                    const mem = bundle.members.find((m) => m.id === id);
                                    return mem ? <Avatar key={id} member={mem} size="sm" /> : null;
                                  })}
                                </span>
                                <Chip tone="bad">{worst.kind.replace(/_/g, " ")}</Chip>
                              </span>
                            ) : (
                              <Chip tone="good">Clear</Chip>
                            )}
                          </td>
                        )}
                        {conflict && (
                          <td>
                            <Spread
                              scores={r.member_scores.map((s) => s.score)}
                              wide={wide}
                              label={`${r.destination.name}: scores range ${Math.round(
                                Math.min(...r.member_scores.map((s) => s.score)),
                              )} to ${Math.round(Math.max(...r.member_scores.map((s) => s.score)))}`}
                            />
                          </td>
                        )}
                        <td>
                          <button
                            type="button"
                            className="btn sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              onPick(r.destination.name);
                            }}
                          >
                            Open
                          </button>
                        </td>
                      </tr>
                    );
                  })}
            </tbody>
          </table>
        </div>
      </div>

      {recs.length === 0 && !loading && (
        <div className="card" style={{ marginTop: 14 }}>
          <Empty
            title="No destinations"
            note="The catalogue is empty, so there is nothing to rank yet."
            action={
              <button
                type="button"
                className="btn"
                onClick={() => navigate(`/trips/${tripId}/people`)}
              >
                Check the group
              </button>
            }
          />
        </div>
      )}
      <span className="sr">Acting member {actorId ?? "none"}</span>
    </>
  );
}

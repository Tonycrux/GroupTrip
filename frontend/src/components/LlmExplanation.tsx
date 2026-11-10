import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { LlmExplanation as Result } from "../api/client";

export default function LlmExplanation({
  tripId,
  destinationId,
  fallback,
  refreshKey,
}: {
  tripId: number;
  destinationId: number;
  fallback: string;
  refreshKey: string;
}) {
  const [data, setData] = useState<Result | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .llmExplanation(tripId, destinationId)
      .then((r) => {
        if (!cancelled) setData(r);
      })
      .catch(() => {
        if (!cancelled) setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tripId, destinationId, refreshKey]);

  // Until the model answers (or if it fails), show the standard explanation.
  if (!data) {
    return (
      <>
        <p className="note">{fallback}</p>
        {loading && <p className="hint">Writing a clearer explanation…</p>}
      </>
    );
  }

  return (
    <div className="note">
      <div className="llm-row">
        <span className={`chip ${data.source === "llm" ? "good" : "mid"}`}>
          {data.source === "llm" ? "AI-written, checked" : "Standard summary"}
        </span>
      </div>
      <p className="llm-line">
        <b>{data.headline}</b>
      </p>
      {data.per_member.map((p) => (
        <p className="llm-line" key={p.member}>
          <b>{p.member}:</b> {p.line}
        </p>
      ))}
    </div>
  );
}
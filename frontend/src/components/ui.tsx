import type { ReactNode } from "react";

import type { Member } from "../types";

const TONES = ["a", "b", "c", "d", "e", "f"] as const;

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "?";
}

export function bandColor(score: number): string {
  if (score >= 70) return "var(--green-ink)";
  if (score >= 45) return "var(--amber-ink)";
  return "var(--salmon-ink)";
}

export function Avatar({
  member,
  size = "md",
}: {
  member: Pick<Member, "id" | "name"> | undefined;
  size?: "sm" | "md" | "lg";
}) {
  if (!member) return null;
  const tone = TONES[(member.id - 1) % TONES.length];
  return (
    <span className={`av av-${tone} av-${size}`} title={member.name}>
      {initials(member.name)}
    </span>
  );
}

export function AvatarStack({
  members,
  label,
  size = "sm",
}: {
  members: Pick<Member, "id" | "name">[];
  label?: string;
  size?: "sm" | "md";
}) {
  return (
    <span className="stack-dots" title={label ?? members.map((m) => m.name).join(", ")}>
      {members.map((m) => (
        <Avatar key={m.id} member={m} size={size} />
      ))}
    </span>
  );
}

export function Chip({
  tone = "ghost",
  children,
}: {
  tone?: "ghost" | "good" | "bad" | "mid";
  children: ReactNode;
}) {
  return <span className={`chip chip-${tone}`}>{children}</span>;
}

export function ScoreBar({ value, size = "md" }: { value: number; size?: "sm" | "md" }) {
  const v = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div className={`scorebar scorebar-${size}`} title={`${v} / 100`}>
      <span className="scorebar-v" style={{ color: bandColor(v) }}>
        {v}
      </span>
      <span className="scorebar-track">
        <span className="scorebar-fill" style={{ width: `${v}%`, background: bandColor(v) }} />
      </span>
    </div>
  );
}

export function Spread({
  scores,
  wide,
  label,
}: {
  scores: number[];
  wide: boolean;
  label?: string;
}) {
  const s = scores.map((n) => Math.max(2, Math.min(100, n)));
  const lo = Math.min(...s);
  const hi = Math.max(...s);
  return (
    <div
      className={`spread${wide ? " spread-wide" : ""}`}
      role="img"
      aria-label={label ?? `Scores range ${Math.round(lo)} to ${Math.round(hi)} out of 100`}
    >
      <span className="spread-track" />
      <span className="spread-range" style={{ left: `${lo}%`, width: `${Math.max(hi - lo, 3)}%` }} />
      {s.map((n, i) => (
        <span key={i} className="spread-tick" style={{ left: `calc(${n}% - 2px)` }} />
      ))}
    </div>
  );
}

export function Ring({ done, total }: { done: number; total: number }) {
  const r = 26;
  const c = 2 * Math.PI * r;
  const p = total > 0 ? done / total : 0;
  return (
    <div className="ring" role="img" aria-label={`${done} of ${total} approved`}>
      <svg width="64" height="64" viewBox="0 0 64 64" aria-hidden="true">
        <circle cx="32" cy="32" r={r} fill="none" stroke="var(--line)" strokeWidth="7" />
        <circle
          cx="32"
          cy="32"
          r={r}
          fill="none"
          stroke={p === 1 ? "var(--green)" : "var(--mint)"}
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - p)}
          transform="rotate(-90 32 32)"
        />
      </svg>
      <span className="ring-lab">
        {done}/{total}
      </span>
    </div>
  );
}

export function Skeleton({ w = "100%", h = 12, r = 99 }: { w?: string; h?: number; r?: number }) {
  return <span className="sk" style={{ width: w, height: h, borderRadius: r }} />;
}

export function Empty({
  title,
  note,
  action,
}: {
  title: string;
  note: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-mark" aria-hidden="true">
        ⌘
      </span>
      <p className="empty-title">{title}</p>
      <p className="empty-note">{note}</p>
      {action}
    </div>
  );
}

export function Banner({
  tone,
  title,
  note,
  action,
}: {
  tone: "bad" | "info";
  title: string;
  note: string;
  action?: ReactNode;
}) {
  return (
    <div className={`banner banner-${tone}`} role={tone === "bad" ? "alert" : undefined}>
      <div>
        <strong>{title}</strong> {note}
      </div>
      {action}
    </div>
  );
}

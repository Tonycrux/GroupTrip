import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Navigate,
  NavLink,
  Route,
  Routes,
  useNavigate,
  useParams,
} from "react-router-dom";

import DestinationDrawer from "./components/DestinationDrawer";
import { DialogProvider } from "./components/DialogProvider";
import { Avatar } from "./components/ui";
import { api } from "./api/client";
import { AppProvider, useApp } from "./state/AppState";
import type { RankingStrategy } from "./types";
import Compare from "./views/Compare";
import People from "./views/People";
import Plan from "./views/Plan";
import Record from "./views/Record";
import TripSetup from "./views/TripSetup";

const TABS = [
  { to: "compare", label: "Compare" },
  { to: "people", label: "People" },
  { to: "plan", label: "Plan" },
  { to: "record", label: "Record" },
];

const STRATEGIES: { value: RankingStrategy; label: string }[] = [
  { value: "average", label: "Highest average" },
  { value: "maximin", label: "Least-satisfied member" },
  { value: "balanced", label: "Balance both" },
  { value: "avoid_dislikes", label: "Avoid dislikes" },
  { value: "complementary", label: "Satisfy most" },
];

function Boot() {
  return (
    <div className="boot">
      <span className="mark big" aria-hidden="true">
        ⌘
      </span>
    </div>
  );
}

function NotFound({ note }: { note?: string }) {
  const navigate = useNavigate();
  return (
    <div className="boot">
      <div className="card" style={{ maxWidth: 440 }}>
        <div className="empty">
          <span className="empty-mark" aria-hidden="true">
            ⌘
          </span>
          <p className="empty-title">That page doesn't exist</p>
          <p className="empty-note">
            {note ?? "The address may be mistyped, or the trip may have been deleted."}
          </p>
          <button type="button" className="btn go" onClick={() => navigate("/")}>
            Back to your trips
          </button>
        </div>
      </div>
    </div>
  );
}

function TaskEntry() {
  const { taskId } = useParams();
  const [tripId, setTripId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const id = Number(taskId);
    if (!Number.isFinite(id) || id <= 0) {
      setError("That task link is not valid.");
      return;
    }
    api
      .taskTrip(id)
      .then((trip) => setTripId(trip.id))
      .catch((e) => setError(e instanceof Error ? e.message : "Could not open that task"));
  }, [taskId]);

  if (error) return <NotFound note={error} />;
  if (tripId === null) return <Boot />;
  return <Navigate to={`/trips/${tripId}/compare?task=${taskId}`} replace />;
}

function TripShell() {
  const {
    tripId,
    bundle,
    recs,
    ready,
    actorId,
    setActorId,
    variant,
    setVariant,
    strategy,
    setStrategy,
    task,
  } = useApp();
  const navigate = useNavigate();
  const [picked, setPicked] = useState<string | null>(null);

  if (!ready || !bundle) return <Boot />;

  const paused = task && task.status === "completed";
  const recommendation = picked ? recs.find((r) => r.destination.name === picked) ?? null : null;

  return (
    <>
      <header className="app">
        <div className="app-in">
          <span className="logo">
            <span className="mark" aria-hidden="true">
              ⌘
            </span>
            GroupTrip
          </span>

          <nav className="tabs" aria-label="Sections">
            {TABS.map((tab) => (
              <NavLink key={tab.to} to={tab.to}>
                {tab.label}
              </NavLink>
            ))}
          </nav>

          <div className="push ctl">
            <div className="seg" role="group" aria-label="Interface version">
              <button
                type="button"
                aria-pressed={variant === "plain"}
                disabled={Boolean(task)}
                title={task ? "Set by the study session" : undefined}
                onClick={() => setVariant("plain")}
              >
                Plain
              </button>
              <button
                type="button"
                aria-pressed={variant === "conflict"}
                disabled={Boolean(task)}
                title={task ? "Set by the study session" : undefined}
                onClick={() => setVariant("conflict")}
              >
                Conflict-aware
              </button>
            </div>

            <select
              aria-label="Ranking strategy"
              value={strategy}
              onChange={(e) => void setStrategy(e.target.value as RankingStrategy)}
            >
              {STRATEGIES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>

            <select
              aria-label="Acting as"
              value={actorId ?? ""}
              onChange={(e) => setActorId(Number(e.target.value))}
            >
              {bundle.members.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>

            <div className="who">
              {bundle.members.map((m) => (
                <Avatar key={m.id} member={m} size="sm" />
              ))}
            </div>

            <button type="button" className="btn sm" onClick={() => navigate("/")}>
              Switch
            </button>
          </div>
        </div>
      </header>

      <main>
        {paused && (
          <div className="banner banner-info" style={{ marginBottom: 14 }}>
            <div>
              <strong>This task is finished.</strong> Answers are still visible for review.
            </div>
          </div>
        )}

        <Routes>
          <Route index element={<Navigate to="compare" replace />} />
          <Route path="compare" element={<Compare onPick={setPicked} />} />
          <Route path="people" element={<People />} />
          <Route path="plan" element={<Plan />} />
          <Route path="record" element={<Record />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>

      <DestinationDrawer recommendation={recommendation} onClose={() => setPicked(null)} />

      <span className="sr">
        Viewing trip {tripId ?? "unknown"}
      </span>
    </>
  );
}

function TripLayout() {
  const { tripId } = useParams();
  const id = Number(tripId);
  if (!Number.isFinite(id) || id <= 0) return <NotFound />;
  return (
    <AppProvider tripId={id} key={id}>
      <TripShell />
    </AppProvider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <DialogProvider>
        <Routes>
          <Route path="/" element={<TripSetup />} />
          <Route path="/task/:taskId" element={<TaskEntry />} />
          <Route path="/trips/:tripId/*" element={<TripLayout />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </DialogProvider>
    </BrowserRouter>
  );
}

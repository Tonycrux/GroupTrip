import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";
import type { Trip } from "../types";
import { Banner, Skeleton } from "../components/ui";

export default function TripSetup() {
  const navigate = useNavigate();
  const [trips, setTrips] = useState<Trip[] | null>(null);
  const [name, setName] = useState("");
  const [origin, setOrigin] = useState("Toronto");
  const [days, setDays] = useState(3);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .listTrips()
      .then(setTrips)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load trips"));
  }, []);

  const create = async () => {
    setBusy(true);
    try {
      const trip = await api.createTrip({ name: name.trim(), origin: origin.trim(), days });
      navigate(`/trips/${trip.id}/compare`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create the trip");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="setup">
      <div className="setup-card card">
        <div className="card-pad">
          <span className="mark big" aria-hidden="true">
            ⌘
          </span>
          <h1 className="h1" style={{ marginTop: 12 }}>
            Start a trip
          </h1>
          <p className="sub" style={{ marginBottom: 18 }}>
            Everyone keeps their own limits. The group score is only ever a summary.
          </p>

          {error && <Banner tone="bad" title="Something failed." note={error} />}

          <label>
            Trip name
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Summer 2027" />
          </label>
          <div className="form-grid" style={{ marginTop: 12 }}>
            <label>
              From
              <input value={origin} onChange={(e) => setOrigin(e.target.value)} placeholder="Toronto" />
            </label>
            <label>
              Days
              <input
                type="number"
                min={1}
                value={days}
                onChange={(e) => setDays(Number(e.target.value) || 1)}
              />
            </label>
          </div>

          <button
            type="button"
            className="btn go"
            style={{ marginTop: 16, width: "100%" }}
            disabled={!name.trim() || busy}
            onClick={() => void create()}
          >
            {busy ? "Creating…" : "Create trip"}
          </button>
        </div>
      </div>

      <div className="setup-card card">
        <div className="card-pad">
          <h3 className="sec">Existing trips</h3>
          {trips === null ? (
            <div className="stack-8">
              <Skeleton w="60%" />
              <Skeleton w="45%" />
            </div>
          ) : trips.length === 0 ? (
            <p className="hint">None yet.</p>
          ) : (
            trips.map((t) => (
              <button
                key={t.id}
                type="button"
                className="triprow"
                onClick={() => navigate(`/trips/${t.id}/compare`)}
              >
                <span className="nm">{t.name}</span>
                <span className="meta">
                  <span>{t.origin}</span>
                  <span>·</span>
                  <span className="n">{t.days} days</span>
                </span>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

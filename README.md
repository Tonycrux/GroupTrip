# GroupTrip

Explainable destination recommendations for groups with conflicting preferences.

A shared trip-planning prototype where every member keeps a **separate** preference model and
their own **conditions**. The system surfaces where members disagree, explains the trade-offs
behind each recommendation, and records whether conflicts get resolved by changing the plan or
by a member revising a condition.

The schema is frozen and documented in [`docs/erd.md`](docs/erd.md) — every table and field
traces back to a requirement in the project proposal.

## Stack

- **Frontend:** React + Vite + TypeScript
- **Backend:** FastAPI + SQLModel (SQLite)
- **Explanations:** deterministic templates first, LLM behind a swappable interface

## Layout

```
backend/
  app/
    main.py            FastAPI app + startup (create tables, seed)
    models.py          SQLModel tables (core planning + study layer)
    schemas.py         Pydantic request/response models
    enums.py           condition types, strategies, rating values, variants
    deps.py            minimal actor identity (X-Member-Id)
    seed.py            loads data/*.json into SQLite on first run
    routers/           trips, members, profile, conditions, destinations, activities,
                       ratings, recommendations, plan, revisions, vetoes, approvals,
                       conflicts, requests, study
    engine/
      scoring.py       per-member suitability from profile fields + card ratings
      aggregation.py   group strategies (average, maximin, balanced, …)
      conflicts.py     conflict detection between members
      scheduler.py     rule-based day scheduling
    explain/
      templates.py     deterministic explanation (fallback)
      llm.py           LLM explainer with automatic fallback
  data/                50 destinations + 600 activities, as .json and .csv, + provenance
  scripts/             build_dataset.py (regenerates data/ from live sources)
  tests/               engine tests + router-level invariant tests
  pyproject.toml       dependencies, pdm run scripts, pytest config
  pdm.lock             pinned dependency lockfile
frontend/
  src/
    views/             Compare, People, Plan, Record, TripSetup
    components/        DestinationDrawer + UI primitives (avatars, score bars, spread, ring)
    api/client.ts      typed client for every endpoint (sends X-Member-Id as the acting member)
    state/AppState.tsx trip bundle, variant, ranking, acting member, all mutations
    types.ts           shared API types
docs/
  erd.md               frozen data model, traced to the proposal
  data-sources.md      where the dataset comes from, and how it is derived
  e2e-checklist.md     plain-language list of what to click through, and what to expect
  prototype.html       the design prototype (single self-contained page)
```

## The dataset

`backend/data/` holds **50 real destinations** and **600 activities**, generated from live
sources rather than hand-written:

- **Cost** — Budget Your Trip's per-person daily travel spend (data current as of late Oct /
  early Nov 2026), × 3 days, in USD.
- **Climate** — classified from 10 years of Open-Meteo archive temperature and precipitation.
- **Travel time** — great-circle distance from Toronto (the nominal origin) over a flight model.
- **Activities** — real Wikivoyage listings (See/Do/Eat/Drink/Buy) with real names, and real
  opening hours and prices where the source states them.
- **Images** — each destination's lead photo from Wikipedia / Wikimedia Commons, with flags,
  maps and logos filtered out.

Full derivation, per-destination source URLs and caveats are in
[`docs/data-sources.md`](docs/data-sources.md); `backend/data/provenance.json` records the raw
figures and fetch dates. Each table ships as **JSON and CSV** (`destinations`, `activities`,
`provenance`) — the CSV copies are for opening in a spreadsheet. Rebuild with:

```bash
cd backend
pdm run python scripts/build_dataset.py          # or --from-json to just re-export CSV
```

## Getting started (Linux, macOS or Windows)

It runs the same way on all three. Only two things differ: how you install the tools, and how
you copy one file.

### What you need

| Tool | Version | What it is for |
| --- | --- | --- |
| Python | **3.11 or newer** | runs the backend |
| [pdm](https://pdm-project.org) | latest | installs the backend's Python packages |
| Node.js | **18 or newer** (20 LTS is best) | builds and serves the frontend |
| Git | any recent version | to clone the repository |

Check what you already have. Each command prints a version number:

```bash
python3 --version     # macOS and Linux
python --version      # Windows
node --version
```

### Install pdm

The official installer is the quickest route. Run the line for your system, then **close and
reopen the terminal** so the new command is found.

**Linux**

```bash
curl -sSL https://pdm-project.org/install.sh | bash
```

**macOS**

```bash
curl -sSL https://pdm-project.org/install.sh | bash
# or, if you use Homebrew:
brew install pdm
```

**Windows** (PowerShell)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://pdm-project.org/install.ps1 | iex"
```

Anything that works everywhere: `pipx install pdm` or `uv tool install pdm`.

### Install Node.js

The LTS installer from [nodejs.org](https://nodejs.org) works on all three systems and adds
`npm` for you. Or use a package manager:

| System | Command |
| --- | --- |
| macOS | `brew install node` |
| Windows | `winget install OpenJS.NodeJS.LTS` |
| Linux | your distribution's package, or [nvm](https://github.com/nvm-sh/nvm) |

Close and reopen the terminal afterwards, then check `node --version` shows 18 or higher.

## Run the backend

The backend is a [pdm](https://pdm-project.org) project. `pyproject.toml` holds the
dependencies and the run scripts, and `pdm.lock` pins exact versions.

```bash
cd backend
pdm install          # creates .venv and installs everything from the lockfile
pdm run dev          # starts the API on port 8000
```

You do **not** need to activate the virtual environment. `pdm run` handles it, which also means
there is no Windows-vs-rest difference to remember (no `.venv\Scripts\activate` one way and
`source .venv/bin/activate` the other).

Copying the config file is optional, because the defaults work. Do it only if you want to move
the database or add an LLM key:

```bash
cp .env.example .env            # macOS and Linux
```

```powershell
copy .env.example .env          # Windows, in cmd or PowerShell
```

- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health
- The database is created and seeded from `data/` on first start.
- `pdm run start` runs the same server without auto-reload.

Run the tests:

```bash
cd backend
pdm run test
```

> **Schema changes:** tables are created with `create_all`, which does **not** migrate an
> existing database. After changing `models.py`, delete `backend/grouptrip.db` so it is rebuilt.

Add a dependency with `pdm add <package>` or `pdm add -dG dev <package>`; pdm updates the lock
file and installs it.

## Run the frontend

Leave the backend running, and open a **second terminal**:

```bash
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173**. Vite forwards `/api` calls to the backend on port 8000, so
both have to be running for the app to work.

### Routes

Every screen has its own address, so a refresh, a bookmark, or a link sent to a participant
lands on the same place.

| Address | Shows |
| --- | --- |
| `/` | your trips, and the form to start a new one |
| `/trips/:id/compare` | the ranked board |
| `/trips/:id/people` | one card per traveller |
| `/trips/:id/plan` | the day-by-day timetable |
| `/trips/:id/record` | conflicts, revisions and suggestions |
| `/task/:id` | opens the trip attached to a study task, with its variant locked |

`/task/:id` is the link you hand to a participant: it looks up which trip belongs to the task
and forwards to the right screen with `?task=<id>` on the end.

## Troubleshooting

| What you see | What to do |
| --- | --- |
| `pdm: command not found`, or "not recognized as a command" | Close and reopen the terminal. The installer added it to your PATH, but terminals opened before that don't know yet |
| `node: command not found` | Same fix: reopen the terminal after installing Node |
| Vite complains that Node is too old | Vite 5 needs Node 18 or newer. Install the LTS from nodejs.org |
| `pdm install` says the Python version is too low | The project needs 3.11+. Install a newer Python, or let pdm fetch one: `pdm python install 3.11` |
| `Address already in use` on port 8000 | Another server is running. Stop it, or use a different port: `pdm run uvicorn app.main:app --port 8001` |
| `Address already in use` on port 5173 | Another Vite is running. Stop it, or use `npm run dev -- --port 5174` |
| The page loads but every action fails | The backend isn't running, or isn't on port 8000. Start it first |
| Destinations or activities look wrong | Delete `backend/grouptrip.db` and restart the backend so it reseeds from `data/` |
| `python` opens the Microsoft Store on Windows | Install Python from python.org and tick "Add python.exe to PATH", or use `py` instead of `python` |
| A refresh on a sub-page 404s | Only happens on a plain static host. See the note under Routes |

## Design rules the code follows

- The **LLM never ranks**. Ranking is deterministic and computed in `engine/`.
- Explanations are generated from already-computed scores and conflicts; if the LLM is
  unavailable or `LLM_PROVIDER=template`, the template explainer is used.
- Each member has their own **profile fields**, each carrying a `source` (explicit/inferred)
  and confidence, so the system's reading of a member can be corrected field by field.
- Group score is only produced by an explicit aggregation strategy, so disagreements stay
  visible instead of averaging away.
- **A high score is not approval.** `Approval` is per-member and explicit; the plan is only
  fully approved when every current member has approved.
- **Card ratings feed the score.** `interested` / `not_interested` adjust the member's score;
  `interested_if` additionally spawns an owned condition. `skipped` changes nothing.
- **Vetoes are first-class** — a vetoed destination is blocked (group score 0) and flagged.
- **Fixed** conditions are never changed automatically; only the owner can change a condition's
  status or confirm it (enforced against the acting member via the `X-Member-Id` header).
- Conflicts are **persisted**, so a revision can record which conflict it resolved.
- The UI ships **two conditions**: *Plain* withholds per-member scores, conflicts, the trade-off
  explanation and the change preview; *Conflict-aware* shows them. Same engine and data in both,
  which is what makes the comparison in RQ1 meaningful.
- **Activities are scored per member too** (preferred type, likes, dislikes, and the member's own
  In/Out vote). An activity anyone marks *not interested* is dropped from the next generated plan,
  and the row says so.

## Configuration (`backend/.env`)

| Variable          | Purpose                                              |
| ----------------- | ---------------------------------------------------- |
| `DATABASE_URL`    | SQLite path (default `backend/grouptrip.db`)         |
| `CORS_ORIGINS`    | Allowed frontend origins                             |
| `LLM_PROVIDER`    | `template` (default), `openai`, or `anthropic`       |
| `LLM_MODEL`       | Model name for the chosen provider                   |
| `OPENAI_API_KEY`  | Required when `LLM_PROVIDER=openai`                  |
| `ANTHROPIC_API_KEY` | Required when `LLM_PROVIDER=anthropic`             |

## Main endpoints

Endpoints marked ✱ require the `X-Member-Id` header (the acting member).

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/trips/{id}/bootstrap` | everything one trip screen needs, in one round trip |
| POST | `/trips` | create a trip |
| POST | `/trips/{id}/members` | add a member |
| GET/PUT | `/members/{id}/profile` | read / set a member's profile fields |
| PATCH | `/members/{id}/profile/{field}` | set one field with a source (inferred or corrected) |
| POST | `/trips/{id}/conditions` | add an owned condition (fixed/flexible) |
| PATCH ✱ | `/conditions/{id}` | edit a condition (status change is owner-only) |
| POST ✱ | `/conditions/{id}/confirm` | owner confirms their condition |
| POST | `/members/{id}/ratings` | interested / interested-if / not-interested / skip |
| GET | `/trips/{id}/activities` | every activity at the chosen destination, scored per member |
| GET | `/trips/{id}/recommendations?strategy=` | ranked destinations + per-member scores + conflicts + explanation |
| POST | `/trips/{id}/vetoes` | veto a destination |
| POST | `/trips/{id}/conflicts/detect` | recompute and persist conflicts |
| GET | `/trips/{id}/approvals` | per-member approval status |
| POST | `/trips/{id}/plan/generate` | rule-based day schedule for the selected destination |
| POST | `/trips/{id}/changes/preview` | which members/conditions a change affects |
| POST | `/trips/{id}/requests` | request an alternative activity |
| GET/POST | `/trips/{id}/revisions` | revision log (activity vs condition, linked to a conflict) |

### Study layer

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/participants`, `/sessions`, `/scenarios`, `/tasks` | set up a study run |
| GET | `/tasks/{id}` | read one task (used to drive the UI variant) |
| GET | `/tasks/{id}/trip` | the trip attached to a task (used by the `/task/:id` route) |
| POST | `/events` | append an interaction event |
| POST | `/surveys` | record a participant's answer |

A `TaskInstance` ties a session, a scenario and an interface **variant** together; the `Trip`
for a run links back to it via `Trip.task_instance_id`. Opening the app with `?task=<id>` puts it
in study mode: the UI locks to that task's variant and posts an event for each meaningful action.

# BRAHMO Governance Engine

A governance engine for hospital knowledge graphs: **cascade invalidation**,
a 4-dimension **knowledge health score**, and **pulse notifications** — so AI
assistants never serve doctors outdated clinical guidance.

When a protocol is superseded, the engine ripples a review flag through every
piece of knowledge derived from it (bounded, audited, compliance-aware),
recomputes the graph's health, and notifies exactly the right people.

**Stack:** FastAPI (Python) · Supabase (PostgreSQL) · React (Vite) · Tailwind
**Zero LLM** — fully deterministic SQL + graph traversal.

---

## Features

- **Cascade invalidation** — BFS over `DERIVED_FROM` edges with three guards:
  depth bound, visited set, and a logged LEGAL_HOLD skip.
- **Status state machine** — enforced transitions; `SUPERSEDED` is terminal,
  `LEGAL_HOLD` is ADMIN-only.
- **Health score** — Coverage, Freshness, Balance, Consistency + weighted
  overall, with **deferred recomputation** (no misleading drop before review).
- **Pulse notifications** — routed to affected-department HOD/EDITOR only,
  aggregated one-per-doctor, severity-tagged.
- **Review flow** — confirm / supersede / expire, fully audited.
- **Dashboard** — live cascade tree, health bars, alerts, and audit timeline.

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- A free Supabase project (PostgreSQL)

---

## Setup

### 1. Database (Supabase)

1. Create a free project at supabase.com.
2. In the SQL Editor, run `supabase/schema.sql` (creates tables + indexes).
3. Then run `supabase/seed.sql` (loads 18 nodes, edges, users).
4. Verify: `SELECT COUNT(*) FROM knowledge_nodes;` → 18.

### 2. Backend (FastAPI)

```bash
# from the project root
py -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS/Linux

pip install fastapi uvicorn python-dotenv "psycopg[binary]"
```

Create a `.env` in the project root (see `.env.example`):

```
DB_HOST=aws-1-<region>.pooler.supabase.com
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres.<your-project-ref>
DB_PASSWORD=<your-db-password>
```

> Connection values come from Supabase → **Connect** → **Session pooler**.
> Use the host shown there exactly (region/aws number varies per project).

Run the API:

```bash
uvicorn backend.main:app --reload
```

API runs at `http://localhost:8000` — interactive docs at `/docs`.

### 3. Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

App runs at `http://localhost:5173`.

> Both servers run at once: FastAPI on 8000, Vite on 5173.

---

## Demo Flow

1. Open `http://localhost:5173` — the dashboard loads (health ~76%, all nodes ACTIVE).
2. Click **Supersede Sepsis v2 → Cascade**:
   - 9 nodes flip to `REVIEW_REQUIRED`; `N-HELD` is skipped (LEGAL_HOLD).
   - Health drops with a `PENDING REVIEW` badge.
   - 2 pulse alerts route to Medicine doctors (Dr. Meera, Dr. Ananya).
   - Audit trail records `CASCADE_TRIGGER`, `STATUS_CHANGE` ×9, `CASCADE_SKIP` ×1.
3. Click **Still valid** on a flagged node → it returns to ACTIVE; score recomputes.
4. Click **Reset Demo** → back to the clean starting state.

**Surprise test:** trigger a cascade from an Orthopaedics node (`N-O01`)
instead — works with zero code changes (routing/scoring are data-driven).

---

## Project Structure

```
brahmo-governance/
├── backend/
│   ├── db.py
│   ├── main.py
│   ├── reset_demo.py
│   └── governance/
│       ├── status_machine.py
│       ├── cascade_engine.py
│       ├── health_score.py
│       ├── health_state.py
│       ├── pulse_router.py
│       └── review_handler.py
├── frontend/
│   └── src/
│       ├── api.js
│       ├── App.jsx
│       └── components/
│           ├── HealthDashboard.jsx
│           ├── CascadeTree.jsx
│           ├── PulseAlerts.jsx
│           └── AuditTimeline.jsx
├── supabase/
│   ├── schema.sql
│   └── seed.sql
├── docs/
│   └── architecture.md
├── data_sources.md
└── README.md
```
## Innovation
- Deferred health score — shows a pending badge instead of a misleading drop immediately after cascade. Score recomputes on first review or after 24h.
- Notification aggregation — one alert per doctor per cascade (not one per node), grouped by cascade_id. Prevents notification fatigue.

See `docs/architecture.md` for design decisions (cascade bounding, deferred
health recomputation, notification routing, department-agnostic design).

---

## Demo Video

Loom walkthrough: https://www.loom.com/share/453a1d14e54e468087084e90be4e3ac7

# Architecture — BRAHMO Governance Engine

This document explains the design decisions behind the cascade invalidation
engine, the health score, the pulse notification system, and how the pieces
fit together. It focuses on the *why*, not just the *what*.

---

## 1. System Overview

The Governance Engine keeps a hospital's knowledge graph trustworthy. When a
protocol is superseded, everything derived from it may now be stale. Three
cooperating engines handle this:

```
Supersede a node
      │
      ▼
[1] Cascade Engine ── walks DERIVED_FROM edges (BFS), flags descendants
      │
      ├──► [2] Health Score ── recomputes graph quality (deferred)
      │
      └──► [3] Pulse Router ── notifies the right doctors
                  │
                  ▼
            Doctor reviews ── confirm / supersede / expire (closes the loop)
```

**Stack:** FastAPI (Python) + Supabase (PostgreSQL) + React (Vite) + Tailwind.
**Zero LLM** — every decision is deterministic SQL or graph traversal.

### Component map

| Layer | File | Responsibility |
|-------|------|----------------|
| Backend | `backend/db.py` | Database connection |
| Backend | `backend/governance/status_machine.py` | Valid status transitions (single source of truth) |
| Backend | `backend/governance/cascade_engine.py` | BFS cascade + guards + audit |
| Backend | `backend/governance/health_score.py` | 4-dimension SQL scoring |
| Backend | `backend/governance/health_state.py` | Deferred recomputation logic |
| Backend | `backend/governance/pulse_router.py` | Notification routing + aggregation |
| Backend | `backend/governance/review_handler.py` | Confirm / supersede / expire |
| Backend | `backend/main.py` | FastAPI HTTP endpoints |
| Frontend | `frontend/src/components/*` | Dashboard, tree, alerts, audit timeline |

---

## 2. Cascade Invalidation

### Why BFS (not DFS or recursive SQL)

The cascade must do three things per node: apply a conditional status change,
write an audit row, and log skips. Those per-node side-effects live most
cleanly in an imperative breadth-first loop. BFS also tracks depth naturally
(each level = one hop), which makes the depth bound trivial to enforce.

A recursive SQL CTE could *find* descendants faster, but expressing
conditional side-effects and audit logging inside a CTE is unreadable and
hard to test. At this graph size (and even at hundreds of nodes), BFS's
clarity outweighs SQL's speed advantage.

### The three guards (the safety core)

1. **Depth bound (`max_depth`, default 3)** — stops the ripple from
   propagating indefinitely. At depth 1 a node is directly built on the
   protocol; by depth 4+ the connection is so indirect that auto-flagging
   produces false positives. The bound is stored in `organizations.config`
   so each org can tune it without code changes.

2. **Visited set** — prevents re-processing a node reached by more than one
   path (multi-parent nodes) and eliminates any risk of infinite loops in a
   cyclic graph.

3. **LEGAL_HOLD skip (logged)** — a node frozen for compliance must never
   have its status changed by the cascade. It is skipped *and* a
   `CASCADE_SKIP` audit entry is written. A silent skip would be a
   compliance audit gap.

Additionally, already-`SUPERSEDED` and already-`REVIEW_REQUIRED` nodes are
skipped (idempotent — re-running a cascade does nothing harmful).

### Cascade follows DERIVED_FROM only

Only `DERIVED_FROM` edges propagate staleness. A `SUPPORTS` edge means "this
evidence backs that claim" — updating the supported claim doesn't invalidate
the supporting evidence. `SUPERSEDES` is handled by the supersede action
itself, not the cascade.

### Atomicity

`run_cascade()` performs all status updates and audit inserts inside a single
database transaction. Either the entire cascade lands, or none of it does —
the graph never ends up half-flagged.

---

## 3. Status Transition State Machine

All status changes route through `status_machine.assert_transition()`, the
single source of truth. Key rules:

- `SUPERSEDED` is **terminal** — no transition out of it (medical history must
  be preserved for medico-legal review).
- `LEGAL_HOLD` is **ADMIN-only** to set or release.
- Cascade-triggered `ACTIVE → REVIEW_REQUIRED` is valid; illegal transitions
  raise an error and are rejected.

Centralising the rules prevents drift — every module (cascade, review, legal
hold) asks the same authority whether a change is allowed.

---

## 4. Knowledge Health Score

Four dimensions, each computed by SQL aggregation from live data:

| Dimension | Measures | Formula (simplified) |
|-----------|----------|----------------------|
| Coverage | Are hierarchy levels populated? | levels with an ACTIVE node / total levels |
| Freshness | Are active nodes within validity? | fresh ACTIVE nodes / (ACTIVE + REVIEW_REQUIRED) |
| Balance | Is the type mix healthy? | 1 − (stddev of type counts / mean) |
| Consistency | Are nodes free of pending review? | ACTIVE / (ACTIVE + REVIEW_REQUIRED) |

Overall is a weighted sum (weights from `organizations.config`).

A cascade drops **Freshness** and **Consistency** (more nodes pending review)
while leaving **Coverage** and **Balance** roughly unchanged — which is
correct: a cascade is a review trigger, not a data-quality loss.

### Deferred recomputation (key decision)

Immediately after a cascade, showing the dropped score (e.g. 76% → 39%) is
misleading — the knowledge isn't bad, it's queued for review. So
recomputation is **deferred**: the dashboard shows a `PENDING REVIEW` badge
until either (a) the first review is confirmed, or (b) 24 hours pass —
whichever comes first. This stops leadership reacting to a number that
self-corrects. State is tracked via the audit log (the most recent
`CASCADE_TRIGGER` not yet followed by a `REVIEW_CONFIRMED`), so no extra
table is needed.

---

## 5. Pulse Notifications

After a cascade, alerts route to the right people:

- **Role filter:** only `HOD` and `EDITOR` (not `VIEWER`, not `ADMIN`).
- **Department filter:** only departments that own affected nodes —
  read from the graph, never hardcoded.
- **Aggregation:** one alert per doctor per cascade, summarising the count
  ("9 of your nodes need review"), not one alert per node. All alerts share a
  `cascade_id` so they can be grouped or cleared together. This prevents
  notification fatigue when a large cascade touches dozens of nodes.

Severity: `URGENT` for cascades, `WARNING` for health drops, `INFO` for
completed reviews.

---

## 6. Review Flow

A flagged node offers three actions, each validated by the state machine and
audited:

- **Confirm** → `REVIEW_REQUIRED → ACTIVE` ("still valid")
- **Expire** → `REVIEW_REQUIRED → EXPIRED` ("no longer relevant")
- **Supersede** → old node `SUPERSEDED`, a new ACTIVE replacement created and
  linked via a `SUPERSEDES` edge ("needs update")

The first confirmed review also ends the health-score deferral window, so the
score recomputes and begins recovering.

---

## 7. Department-Agnostic Design (Surprise Test)

The cascade, routing, and scoring are entirely data-driven — they read node
IDs, departments, and edges from the database. Nothing is hardcoded to the
Medicine/Sepsis scenario. Triggering a cascade from an Orthopaedics node
(e.g. `N-O01` DVT Prophylaxis) works with zero code changes: the BFS walks
that subtree, the visited set still protects multi-parent nodes, alerts route
to Ortho's HOD instead of Medicine's, and the health score reflects the new
state.

---

## 8. Performance

The cascade is bounded BFS — it visits exactly the DERIVED_FROM subgraph up to
`max_depth`. For N affected nodes that's N status updates and N audit inserts,
batched in one transaction. A cascade touching 85 nodes completes in under a
couple of seconds. Health recomputation is deferred and runs once, not
per-node. Indexes on `edges(target_id)`, `edges(edge_type)`, and
`knowledge_nodes(status)` keep the per-node lookups fast.

---

## 9. Security Note

Row Level Security is disabled for the demo to keep the local setup simple.
In production, RLS policies scoped by `org_id` and `department` would ensure a
Medicine HOD cannot read Ortho's nodes, and the publishable key alone could
not expose data. Database credentials are kept in a gitignored `.env` file;
the repository ships a `.env.example` documenting the required variables.
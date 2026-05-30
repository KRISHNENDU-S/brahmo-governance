"""
main.py  (STEP 6 - FastAPI server: the backend/frontend bridge)
===============================================================
Exposes the governance engine as HTTP endpoints the React frontend calls.
Each endpoint is a thin wrapper around the governance functions we built.

Run:  uvicorn backend.main:app --reload
Docs: http://localhost:8000/docs   (auto-generated interactive API docs)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import get_connection
from governance.cascade_engine import run_cascade
from governance.health_state import get_health_state
from governance.pulse_router import route_cascade_alerts
from governance.review_handler import confirm, expire, supersede
from governance.status_machine import InvalidTransitionError

app = FastAPI(title="BRAHMO Governance Engine")

# allow the React dev server (localhost:3000) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # demo only; lock down in production
    allow_methods=["*"],
    allow_headers=["*"],
)

ORG = "supra"


# ---------- request body shapes ----------
class CascadeRequest(BaseModel):
    node_id: str
    actor_id: str = "U-MEERA"
    max_depth: int = 3


class ReviewRequest(BaseModel):
    node_id: str
    action: str                      # "confirm" | "expire" | "supersede"
    actor_id: str = "U-MEERA"
    actor_role: str = "HOD"
    new_title: str | None = None     # for supersede
    new_content: str | None = None   # for supersede


# ---------- read endpoints ----------
@app.get("/nodes")
def list_nodes():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, type, title, status, department,
                   hierarchy_level_id, superseded_by
            FROM knowledge_nodes WHERE org_id = %s ORDER BY id
            """,
            (ORG,),
        )
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@app.get("/edges")
def list_edges():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT source_id, target_id, edge_type FROM edges")
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@app.get("/health")
def health():
    return get_health_state(ORG)


@app.get("/alerts")
def list_alerts():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.id, a.user_id, u.name AS user_name, a.alert_type,
                   a.severity, a.title, a.body, a.link, a.is_read, a.created_at
            FROM pulse_alerts a JOIN users u ON u.id = a.user_id
            WHERE a.org_id = %s
            ORDER BY CASE a.severity WHEN 'URGENT' THEN 0
                        WHEN 'WARNING' THEN 1 ELSE 2 END, a.created_at DESC
            """,
            (ORG,),
        )
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@app.get("/audit")
def list_audit(limit: int = 30):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT node_id, action, old_value, new_value, actor_id,
                   reason, timestamp
            FROM audit_log WHERE org_id = %s
            ORDER BY timestamp DESC LIMIT %s
            """,
            (ORG, limit),
        )
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@app.get("/users")
def list_users():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, role, department FROM users WHERE org_id = %s",
            (ORG,),
        )
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


# ---------- action endpoints ----------
@app.post("/cascade")
def trigger_cascade(req: CascadeRequest):
    result = run_cascade(req.node_id, actor_id=req.actor_id,
                         org_id=ORG, max_depth=req.max_depth)
    # route notifications for this cascade
    alerts = route_cascade_alerts(result, org_id=ORG, source_title=req.node_id)
    return {"cascade": result, "alerts_created": len(alerts)}


@app.post("/review")
def do_review(req: ReviewRequest):
    try:
        if req.action == "confirm":
            return confirm(req.node_id, req.actor_id, req.actor_role)
        if req.action == "expire":
            return expire(req.node_id, req.actor_id, req.actor_role)
        if req.action == "supersede":
            if not req.new_title or not req.new_content:
                raise HTTPException(400, "supersede requires new_title and new_content")
            return supersede(req.node_id, req.new_title, req.new_content,
                             req.actor_id, req.actor_role)
        raise HTTPException(400, f"Unknown action: {req.action}")
    except InvalidTransitionError as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/reset")
def reset_demo():
    # inline reset (mirrors reset_demo.py) so the frontend has a button
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("UPDATE knowledge_nodes SET status='ACTIVE' WHERE status='REVIEW_REQUIRED'")
        cur.execute("UPDATE knowledge_nodes SET status='ACTIVE', superseded_by=NULL WHERE id='N-M08'")
        cur.execute("DELETE FROM edges WHERE source_id LIKE 'N-%-V%' OR edge_type='SUPERSEDES'")
        cur.execute("DELETE FROM knowledge_nodes WHERE id LIKE 'N-%-V%'")
        cur.execute("DELETE FROM audit_log WHERE action IN "
                    "('CASCADE_TRIGGER','STATUS_CHANGE','CASCADE_SKIP','REVIEW_CONFIRMED','SUPERSEDE')")
        cur.execute("DELETE FROM pulse_alerts")
    return {"status": "reset complete"}


@app.get("/")
def root():
    return {"service": "BRAHMO Governance Engine", "docs": "/docs"}
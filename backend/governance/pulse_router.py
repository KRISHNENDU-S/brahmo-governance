"""
pulse_router.py  (STEP 4 - targeted notifications)
==================================================
After a cascade, route alerts to the RIGHT people - and nobody else.

ROUTING RULES:
  - notify roles HOD and EDITOR only  (not VIEWER, not ADMIN)
  - only users in a department that actually has affected nodes
  - ONE alert per user per cascade  (aggregated, never one-per-node)

AGGREGATION:
  A cascade touching 9 nodes does NOT send 9 alerts. It sends one alert
  per affected doctor: "N of your department's nodes need review."
  All alerts share the cascade_id so they can be grouped/cleared together.

SEVERITY:
  CONSTRAINT superseded -> URGENT   (a hard rule changed)
  cascade (general)     -> URGENT
  health score < 0.70   -> WARNING
  review completed      -> INFO
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uuid
from db import get_connection


def _affected_departments(conn, node_ids: list[str]) -> set[str]:
    """Departments that own the affected nodes."""
    if not node_ids:
        return set()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT department FROM knowledge_nodes WHERE id = ANY(%s)",
            (node_ids,),
        )
        return {r[0] for r in cur.fetchall() if r[0]}


def _nodes_per_department(conn, node_ids: list[str]) -> dict[str, int]:
    """Count of affected nodes grouped by department."""
    counts: dict[str, int] = {}
    if not node_ids:
        return counts
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT department, COUNT(*) FROM knowledge_nodes
            WHERE id = ANY(%s) GROUP BY department
            """,
            (node_ids,),
        )
        for dept, cnt in cur.fetchall():
            if dept:
                counts[dept] = cnt
    return counts


def _recipients(conn, departments: set[str], org_id: str) -> list[dict]:
    """Users to notify: HOD/EDITOR in the affected departments."""
    if not departments:
        return []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, role, department FROM users
            WHERE org_id = %s
              AND department = ANY(%s)
              AND role IN ('HOD', 'EDITOR')
            """,
            (org_id, list(departments)),
        )
        return [{"id": r[0], "name": r[1], "role": r[2], "department": r[3]}
                for r in cur.fetchall()]


def route_cascade_alerts(cascade_result: dict, org_id: str = "supra",
                         source_title: str = "a protocol") -> list[dict]:
    """
    Create one aggregated pulse alert per affected doctor.
    `cascade_result` is what run_cascade() returns.
    Returns the list of alerts created.
    """
    affected_ids = [a["node_id"] for a in cascade_result.get("affected", [])]
    cascade_id = cascade_result.get("cascade_id", str(uuid.uuid4()))
    source = cascade_result.get("source", "")

    created: list[dict] = []

    with get_connection() as conn:
        departments = _affected_departments(conn, affected_ids)
        dept_counts = _nodes_per_department(conn, affected_ids)
        recipients = _recipients(conn, departments, org_id)

        with conn.cursor() as cur:
            for user in recipients:
                count = dept_counts.get(user["department"], 0)
                if count == 0:
                    continue
                alert_id = str(uuid.uuid4())
                title = f"{source} superseded — {count} of your nodes need review"
                body = (f"A cascade from {source} flagged {count} node(s) in your "
                        f"department ({user['department']}) as REVIEW_REQUIRED.")
                link = f"/nodes?status=REVIEW_REQUIRED&dept={user['department']}"
                cur.execute(
                    """
                    INSERT INTO pulse_alerts
                      (id, org_id, user_id, alert_type, severity, title, body,
                       link, cascade_id, is_read)
                    VALUES (%s,%s,%s,'CASCADE','URGENT',%s,%s,%s,%s,FALSE)
                    """,
                    (alert_id, org_id, user["id"], title, body, link, cascade_id),
                )
                created.append({"user": user["name"], "role": user["role"],
                                "department": user["department"],
                                "count": count, "severity": "URGENT"})

    return created


if __name__ == "__main__":
    # Run a cascade, then route alerts for it.
    from governance.cascade_engine import run_cascade
    result = run_cascade("N-M08")
    alerts = route_cascade_alerts(result, source_title="Sepsis Protocol v2")

    print(f"Pulse alerts created: {len(alerts)}\n")
    for a in alerts:
        print(f"   [{a['severity']}] -> {a['user']} ({a['role']}, "
              f"{a['department']}): {a['count']} nodes need review")
    print("\nNote: only Medicine HOD/EDITOR notified. Ortho + VIEWER + ADMIN excluded.")
"""
review_handler.py  (STEP 5 - the doctor's review actions)
=========================================================
After a cascade flags nodes REVIEW_REQUIRED, a doctor reviews each one
and picks an action. This module performs that action safely (through
the state machine) and writes the audit trail.

THREE ACTIONS:
  confirm(node)   REVIEW_REQUIRED -> ACTIVE      "still valid"
  expire(node)    REVIEW_REQUIRED -> EXPIRED     "no longer relevant"
  supersede(node) REVIEW_REQUIRED -> SUPERSEDED  "needs update"
                  + creates a NEW node (the replacement) in ACTIVE

Every action:
  - validates the transition via status_machine (illegal -> rejected)
  - updates the node
  - writes a REVIEW_CONFIRMED audit entry
The first confirmed review also ends the health-score deferral window
(see health_state.py) so the score recomputes and starts recovering.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uuid
from db import get_connection
from governance.status_machine import assert_transition, InvalidTransitionError


def _current(conn, node_id: str):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT status, type, department, org_id FROM knowledge_nodes WHERE id = %s",
            (node_id,),
        )
        return cur.fetchone()


def _audit(cur, node_id, old, new, actor, org, reason):
    cur.execute(
        """
        INSERT INTO audit_log
          (id, node_id, action, old_value, new_value, actor_id, org_id, reason)
        VALUES (%s,%s,'REVIEW_CONFIRMED',%s,%s,%s,%s,%s)
        """,
        (str(uuid.uuid4()), node_id, old, new, actor, org, reason),
    )


def _do_simple(node_id, new_status, actor_id, actor_role, reason):
    """Shared logic for confirm (->ACTIVE) and expire (->EXPIRED)."""
    with get_connection() as conn:
        row = _current(conn, node_id)
        if not row:
            raise ValueError(f"Node {node_id} not found")
        old_status, _type, _dept, org = row

        # state machine: reject illegal transitions
        assert_transition(old_status, new_status, actor_role)

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE knowledge_nodes SET status = %s WHERE id = %s",
                (new_status, node_id),
            )
            _audit(cur, node_id, old_status, new_status, actor_id, org, reason)

    return {"node_id": node_id, "old": old_status, "new": new_status}


def confirm(node_id, actor_id="U-MEERA", actor_role="HOD"):
    """'Still valid' -> back to ACTIVE."""
    return _do_simple(node_id, "ACTIVE", actor_id, actor_role,
                      "Reviewed: still valid, restored to ACTIVE")


def expire(node_id, actor_id="U-MEERA", actor_role="HOD"):
    """'No longer relevant' -> EXPIRED."""
    return _do_simple(node_id, "EXPIRED", actor_id, actor_role,
                      "Reviewed: no longer relevant, marked EXPIRED")


def supersede(node_id, new_title, new_content,
              actor_id="U-MEERA", actor_role="HOD"):
    """
    'Needs update' -> old node SUPERSEDED, a new ACTIVE node created,
    linked by a SUPERSEDES edge and superseded_by pointer.
    """
    with get_connection() as conn:
        row = _current(conn, node_id)
        if not row:
            raise ValueError(f"Node {node_id} not found")
        old_status, node_type, dept, org = row

        assert_transition(old_status, "SUPERSEDED", actor_role)

        new_id = f"{node_id}-V{uuid.uuid4().hex[:4]}"
        with conn.cursor() as cur:
            # create the replacement (inherits type/dept/level)
            cur.execute(
                """
                INSERT INTO knowledge_nodes
                  (id, org_id, hierarchy_level_id, type, title, content,
                   importance, status, department, created_by)
                SELECT %s, org_id, hierarchy_level_id, type, %s, %s,
                       importance, 'ACTIVE', department, %s
                FROM knowledge_nodes WHERE id = %s
                """,
                (new_id, new_title, new_content, actor_id, node_id),
            )
            # retire the old one + point it at the replacement
            cur.execute(
                "UPDATE knowledge_nodes SET status = 'SUPERSEDED', superseded_by = %s WHERE id = %s",
                (new_id, node_id),
            )
            # link them
            cur.execute(
                "INSERT INTO edges (id, source_id, target_id, edge_type) "
                "VALUES (%s,%s,%s,'SUPERSEDES')",
                (str(uuid.uuid4()), new_id, node_id),
            )
            _audit(cur, node_id, old_status, "SUPERSEDED", actor_id, org,
                   f"Reviewed: superseded by new version {new_id}")

    return {"node_id": node_id, "old": old_status, "new": "SUPERSEDED",
            "replacement": new_id}


if __name__ == "__main__":
    from governance.cascade_engine import run_cascade

    # set up: cascade flags 9 nodes
    run_cascade("N-M08")
    print("Cascade done. Now reviewing some flagged nodes...\n")

    # confirm one
    r1 = confirm("N-DRV-01", actor_id="U-ANANYA", actor_role="EDITOR")
    print(f"confirm  N-DRV-01: {r1['old']} -> {r1['new']}")

    # expire one
    r2 = expire("N-DRV-05", actor_id="U-MEERA", actor_role="HOD")
    print(f"expire   N-DRV-05: {r2['old']} -> {r2['new']}")

    # try an illegal one to prove the guard works
    try:
        confirm("N-DRV-01", actor_role="EDITOR")  # already ACTIVE now
        # ACTIVE -> ACTIVE is not a defined transition
    except InvalidTransitionError as e:
        print(f"blocked  N-DRV-01 again: {e}")
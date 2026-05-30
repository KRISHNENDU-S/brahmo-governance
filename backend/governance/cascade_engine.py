"""
cascade_engine.py  (STEP 2b - full engine with database writes)
===============================================================
When a node is superseded, its DERIVED_FROM descendants become
"stale by association" and must be flagged REVIEW_REQUIRED.

plan_cascade()  -> read-only: works out WHAT would change (the 3 guards live here)
run_cascade()   -> writes:    applies the plan atomically + writes the audit trail

THE THREE GUARDS (safety core):
  1. max_depth   - bound the ripple (default 3)
  2. visited set - never process a node twice (multi-parent / loops)
  3. LEGAL_HOLD  - skip frozen nodes, but RECORD the skip (compliance)
Plus SUPERSEDED / already-REVIEW_REQUIRED are skipped (idempotent).

ATOMICITY: run_cascade() does all UPDATEs + INSERTs in ONE transaction.
           Either the whole cascade lands, or nothing does.

Edge convention: (source, target, 'DERIVED_FROM') => source DERIVED_FROM target
  => children of X = source_ids where target_id = X
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uuid
from collections import deque
from db import get_connection
from governance.status_machine import is_valid_transition

DEFAULT_MAX_DEPTH = 3


# ----------------------------------------------------------------------
# READ-ONLY PLANNING (the BFS walk + the three guards)
# ----------------------------------------------------------------------
def _get_children(conn, node_id: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT source_id FROM edges
            WHERE target_id = %s AND edge_type = 'DERIVED_FROM'
            """,
            (node_id,),
        )
        return [r[0] for r in cur.fetchall()]


def _get_status(conn, node_id: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM knowledge_nodes WHERE id = %s", (node_id,))
        row = cur.fetchone()
        return row[0] if row else None


def plan_cascade(conn, source_node_id: str, max_depth: int = DEFAULT_MAX_DEPTH) -> dict:
    """Walk DERIVED_FROM edges (BFS). Returns a plan; writes nothing."""
    affected: list[dict] = []
    skipped: list[dict] = []
    visited: set[str] = {source_node_id}
    queue: deque[tuple[str, int]] = deque([(source_node_id, 0)])

    while queue:
        current_id, depth = queue.popleft()      # BFS / FIFO

        if depth >= max_depth:                    # GUARD 1: depth bound
            continue

        for child_id in _get_children(conn, current_id):
            if child_id in visited:               # GUARD 2: visited set
                continue
            visited.add(child_id)

            status = _get_status(conn, child_id)
            child_depth = depth + 1

            if status == "LEGAL_HOLD":            # GUARD 3: compliance skip
                skipped.append({"node_id": child_id, "depth": child_depth,
                                "reason": "LEGAL_HOLD - status frozen during cascade"})
                continue
            if status == "SUPERSEDED":
                skipped.append({"node_id": child_id, "depth": child_depth,
                                "reason": "already SUPERSEDED"})
                continue
            if status == "REVIEW_REQUIRED":
                skipped.append({"node_id": child_id, "depth": child_depth,
                                "reason": "already REVIEW_REQUIRED"})
                continue

            affected.append({"node_id": child_id, "depth": child_depth})
            queue.append((child_id, child_depth))

    return {"source": source_node_id, "affected": affected,
            "skipped": skipped, "max_depth": max_depth}


# ----------------------------------------------------------------------
# WRITE SIDE (apply the plan atomically + full audit trail)
# ----------------------------------------------------------------------
def _audit(cur, node_id, action, old, new, actor, org, reason, cascade_id):
    cur.execute(
        """
        INSERT INTO audit_log
          (id, node_id, action, old_value, new_value, actor_id, org_id, reason, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (str(uuid.uuid4()), node_id, action, old, new, actor, org, reason,
         f'{{"cascade_id": "{cascade_id}"}}'),
    )


def run_cascade(source_node_id: str, actor_id: str = "U-MEERA",
                org_id: str = "supra", max_depth: int = DEFAULT_MAX_DEPTH) -> dict:
    """
    Execute the cascade: flag affected nodes REVIEW_REQUIRED, log every change,
    log every LEGAL_HOLD skip, and record one CASCADE_TRIGGER event.
    All writes happen in a single transaction (atomic).
    """
    cascade_id = str(uuid.uuid4())

    with get_connection() as conn:
        plan = plan_cascade(conn, source_node_id, max_depth)

        with conn.cursor() as cur:
            # 1) record the trigger event itself
            _audit(cur, source_node_id, "CASCADE_TRIGGER", None, None,
                   actor_id, org_id,
                   f"Cascade from {source_node_id}: "
                   f"{len(plan['affected'])} affected, {len(plan['skipped'])} skipped",
                   cascade_id)

            # 2) flag each affected node ACTIVE -> REVIEW_REQUIRED (+ audit)
            for item in plan["affected"]:
                nid = item["node_id"]
                # state-machine safety: confirm the transition is legal
                if not is_valid_transition("ACTIVE", "REVIEW_REQUIRED"):
                    continue
                cur.execute(
                    "UPDATE knowledge_nodes SET status = 'REVIEW_REQUIRED' WHERE id = %s",
                    (nid,),
                )
                _audit(cur, nid, "STATUS_CHANGE", "ACTIVE", "REVIEW_REQUIRED",
                       actor_id, org_id,
                       f"Cascade from {source_node_id} at depth {item['depth']}",
                       cascade_id)

            # 3) log each LEGAL_HOLD skip (compliance: never silent)
            for item in plan["skipped"]:
                if "LEGAL_HOLD" in item["reason"]:
                    _audit(cur, item["node_id"], "CASCADE_SKIP", "LEGAL_HOLD", "LEGAL_HOLD",
                           actor_id, org_id,
                           f"Skipped during cascade from {source_node_id}: {item['reason']}",
                           cascade_id)
            # conn commits automatically on clean exit of the `with` block

    return {**plan, "cascade_id": cascade_id}


if __name__ == "__main__":
    result = run_cascade("N-M08")   # supersede Sepsis v2 -> cascade

    print(f"Cascade {result['cascade_id'][:8]}... from {result['source']}\n")
    print(f"AFFECTED ({len(result['affected'])}) -> now REVIEW_REQUIRED:")
    for a in sorted(result["affected"], key=lambda x: (x["depth"], x["node_id"])):
        print(f"   depth {a['depth']}  {a['node_id']}")
    print(f"\nSKIPPED ({len(result['skipped'])}):")
    for s in sorted(result["skipped"], key=lambda x: (x["depth"], x["node_id"])):
        print(f"   depth {s['depth']}  {s['node_id']}  <- {s['reason']}")
    print("\nAll changes + audit entries committed in one transaction.")
"""
health_score.py  (STEP 3a - the 4-dimension computation)
========================================================
Computes a Knowledge Health Score from LIVE database state.
Pure SQL aggregation - ZERO LLM, fully deterministic.

FOUR DIMENSIONS (each 0.0 - 1.0):
  Coverage    = hierarchy levels with >=1 ACTIVE node / total levels
  Freshness   = ACTIVE & not-expiring nodes / (ACTIVE + REVIEW_REQUIRED)
  Balance     = 1 - (stddev of type counts / mean of type counts)
                (penalises a graph that is all one type)
  Consistency = ACTIVE / (ACTIVE + REVIEW_REQUIRED)
                (REVIEW_REQUIRED nodes = unresolved = inconsistency)

OVERALL = weighted sum (weights come from organizations.config)

Scope: scores are computed per organization. A department filter can be
added later for per-dept dashboards (surprise test) without changing the math.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import statistics
from db import get_connection

DEFAULT_WEIGHTS = {"coverage": 0.25, "freshness": 0.30,
                   "balance": 0.20, "consistency": 0.25}


def _get_weights(conn, org_id: str) -> dict:
    """Read health-score weights from org config; fall back to defaults."""
    with conn.cursor() as cur:
        cur.execute("SELECT config FROM organizations WHERE id = %s", (org_id,))
        row = cur.fetchone()
    if row and row[0] and "health_score_weights" in row[0]:
        return row[0]["health_score_weights"]
    return DEFAULT_WEIGHTS


def _coverage(conn, org_id: str) -> float:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM hierarchy_levels WHERE org_id = %s", (org_id,))
        total_levels = cur.fetchone()[0]
        cur.execute(
            """
            SELECT COUNT(DISTINCT hierarchy_level_id)
            FROM knowledge_nodes
            WHERE org_id = %s AND status = 'ACTIVE'
            """,
            (org_id,),
        )
        populated = cur.fetchone()[0]
    return populated / total_levels if total_levels else 0.0


def _freshness(conn, org_id: str) -> float:
    with conn.cursor() as cur:
        # denominator = nodes "in play" (ACTIVE or awaiting review)
        cur.execute(
            """
            SELECT COUNT(*) FROM knowledge_nodes
            WHERE org_id = %s AND status IN ('ACTIVE', 'REVIEW_REQUIRED')
            """,
            (org_id,),
        )
        in_play = cur.fetchone()[0]
        # numerator = ACTIVE nodes that are not past their validity window
        cur.execute(
            """
            SELECT COUNT(*) FROM knowledge_nodes
            WHERE org_id = %s AND status = 'ACTIVE'
              AND (valid_until IS NULL OR valid_until > NOW())
            """,
            (org_id,),
        )
        fresh = cur.fetchone()[0]
    return fresh / in_play if in_play else 1.0


def _balance(conn, org_id: str) -> float:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT type, COUNT(*) FROM knowledge_nodes
            WHERE org_id = %s AND status NOT IN ('SUPERSEDED')
            GROUP BY type
            """,
            (org_id,),
        )
        rows = cur.fetchall()
    # ensure all 4 types represented (missing type = count 0)
    counts = {"CONSTRAINT": 0, "DECISION": 0, "ANTI_PATTERN": 0, "FACT": 0}
    for t, c in rows:
        counts[t] = c
    values = list(counts.values())
    mean = statistics.mean(values)
    if mean == 0:
        return 0.0
    std = statistics.pstdev(values)            # population stddev
    return max(0.0, 1.0 - (std / mean))


def _consistency(conn, org_id: str) -> float:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              COUNT(*) FILTER (WHERE status = 'ACTIVE'),
              COUNT(*) FILTER (WHERE status = 'REVIEW_REQUIRED')
            FROM knowledge_nodes WHERE org_id = %s
            """,
            (org_id,),
        )
        active, review = cur.fetchone()
    denom = active + review
    return active / denom if denom else 1.0


def compute_health_score(org_id: str = "supra") -> dict:
    """Compute all 4 dimensions + weighted overall from live data."""
    with get_connection() as conn:
        weights = _get_weights(conn, org_id)
        coverage = _coverage(conn, org_id)
        freshness = _freshness(conn, org_id)
        balance = _balance(conn, org_id)
        consistency = _consistency(conn, org_id)

    overall = (coverage * weights["coverage"]
               + freshness * weights["freshness"]
               + balance * weights["balance"]
               + consistency * weights["consistency"])

    return {
        "coverage": round(coverage, 2),
        "freshness": round(freshness, 2),
        "balance": round(balance, 2),
        "consistency": round(consistency, 2),
        "overall": round(overall, 2),
    }


if __name__ == "__main__":
    s = compute_health_score("supra")
    print("KNOWLEDGE HEALTH SCORE (live)\n")
    print(f"  Coverage    : {s['coverage']:.2f}")
    print(f"  Freshness   : {s['freshness']:.2f}")
    print(f"  Balance     : {s['balance']:.2f}")
    print(f"  Consistency : {s['consistency']:.2f}")
    print(f"  ---------------------------")
    print(f"  OVERALL     : {s['overall']:.2f}  ({s['overall']*100:.0f}%)")
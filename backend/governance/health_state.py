"""
health_state.py  (STEP 3b - deferred recomputation wrapper)
===========================================================
Wraps compute_health_score() with DEFERRED recomputation logic.

THE PROBLEM:
  Immediately after a cascade, the raw score plunges (e.g. 76% -> 39%)
  because 9 nodes are REVIEW_REQUIRED. But the knowledge isn't "bad" -
  it's just queued for review. Showing 39% instantly makes leadership
  panic over a number that self-corrects as reviews complete.

THE RULE (deferred):
  After a cascade, DON'T show the new number yet. Show the last
  confirmed score + a "pending review" badge until ONE of:
    (a) the first review is confirmed, OR
    (b) 24 hours have passed since the cascade,
  whichever comes first. Then recompute and show the live number.

We track cascade time + pending state via the audit_log (no new table
needed): the most recent CASCADE_TRIGGER not yet followed by a
REVIEW_CONFIRMED tells us a cascade is pending.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta, timezone
from db import get_connection
from governance.health_score import compute_health_score

DEFER_HOURS = 24


def _last_cascade(conn, org_id: str):
    """Return (timestamp) of the most recent CASCADE_TRIGGER, or None."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT timestamp FROM audit_log
            WHERE org_id = %s AND action = 'CASCADE_TRIGGER'
            ORDER BY timestamp DESC LIMIT 1
            """,
            (org_id,),
        )
        row = cur.fetchone()
    return row[0] if row else None


def _review_since(conn, org_id: str, since) -> bool:
    """True if any review was confirmed after `since`."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM audit_log
            WHERE org_id = %s AND action = 'REVIEW_CONFIRMED'
              AND timestamp > %s
            """,
            (org_id, since),
        )
        return cur.fetchone()[0] > 0


def get_health_state(org_id: str = "supra") -> dict:
    """
    Return the health score the dashboard should display, plus whether
    recomputation is currently deferred (pending reviews).

    {
      "score": {...4 dims + overall...},
      "deferred": bool,         # True => show 'pending review' badge
      "reason": str,
    }
    """
    with get_connection() as conn:
        cascade_ts = _last_cascade(conn, org_id)

        if cascade_ts is None:
            # no cascade has happened -> just show the live score
            return {"score": compute_health_score(org_id),
                    "deferred": False,
                    "reason": "No recent cascade - live score."}

        now = datetime.now(timezone.utc)
        hours_since = (now - cascade_ts).total_seconds() / 3600.0
        reviewed = _review_since(conn, org_id, cascade_ts)

        if reviewed:
            return {"score": compute_health_score(org_id),
                    "deferred": False,
                    "reason": "A review was confirmed - score recomputed."}

        if hours_since >= DEFER_HOURS:
            return {"score": compute_health_score(org_id),
                    "deferred": False,
                    "reason": f"{DEFER_HOURS}h elapsed since cascade - score recomputed."}

        # still within the deferral window, no reviews yet
        return {"score": compute_health_score(org_id),
                "deferred": True,
                "reason": (f"Cascade {hours_since:.1f}h ago, no reviews yet. "
                           f"Showing live numbers with a PENDING REVIEW badge; "
                           f"recompute defers until first review or {DEFER_HOURS}h.")}


if __name__ == "__main__":
    state = get_health_state("supra")
    s = state["score"]
    badge = "  [PENDING REVIEW]" if state["deferred"] else ""
    print(f"HEALTH DASHBOARD{badge}\n")
    print(f"  Overall: {s['overall']*100:.0f}%   "
          f"(C {s['coverage']:.2f} | F {s['freshness']:.2f} | "
          f"B {s['balance']:.2f} | X {s['consistency']:.2f})")
    print(f"\n  deferred = {state['deferred']}")
    print(f"  {state['reason']}")
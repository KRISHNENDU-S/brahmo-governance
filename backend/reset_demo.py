"""
reset_demo.py
=============
Restores the database to its pre-cascade state so the demo can be
re-run cleanly. Run this between demo runs.

What it does:
  - all REVIEW_REQUIRED nodes  -> ACTIVE
  - N-M08 (Sepsis v2)          -> ACTIVE (in case a supersede test ran)
  - N-HELD stays LEGAL_HOLD, N-EXP stays EXPIRED (their seeded states)
  - clears cascade/review audit rows + pulse alerts generated during demos
  - removes any demo-created Sepsis v3 node
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from db import get_connection


def reset():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1) un-flag everything the cascade touched
            cur.execute(
                "UPDATE knowledge_nodes SET status = 'ACTIVE' "
                "WHERE status = 'REVIEW_REQUIRED'"
            )
            # 2) restore the superseded source if a supersede test ran
            cur.execute(
                "UPDATE knowledge_nodes SET status = 'ACTIVE', superseded_by = NULL "
                "WHERE id = 'N-M08'"
            )
            # 3) remove any demo-created replacement node (e.g. Sepsis v3)
            cur.execute("DELETE FROM edges WHERE source_id LIKE 'N-M08-V3%' "
                        "OR target_id LIKE 'N-M08-V3%'")
            cur.execute("DELETE FROM knowledge_nodes WHERE id LIKE 'N-M08-V3%'")
            # 4) clear demo-generated audit + alerts
            cur.execute("DELETE FROM audit_log WHERE action IN "
                        "('CASCADE_TRIGGER','STATUS_CHANGE','CASCADE_SKIP',"
                        "'REVIEW_CONFIRMED','SUPERSEDE')")
            cur.execute("DELETE FROM pulse_alerts")

    print("Demo reset complete. All nodes ACTIVE (except N-HELD=LEGAL_HOLD, N-EXP=EXPIRED).")


if __name__ == "__main__":
    reset()
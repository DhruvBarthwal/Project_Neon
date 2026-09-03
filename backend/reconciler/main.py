import argparse
import os
import re

import psycopg2
import psycopg2.extras

from .matcher import run_matching
from .constants import FEE_EPSILON,FEE_PCT,GST_PCT,AMOUNT_TOLERANCE, DATE_TOLERANCE_DAYS
from dotenv import load_dotenv
from reconciler.audit_service import record_business_audit
from reconciler.db import get_connection

load_dotenv()

#=========== Convert all UTRs to UPPER CASE ==========#
    
def normalize_utr(utr):
    if not utr:
        return None
    return re.sub(r"\s+","",utr).upper()

#============ Fetching gateway and bank rows ===========#

def fetch_period(conn, period):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """SELECT payment_id, order_id, amount, status, utr, created_at FROM gateway_records WHERE period = %s""",
            (period,),
        )
        gateway_rows = cur.fetchall()
        
        cur.execute(
            """SELECT id, utr, amount, credited_at, narration FROM bank_records WHERE period = %s""",
            (period,),
        )
        bank_rows = cur.fetchall()
        
    #======== Normalizing values =========#
        
    for g in gateway_rows:
        g["utr_norm"] = normalize_utr(g["utr"])
        g["amount"] = round(float(g["amount"]),2)
    
    for b in bank_rows:
        b["utr_norm"] = normalize_utr(b["utr"])
        b["amount"] = round(float(b["amount"]),2)
        
    return gateway_rows, bank_rows


def fetch_merchant_records(conn, period):
    with conn.cursor() as cur:
        cur.execute(
            """SELECT order_id, payment_id, amount, status
               FROM merchant_records WHERE period = %s""",
            (period,),
        )
        rows = cur.fetchall()
    return [
        {"order_id": r[0], "payment_id": r[1], "amount": float(r[2]), "status": r[3]}
        for r in rows
    ]
    
#========== Writing Tables ==============#

def write_results(conn, period, matches, exceptions, triggered_by=None, trigger_source="manual"):
    import json

    with conn.cursor() as cur:
        # 1. Clear previous run data for this period
        cur.execute("DELETE FROM ledger_matches WHERE period = %s", (period,))
        cur.execute("DELETE FROM exceptions WHERE period = %s", (period,))

        # 2. Insert matched rows
        for m in matches:
            cur.execute(
                """INSERT INTO ledger_matches
                   (payment_id, period, match_type, matched_amount, bank_amount, risk, explanation)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (
                    m["payment_id"],
                    period,
                    m["match_type"],
                    m["matched_amount"],
                    m["bank_amount"],
                    m["risk"],
                    m["explanation"],
                ),
            )

        # 3. Insert exception rows
        for e in exceptions:
            cur.execute(
                """INSERT INTO exceptions
                   (payment_id, period, reason_code, reason_detail, recommended_action, risk, amount)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (
                    e["payment_id"],
                    period,
                    e["reason_code"],
                    e["reason_detail"],
                    e["recommended_action"],
                    e["risk"],
                    e["amount"],
                ),
            )

        # 4. Engine Run Metric
        total = len(matches) + len(exceptions)
        match_rate = round(len(matches) / total * 100, 2) if total else 0
        cur.execute(
            """INSERT INTO reconciliation_runs
               (period, triggered_by, trigger_source, total_records, matched_count, exception_count, match_rate)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (
                period,
                triggered_by or "auto",
                trigger_source,
                total,
                len(matches),
                len(exceptions),
                match_rate,
            ),
        )

        # 5. Business Audit Log (Reuses the active transaction cursor)
        actor = triggered_by or "reconciliation_engine"
        total_risk = sum(float(e.get("amount") or 0.0) for e in exceptions)
        metadata = json.dumps({
            "matches_count": len(matches),
            "exceptions_count": len(exceptions),
            "match_rate_pct": match_rate,
            "trigger_source": trigger_source,
        })

        cur.execute(
            """INSERT INTO audit_logs 
               (period, actor, event_type, intent, target_identifier, outcome_status, exposure_amount, metadata)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                period,
                actor,
                "CYCLE_RUN",
                "reconcile_cycle",
                period,
                "COMPLETED",
                total_risk,
                metadata,
            ),
        )

    # 6. Single atomic commit for ledger data + audit trail
    conn.commit()
 
def print_summary(period, total, matches, exceptions):
    n_match = len(matches)
    n_exc = len(exceptions)
    by_type = {}
    for m in matches:
        by_type[m["match_type"]] = by_type.get(m["match_type"], 0) + 1
    at_risk = round(sum(e["amount"] or 0 for e in exceptions), 2)
 
    print(f"\n=== Reconciliation summary for {period} ===")
    print(f"Total gateway records : {total}")
    print(f"Auto-match rate       : {n_match/total*100:.1f}%  ({n_match}/{total})")
    print(f"Exception rate        : {n_exc/total*100:.1f}%  ({n_exc}/{total})")
    print(f"Amount at risk         : ₹{at_risk}")
    print("Match type breakdown  :", by_type)
 
 
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", type=str, required=True)
    args = ap.parse_args()
 
    conn = get_connection()
    try:
        gateway_rows, bank_rows = fetch_period(conn, args.period)
        if not gateway_rows:
            print(f"No gateway records found for period {args.period}. Run the generator first.")
            raise SystemExit(1)
 
        matches, exceptions = run_matching(gateway_rows, bank_rows)
        write_results(conn, args.period, matches, exceptions)
        print_summary(args.period, len(gateway_rows), matches, exceptions)
    finally:
        conn.close()
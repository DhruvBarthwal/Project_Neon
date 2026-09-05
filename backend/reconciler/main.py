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

def fetch_incremental_period(conn, period: str, since):
    """Returns only the rows that matter for an incremental reconcile pass:
    - gateway rows inserted since the last run
    - gateway rows that currently have an open exception for this period
      (so lump-sum groups and previously-failed matches get re-evaluated
       against the LATEST bank/merchant data, not just brand-new rows)
    Bank/merchant rows are refetched in full for the period since they're
    cheap relative to gateway volume and correctness depends on seeing the
    current state of both tables, not just new rows in them.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT DISTINCT g.payment_id, g.order_id, g.amount, g.status, g.utr, g.created_at
            FROM gateway_records g
            WHERE g.period = %s
              AND (
                    g.inserted_at > %s
                 OR g.payment_id IN (SELECT payment_id FROM exceptions WHERE period = %s)
              )
            """,
            (period, since, period),
        )
        gateway_rows = cur.fetchall()
 
        cur.execute(
            """SELECT id, utr, amount, credited_at, narration FROM bank_records WHERE period = %s""",
            (period,),
        )
        bank_rows = cur.fetchall()
 
    for g in gateway_rows:
        g["utr_norm"] = normalize_utr(g["utr"])
        g["amount"] = round(float(g["amount"]), 2)
    for b in bank_rows:
        b["utr_norm"] = normalize_utr(b["utr"])
        b["amount"] = round(float(b["amount"]), 2)
 
    return gateway_rows, bank_rows

def fetch_already_matched_ids(conn, period: str) -> set:
    """Payment IDs already cleanly resolved in a prior run — these must be
    excluded from re-matching so an incremental pass doesn't reconsider or
    double-count them."""
    with conn.cursor() as cur:
        cur.execute("SELECT payment_id FROM ledger_matches WHERE period = %s", (period,))
        return {r[0] for r in cur.fetchall()}
 
 
def get_last_run_at(conn, period: str):
    """Timestamp of the most recent reconciliation run for this period, or
    None if it has never been run — caller should fall back to a full run
    in that case."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT MAX(run_at) FROM reconciliation_runs WHERE period = %s",
            (period,),
        )
        return cur.fetchone()[0]

#========== Writing Tables ==============#

def write_results(conn, period, matches, exceptions, triggered_by=None, trigger_source="manual"):
    """Upserts matches/exceptions for only the payment_ids being written this
    call — does NOT wipe the rest of the period's history. Safe to call
    repeatedly on an incremental subset without losing prior results.
    A payment that is now a clean match must also be removed from
    `exceptions` if it was previously flagged there (that's the whole point
    of an exception getting resolved), so we explicitly delete it from the
    other table before inserting.
    """
    with conn.cursor() as cur:
        match_ids = [m["payment_id"] for m in matches]
        exception_ids = [e["payment_id"] for e in exceptions]
 
        # A payment newly resolved as a match must be cleared out of exceptions,
        # and vice versa a payment newly flagged as an exception must be
        # cleared out of matches (covers rare re-classification edge cases).
        if match_ids:
            cur.execute(
                "DELETE FROM exceptions WHERE period = %s AND payment_id = ANY(%s)",
                (period, match_ids),
            )
        if exception_ids:
            cur.execute(
                "DELETE FROM ledger_matches WHERE period = %s AND payment_id = ANY(%s)",
                (period, exception_ids),
            )
 
        for m in matches:
            cur.execute(
                """INSERT INTO ledger_matches
                   (payment_id, period, match_type, matched_amount, bank_amount, risk, explanation)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (payment_id, period) DO UPDATE SET
                       match_type = EXCLUDED.match_type,
                       matched_amount = EXCLUDED.matched_amount,
                       bank_amount = EXCLUDED.bank_amount,
                       risk = EXCLUDED.risk,
                       explanation = EXCLUDED.explanation""",
                (m["payment_id"], period, m["match_type"], m["matched_amount"],
                 m["bank_amount"], m["risk"], m["explanation"]),
            )
        for e in exceptions:
            cur.execute(
                """INSERT INTO exceptions
                   (payment_id, period, reason_code, reason_detail, recommended_action, risk, amount)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (payment_id, period) DO UPDATE SET
                       reason_code = EXCLUDED.reason_code,
                       reason_detail = EXCLUDED.reason_detail,
                       recommended_action = EXCLUDED.recommended_action,
                       risk = EXCLUDED.risk,
                       amount = EXCLUDED.amount""",
                (e["payment_id"], period, e["reason_code"], e["reason_detail"],
                 e["recommended_action"], e["risk"], e["amount"]),
            )
 
        # ---- audit trail: totals must reflect the WHOLE period, not just this batch ----
        cur.execute("SELECT COUNT(*) FROM gateway_records WHERE period = %s", (period,))
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ledger_matches WHERE period = %s", (period,))
        total_matched = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM exceptions WHERE period = %s", (period,))
        total_exceptions = cur.fetchone()[0]
        match_rate = round(total_matched / total * 100, 2) if total else 0
 
        cur.execute(
            """INSERT INTO reconciliation_runs
               (period, triggered_by, trigger_source, total_records, matched_count, exception_count, match_rate)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (period, triggered_by or "auto", trigger_source, total, total_matched, total_exceptions, match_rate),
        )
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
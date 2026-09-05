from datetime import datetime
from reconciler.main import get_connection
import re

REASON_LABELS = {
    "no_corresponding_bank_record": "No corresponding bank record",
    "amount_or_date_mismatch_unresolved": "Amount and date both unresolved",
    "held_back_from_lump_sum": "Held back from lump-sum payout",
    "merchant_status_lag": "Settled, but merchant system hasn't caught up",
    "unverified_merchant_claim": "Merchant claims paid — unverified",
    "ambiguous_lump_sum_match": "Multiple valid combinations — needs manual review",
    "lump_sum_too_complex": "Lump-sum group too large to auto-resolve",
}


def list_runs(period: str | None = None, limit: int = 20):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if period:
                cur.execute(
                    """SELECT period, triggered_by, trigger_source, total_records,
                              matched_count, exception_count, match_rate, run_at
                       FROM reconciliation_runs
                       WHERE period = %s
                       ORDER BY run_at DESC LIMIT %s""",
                    (period, limit),
                )
            else:
                cur.execute(
                    """SELECT period, triggered_by, trigger_source, total_records,
                              matched_count, exception_count, match_rate, run_at
                       FROM reconciliation_runs
                       ORDER BY run_at DESC LIMIT %s""",
                    (limit,),
                )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "period": r[0],
            "triggeredBy": r[1],
            "triggerSource": r[2],
            "totalRecords": r[3],
            "matchedCount": r[4],
            "exceptionCount": r[5],
            "matchRate": float(r[6]),
            "runAt": r[7].isoformat(),
        }
        for r in rows
    ]


def period_label(period: str) -> str:
    try:
        dt = datetime.strptime(period, "%Y-%m")
        return dt.strftime("%B %Y")
    except Exception:
        return period


def list_periods():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # All available period months in the system
            cur.execute("SELECT DISTINCT period FROM gateway_records ORDER BY period ASC")
            all_periods = [r[0] for r in cur.fetchall()]

            # Periods that have actually completed a reconciliation run
            cur.execute("SELECT DISTINCT period FROM reconciliation_runs")
            done_periods = {r[0] for r in cur.fetchall()}
    finally:
        conn.close()

    return [
        {
            "period": p,
            "label": period_label(p),
            "status": "done" if p in done_periods else "not_run",
        }
        for p in all_periods
    ]

def get_monthly_risk_trends(conn):
    with conn.cursor() as cur:
        # Aggregate unique exceptions per period to avoid inflating risk
        cur.execute(
            """
            SELECT 
                p.period,
                COALESCE(SUM(sub.amount), 0.0) AS amount_at_risk,
                COUNT(sub.payment_id) AS exception_count
            FROM (SELECT DISTINCT period FROM gateway_records) p
            LEFT JOIN (
                SELECT DISTINCT ON (period, payment_id) period, payment_id, amount
                FROM exceptions
            ) sub ON p.period = sub.period
            GROUP BY p.period
            ORDER BY p.period ASC
            """
        )
        rows = cur.fetchall()

    return [
        {
            "period": r[0],
            "label": datetime.strptime(r[0], "%Y-%m").strftime("%b %Y"),
            "amountAtRisk": float(r[1]),
            "exceptionCount": int(r[2]),
        }
        for r in rows
    ]
    
def _fetch_summary_rows(conn, period: str):
    with conn.cursor() as cur:
        # Check if an actual run exists for this period
        cur.execute(
            """SELECT total_records, matched_count, exception_count, match_rate 
               FROM reconciliation_runs 
               WHERE period = %s 
               ORDER BY run_at DESC LIMIT 1""",
            (period,),
        )
        run_record = cur.fetchone()

        cur.execute("SELECT COUNT(*) FROM gateway_records WHERE period = %s", (period,))
        total_records = cur.fetchone()[0]

        cur.execute(
            """SELECT match_type, COUNT(*) FROM ledger_matches
               WHERE period = %s GROUP BY match_type""",
            (period,),
        )
        breakdown_rows = cur.fetchall()

        # Deduplicate exceptions by payment_id so repeat flags don't push the rate to 100%
        cur.execute(
    """SELECT DISTINCT ON (payment_id) payment_id, reason_code, amount, risk, recommended_action 
       FROM exceptions
       WHERE period = %s 
       ORDER BY payment_id, amount DESC NULLS LAST""",
    (period,),
    )
        exception_rows = cur.fetchall()

        cur.execute(
    """SELECT explanation, bank_amount, payment_id, matched_amount
       FROM ledger_matches
       WHERE period = %s AND match_type = 'lump_sum'
       ORDER BY explanation""",
    (period,),
)
        lump_sum_rows = cur.fetchall()

    return run_record, total_records, breakdown_rows, exception_rows, lump_sum_rows


def _build_breakdown(breakdown_rows):
    breakdown = {"exact": 0, "fuzzy": 0, "lump_sum": 0, "fee_aware": 0}
    for match_type, count in breakdown_rows:
        if match_type in breakdown:
            breakdown[match_type] = count
    return breakdown


def _build_exceptions(exception_rows):
    return [
        {
            "paymentId": row[0],
            "reasonCode": row[1],
            "reasonLabel": REASON_LABELS.get(row[1], row[1].replace("_", " ").title()),
            "amount": float(row[2]) if row[2] is not None else 0.0,
            "risk": row[3],
            "recommendedAction": row[4],
        }
        for row in exception_rows
    ]


def _lump_sum_group_key(payment_id: str) -> str | None:
    m = re.search(r"_ls(\d+)_", payment_id)
    return m.group(1) if m else None

def _build_lump_sum_highlights(lump_sum_rows, exceptions):
    groups: dict[str, dict] = {}
    for explanation, bank_amount, payment_id, matched_amount in lump_sum_rows:
        key = explanation
        g = groups.setdefault(key, {
            "utr": explanation.split("UTR ")[-1] if "UTR " in explanation else "",
            "bankAmount": float(bank_amount),
            "memberPaymentIds": [],
            "memberAmounts": [],
            "heldBackPaymentIds": [],
            "_group_key": _lump_sum_group_key(payment_id),
        })
        g["memberPaymentIds"].append(payment_id)
        g["memberAmounts"].append(float(matched_amount))

    held_back_exceptions = [e for e in exceptions if e["reasonCode"] == "held_back_from_lump_sum"]
    for g in groups.values():
        group_key = g["_group_key"]
        g["heldBackPaymentIds"] = [
            e["paymentId"] for e in held_back_exceptions
            if group_key and _lump_sum_group_key(e["paymentId"]) == group_key
        ]
        del g["_group_key"]  # internal only, don't leak to the API response

    return list(groups.values())


def build_summary(conn, period: str):
    """Assembles the full ReconciliationSummary shape expected by the dashboard.
    Returns status='not_run' if no run has occurred for this month."""
    run_record, total_records, breakdown_rows, exception_rows, lump_sum_rows = _fetch_summary_rows(conn, period)

    if total_records == 0:
        return None

    # Month exists, but reconciliation hasn't been run yet
    if not run_record and not breakdown_rows and not exception_rows:
        return {
            "period": period,
            "status": "not_run",
            "totalRecords": total_records,
            "matchRate": 0.0,
            "exceptionRate": 0.0,
            "amountAtRisk": 0.0,
            "breakdown": {"exact": 0, "fuzzy": 0, "lump_sum": 0, "fee_aware": 0},
            "exceptions": [],
            "highlights": [],
        }

    breakdown = _build_breakdown(breakdown_rows)
    exceptions = _build_exceptions(exception_rows)
    highlights = _build_lump_sum_highlights(lump_sum_rows, exceptions)

    n_matched = sum(breakdown.values())
    n_exceptions = len(exceptions)
    amount_at_risk = sum(e["amount"] for e in exceptions)

    match_rate = round((n_matched / total_records) * 100, 1) if total_records else 0.0
    exception_rate = round((n_exceptions / total_records) * 100, 1) if total_records else 0.0

    return {
        "period": period,
        "status": "done",
        "totalRecords": total_records,
        "matchRate": match_rate,
        "exceptionRate": min(exception_rate, 100.0),
        "amountAtRisk": round(amount_at_risk, 2),
        "breakdown": breakdown,
        "exceptions": exceptions,
        "highlights": highlights,
    }
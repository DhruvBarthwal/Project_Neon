from datetime import datetime

from reconciler.main import get_connection

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
    dt = datetime.strptime(period, "%Y-%m")
    return dt.strftime("%B %Y")


def list_periods():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT period FROM gateway_records ORDER BY period")
            all_periods = [r[0] for r in cur.fetchall()]

            cur.execute(
                "SELECT DISTINCT period FROM ledger_matches "
                "UNION SELECT DISTINCT period FROM exceptions"
            )
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


def _fetch_summary_rows(conn, period: str):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM gateway_records WHERE period = %s", (period,))
        total_records = cur.fetchone()[0]

        cur.execute(
            """SELECT match_type, COUNT(*) FROM ledger_matches
               WHERE period = %s GROUP BY match_type""",
            (period,),
        )
        breakdown_rows = cur.fetchall()

        cur.execute(
            """SELECT payment_id, reason_code, amount, risk FROM exceptions
               WHERE period = %s ORDER BY amount DESC NULLS LAST""",
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

    return total_records, breakdown_rows, exception_rows, lump_sum_rows


def _build_breakdown(breakdown_rows):
    breakdown = {"exact": 0, "fuzzy": 0, "lump_sum": 0, "fee_aware": 0}
    for match_type, count in breakdown_rows:
        breakdown[match_type] = count
    return breakdown


def _build_exceptions(exception_rows):
    return [
        {
            "paymentId": row[0],
            "reasonCode": row[1],
            "reasonLabel": REASON_LABELS.get(row[1], row[1]),
            "amount": float(row[2]) if row[2] is not None else 0,
            "risk": row[3],
        }
        for row in exception_rows
    ]


def _build_lump_sum_highlights(lump_sum_rows, exceptions):
    groups: dict[str, dict] = {}
    for explanation, bank_amount, payment_id, matched_amount in lump_sum_rows:
        key = explanation  # shared explanation string per group is a good-enough key
        g = groups.setdefault(key, {
            "utr": explanation.split("UTR ")[-1] if "UTR " in explanation else "",
            "bankAmount": float(bank_amount),
            "memberPaymentIds": [],
            "memberAmounts": [],
            "heldBackPaymentIds": [],
        })
        g["memberPaymentIds"].append(payment_id)
        g["memberAmounts"].append(float(matched_amount))

    held_back_ids = [e["paymentId"] for e in exceptions if e["reasonCode"] == "held_back_from_lump_sum"]
    for g in groups.values():
        g["heldBackPaymentIds"] = held_back_ids

    return list(groups.values())


def build_summary(conn, period: str):
    """Assembles the full ReconciliationSummary shape the dashboard expects,
    purely from what's already sitting in ledger_matches / exceptions, 
    this never re-runs matching, it just reads and shapes results."""
    total_records, breakdown_rows, exception_rows, lump_sum_rows = _fetch_summary_rows(conn, period)
    if total_records == 0:
        return None

    breakdown = _build_breakdown(breakdown_rows)
    exceptions = _build_exceptions(exception_rows)
    highlights = _build_lump_sum_highlights(lump_sum_rows, exceptions)

    n_matched = sum(breakdown.values())
    amount_at_risk = sum(e["amount"] for e in exceptions)

    return {
        "period": period,
        "status": "done",
        "totalRecords": total_records,
        "matchRate": round(n_matched / total_records * 100, 1),
        "exceptionRate": round(len(exceptions) / total_records * 100, 1),
        "amountAtRisk": round(amount_at_risk, 2),
        "breakdown": breakdown,
        "exceptions": exceptions,
        "highlights": highlights,
    }
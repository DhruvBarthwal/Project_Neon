from datetime import datetime
from langchain_core.messages import AIMessage
import psycopg2.extras

from reconciler.main import (
    fetch_merchant_records,
    fetch_period,
    get_connection,
    write_results,
)
from reconciler.matcher import run_matching
from reconciler.merchant_crosscheck import cross_check_merchant
from reconciler.summary_service import REASON_LABELS
from reconciler.audit_service import record_business_audit

from .llm import chat, classify
from .prompts import (
    multi_record_audit_prompt,
    metric_query_prompt,
    batch_audit_prompt,
    period_audit_report_prompt,
    period_comparison_prompt,
    MAX_PAYMENT_IDS_PER_QUESTION,
)
from .states import AgentState


# ---------- Helpers & Reconciliation Checks ----------

def _period_has_data(conn, period: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM gateway_records WHERE period = %s LIMIT 1", (period,))
        return cur.fetchone() is not None


def _period_already_reconciled(conn, period: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM ledger_matches WHERE period = %s "
            "UNION SELECT 1 FROM exceptions WHERE period = %s LIMIT 1",
            (period, period),
        )
        return cur.fetchone() is not None


def _format_inr(val) -> str:
    if val is None:
        return "—"
    return f"₹{float(val):,.2f}"


def ensure_reconciled_node(state: AgentState) -> dict:
    conn = get_connection()
    try:
        period = state["period"]
        if not _period_has_data(conn, period):
            return {"auto_run_notice": f"NO_DATA:No reconciliation data exists for {period}."}
        if _period_already_reconciled(conn, period):
            return {"auto_run_notice": None}

        gateway_rows, bank_rows = fetch_period(conn, period)
        matches, exceptions = run_matching(gateway_rows, bank_rows)

        matched_payment_ids = {m["payment_id"] for m in matches}
        merchant_rows = fetch_merchant_records(conn, period)
        exceptions = cross_check_merchant(
            gateway_rows, merchant_rows, matched_payment_ids, exceptions
        )

        write_results(
            conn, period, matches, exceptions, triggered_by="audit_agent", trigger_source="auto_agent"
        )
        return {"auto_run_notice": f"(Reconciliation cycle was pending for {period} — executed automatically.)\n\n"}
    finally:
        conn.close()


def no_data_response_node(state: AgentState) -> dict:
    message = state["auto_run_notice"].removeprefix("NO_DATA:")
    return {"answer": message, "messages": [AIMessage(content=message)]}


def classify_intent_node(state: AgentState) -> dict:
    parsed = classify(state["messages"])
    print(">>> CLASSIFY DEBUG:", parsed)
    update = {
        "intent": parsed.get("intent", "not_found"),
        "payment_ids": parsed.get("payment_ids") or [],
        "utrs": parsed.get("utrs") or [],
        "min_amount": parsed.get("min_amount"),
        "compare_period": parsed.get("compare_period"),
        "target_table": parsed.get("target_table") or "exceptions",
    }
    if parsed.get("period"):
        update["period"] = parsed["period"]
    return update


# ---------- Record Audit with Idempotency & Retry Normalization ----------

def _fetch_records_bundle(identifiers: list[str], fallback_period: str) -> list[dict]:
    import re
    conn = get_connection()
    records = []
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for ident in identifiers:
                target_period = fallback_period
                m = re.search(r"pay_(\d{4})(\d{2})_", ident)
                if m:
                    target_period = f"{m.group(1)}-{m.group(2)}"

                # Gateway Lookup
                cur.execute(
                    """SELECT payment_id, order_id, amount, status, utr, created_at, scenario, period
                       FROM gateway_records 
                       WHERE payment_id = %s OR utr = %s LIMIT 1""",
                    (ident, ident),
                )
                gw = cur.fetchone()
                if gw:
                    target_period = gw["period"]

                pid = gw["payment_id"] if gw else ident
                utr = gw["utr"] if gw and gw.get("utr") else ident
                order_id = gw["order_id"] if gw else None
                base_pid = pid.replace("_retry", "")

                # Bank Lookup
                cur.execute(
                    """SELECT id, utr, amount, credited_at, narration, linked_payment_ids
                       FROM bank_records 
                       WHERE (UPPER(utr) = UPPER(%s) OR linked_payment_ids LIKE %s OR linked_payment_ids LIKE %s)
                         AND period = %s LIMIT 1""",
                    (utr, f"%{pid}%", f"%{base_pid}%", target_period),
                )
                bank = cur.fetchone()

                # Merchant Lookup
                cur.execute(
                    """SELECT order_id, payment_id, amount, status, marked_paid_at, scenario
                       FROM merchant_records 
                       WHERE (order_id = %s OR payment_id = %s OR payment_id = %s)
                         AND period = %s LIMIT 1""",
                    (order_id, pid, base_pid, target_period),
                )
                merch = cur.fetchone()

                # Matches
                cur.execute(
                    """SELECT match_type, matched_amount, bank_amount, explanation 
                       FROM ledger_matches 
                       WHERE (payment_id = %s OR payment_id = %s) AND period = %s LIMIT 1""",
                    (pid, base_pid, target_period),
                )
                matched = cur.fetchone()

                # Exceptions
                cur.execute(
                    """SELECT reason_code, reason_detail, recommended_action, amount, risk
                       FROM exceptions 
                       WHERE (payment_id = %s OR payment_id = %s) AND period = %s LIMIT 1""",
                    (pid, base_pid, target_period),
                )
                exception = cur.fetchone()

                records.append({
                    "identifier": ident,
                    "period": target_period,
                    "gateway": dict(gw) if gw else None,
                    "bank": dict(bank) if bank else None,
                    "merchant": dict(merch) if merch else None,
                    "match": dict(matched) if matched else None,
                    "exception": dict(exception) if exception else None,
                    "is_retry": "_retry" in pid,
                    "order_paid": merch["status"] == "paid" if merch else False,
                })
        return records
    finally:
        conn.close()


def lookup_record_node(state: AgentState) -> dict:
    identifiers = state.get("payment_ids") or []
    if not identifiers and state.get("utrs"):
        identifiers = state.get("utrs")

    if not identifiers:
        ans = "Please specify a Payment ID (e.g., `pay_202605_00032`) or a Bank UTR to audit."
        return {"answer": ans, "messages": [AIMessage(content=ans)]}

    records = _fetch_records_bundle(identifiers[:MAX_PAYMENT_IDS_PER_QUESTION], state["period"])
    
    for r in records:
        gw = r.get("gateway")
        merch = r.get("merchant")
        bank = r.get("bank")
        exc = r.get("exception")

        # Handle record not found
        if not gw and not merch and not bank:
            outcome = "RECORD_NOT_FOUND"
            risk_amt = 0.00
        elif r.get("is_retry") and r.get("order_paid"):
            outcome = "BENIGN_RETRY"
            risk_amt = 0.00
        elif exc:
            outcome = "EXCEPTION_FLAGGED"
            risk_amt = float(exc.get("amount") or 0.00)
        else:
            outcome = "CLEAN_MATCH"
            risk_amt = 0.00

        record_business_audit(
            period=r.get("period") or state.get("period") or "2026-05",
            event_type="RECORD_AUDIT",
            intent="lookup_record",
            target_identifier=r.get("identifier") or "UNKNOWN",
            outcome_status=outcome,
            exposure_amount=risk_amt,
            actor="analyst_copilot",
            metadata={
                "gateway_status": gw.get("status") if gw else None,
                "merchant_status": merch.get("status") if merch else None,
                "bank_utr": bank.get("utr") if bank else None,
                "is_retry": r.get("is_retry", False),
            },
        )

    prompt = multi_record_audit_prompt(records)
    answer = chat(prompt, max_tokens=3500)
    return {"answer": answer, "messages": [AIMessage(content=answer)]}

def match_status_node(state: AgentState) -> dict:
    return lookup_record_node(state)

def metric_query_node(state: AgentState) -> dict:
    period = state["period"]
    user_query = state["messages"][-1].content
    conn = get_connection()
    try:
        stats = _fetch_month_stats(conn, period)
    finally:
        conn.close()

    record_business_audit(
        period=period,
        event_type="METRIC_INSPECTION",
        intent="metric_query",
        target_identifier=f"Metrics: {period}",
        outcome_status="INSPECTED",
        exposure_amount=float(stats.get("at_risk") or 0.00),
        actor="analyst_copilot",
        metadata={"match_rate": stats.get("match_rate"), "exceptions": stats.get("exceptions")},
    )

    prompt = metric_query_prompt(period, stats, user_query)
    answer = chat(prompt, max_tokens=1024)
    return {"answer": answer, "messages": [AIMessage(content=answer)]}

# ---------- Table Navigation (Deep Link Injection) ----------

def table_navigation_node(state: AgentState) -> dict:
    period = state["period"]
    table = state.get("target_table") or "exceptions"

    record_business_audit(
        period=period,
        event_type="WORKSPACE_NAVIGATION",
        intent="table_navigation",
        target_identifier=f"Table: {table}",
        outcome_status="NAVIGATED",
        exposure_amount=0.00,
        actor="analyst_copilot",
        metadata={"target_table": table},
    )

    table_labels = {
        "exceptions": "Exceptions Queue",
        "ledger_matches": "Reconciled Ledger Matches",
        "gateway": "Gateway Records",
        "bank": "Bank Settlements",
        "merchant": "Merchant Orders",
    }
    label = table_labels.get(table, "Ledger Table")

    answer = (
        f"Displaying the full dataset inline for **{period}** would flood the audit log. "
        f"You can explore all filtered entries directly in the ledger workspace:\n\n"
        f"[Open {label} ({period}) →](#view_tables?period={period}&table={table})\n\n"
        f"*Use the in-table search and period selector to inspect specific records.*"
    )
    return {"answer": answer, "messages": [AIMessage(content=answer)]}

# ---------- Batch / Lump-Sum Unbundling Audit ----------

def batch_unbundling_audit_node(state: AgentState) -> dict:
    utrs = state.get("utrs") or []
    period = state["period"]

    if not utrs:
        ans = "Please provide the bank deposit UTR to audit batch settlement unbundling."
        return {"answer": ans, "messages": [AIMessage(content=ans)]}

    target_utr = utrs[0]
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM bank_records WHERE UPPER(utr) = UPPER(%s) AND period = %s LIMIT 1",
                (target_utr, period),
            )
            bank_row = cur.fetchone()

            cur.execute(
                """SELECT * FROM ledger_matches 
                   WHERE period = %s AND match_type = 'lump_sum' AND explanation LIKE %s""",
                (period, f"%{target_utr}%"),
            )
            member_matches = [dict(r) for r in cur.fetchall()]

            cur.execute(
                """SELECT * FROM exceptions 
                   WHERE period = %s AND reason_code IN ('held_back_from_lump_sum', 'ambiguous_lump_sum_match', 'lump_sum_too_complex')""",
                (period,),
            )
            held_back = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    if not bank_row:
        ans = f"No bank settlement credit found for UTR `{target_utr}` in `{period}`."
        return {"answer": ans, "messages": [AIMessage(content=ans)]}

    prompt = batch_audit_prompt(target_utr, dict(bank_row), member_matches, held_back)
    answer = chat(prompt, max_tokens=1024)
    return {"answer": answer, "messages": [AIMessage(content=answer)]}


# ---------- On-Demand Reconcile Cycle ----------

def reconcile_cycle_node(state: AgentState) -> dict:
    period = state["period"]
    conn = get_connection()
    try:
        gateway_rows, bank_rows = fetch_period(conn, period)
        if not gateway_rows:
            ans = f"Cannot reconcile `{period}`: zero gateway ingestion records present."
            return {"answer": ans, "messages": [AIMessage(content=ans)]}

        matches, exceptions = run_matching(gateway_rows, bank_rows)
        matched_payment_ids = {m["payment_id"] for m in matches}
        merchant_rows = fetch_merchant_records(conn, period)
        exceptions = cross_check_merchant(
            gateway_rows, merchant_rows, matched_payment_ids, exceptions
        )

        write_results(
            conn, period, matches, exceptions, triggered_by="manual_agent", trigger_source="user_prompt"
        )
        ans = (
            f"Successfully completed 3-way reconciliation cycle for **{period}**.\n\n"
            f"- **Matches Resolved**: {len(matches)}\n"
            f"- **Exceptions Flagged**: {len(exceptions)}\n\n"
            f"[View Reconciled Ledger ({period}) →](#view_tables?period={period}&table=ledger_matches)"
        )
        return {"answer": ans, "messages": [AIMessage(content=ans)]}
    finally:
        conn.close()


# ---------- Period Summary & Comparison ----------

def _fetch_month_stats(conn, period: str) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM gateway_records WHERE period = %s", (period,))
        total = cur.fetchone()[0] or 0

        cur.execute(
            """SELECT match_type, COUNT(*) FROM ledger_matches 
               WHERE period = %s GROUP BY match_type""",
            (period,),
        )
        breakdown = {r[0]: r[1] for r in cur.fetchall()}
        matched = sum(breakdown.values())

        cur.execute(
            """SELECT COUNT(DISTINCT payment_id), COALESCE(SUM(amount), 0)
               FROM exceptions WHERE period = %s""",
            (period,),
        )
        exc_count, at_risk = cur.fetchone()

        cur.execute(
            """SELECT reason_code, COUNT(*), COALESCE(SUM(amount), 0)
               FROM exceptions WHERE period = %s GROUP BY reason_code ORDER BY count DESC""",
            (period,),
        )
        reasons = cur.fetchall()

    match_rate = round((matched / total) * 100, 1) if total else 0.0
    exception_rate = round((exc_count / total) * 100, 1) if total else 0.0

    return {
        "period": period,
        "total": total,
        "matched": matched,
        "match_rate": match_rate,
        "exceptions": exc_count,
        "exception_rate": exception_rate,
        "at_risk": float(at_risk),
        "breakdown": breakdown,
        "reasons": reasons,
    }


def _fetch_all_periods_summary(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT period FROM gateway_records ORDER BY period ASC")
        periods = [r[0] for r in cur.fetchall()]
    return [_fetch_month_stats(conn, p) for p in periods]


def summary_node(state: AgentState) -> dict:
    period = state["period"]
    conn = get_connection()
    try:
        target_stats = _fetch_month_stats(conn, period)
        if target_stats["total"] == 0:
            ans = f"No reconciliation data exists for period `{period}`."
            return {"answer": ans, "messages": [AIMessage(content=ans)]}

        all_history = _fetch_all_periods_summary(conn)
    finally:
        conn.close()

    prompt = period_audit_report_prompt(period, target_stats, all_history)
    answer = chat(prompt, max_tokens=2048)
    return {"answer": answer, "messages": [AIMessage(content=answer)]}


def compare_months_node(state: AgentState) -> dict:
    p1 = state["period"]
    p2 = state.get("compare_period")

    if not p2 or p1 == p2:
        ans = "Please specify two distinct periods to compare (e.g., `Compare 2026-04 with 2026-05`)."
        return {"answer": ans, "messages": [AIMessage(content=ans)]}

    conn = get_connection()
    try:
        s1 = _fetch_month_stats(conn, p1)
        s2 = _fetch_month_stats(conn, p2)
        all_history = _fetch_all_periods_summary(conn)
    finally:
        conn.close()

    if s1["total"] == 0 or s2["total"] == 0:
        missing = p1 if s1["total"] == 0 else p2
        ans = f"Cannot compare: missing records for period `{missing}`."
        return {"answer": ans, "messages": [AIMessage(content=ans)]}

    deltas = {
        "record_diff": s2["total"] - s1["total"],
        "match_rate_delta": round(s2["match_rate"] - s1["match_rate"], 1),
        "exception_rate_delta": round(s2["exception_rate"] - s1["exception_rate"], 1),
        "risk_delta": round(s2["at_risk"] - s1["at_risk"], 2),
        "exception_count_delta": s2["exceptions"] - s1["exceptions"],
    }

    prompt = period_comparison_prompt(p1, p2, s1, s2, deltas, all_history)
    answer = chat(prompt, max_tokens=2048)
    return {"answer": answer, "messages": [AIMessage(content=answer)]}


def filtered_list_node(state: AgentState) -> dict:
    period = state["period"]
    min_amount = state.get("min_amount")

    query = "SELECT payment_id, reason_code, amount, risk FROM exceptions WHERE period = %s"
    params = [period]
    if min_amount is not None:
        query += " AND amount >= %s"
        params.append(min_amount)
    query += " ORDER BY amount DESC LIMIT 10"

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        answer = f"No exceptions matching threshold >= {_format_inr(min_amount)} in `{period}`."
    else:
        table_rows = "\n".join(
            f"| `{r[0]}` | {REASON_LABELS.get(r[1], r[1])} | {_format_inr(r[2])} | **{r[3].upper()}** |"
            for r in rows
        )
        answer = f"""### Filtered Exceptions List ({period})

| Payment ID | Failure Reason | Amount | Risk Tier |
| :--- | :--- | :--- | :--- |
{table_rows}

[Explore Full Exceptions Table →](#view_tables?period={period}&table=exceptions)"""

    return {"answer": answer, "messages": [AIMessage(content=answer)]}


def grouped_reasons_node(state: AgentState) -> dict:
    period = state["period"]
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT reason_code, COUNT(*), COALESCE(SUM(amount), 0)
                   FROM exceptions WHERE period = %s 
                   GROUP BY reason_code ORDER BY COUNT(*) DESC""",
                (period,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        answer = f"Zero exceptions recorded for `{period}` — all transactions reconciled."
    else:
        table_rows = "\n".join(
            f"| {REASON_LABELS.get(r[0], r[0])} | {r[1]} | {_format_inr(r[2])} |" for r in rows
        )
        answer = f"""### Categorized Exception Breakdown ({period})

| Reason Code / Description | Count | Total Balance at Risk |
| :--- | :--- | :--- |
{table_rows}"""

    return {"answer": answer, "messages": [AIMessage(content=answer)]}


def not_found_node(state: AgentState) -> dict:
    answer = (
        "I could not correlate your inquiry with a verified reconciliation record. You can:\n\n"
        "- **Audit a Transaction**: `Why didn't pay_202605_00032 settle?`\n"
        "- **Inspect a Batch UTR**: `Audit lump-sum unbundling for UTRSQ6CHAHW`\n"
        "- **Review Month Performance**: `Generate executive report for 2026-05`\n"
        "- **Compare Accounting Cycles**: `Compare 2026-04 with 2026-05`\n"
        "- **Access Ledger Tables**: `Show me the exceptions table for May`"
    )
    return {"answer": answer, "messages": [AIMessage(content=answer)]}
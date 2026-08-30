"""
Every node here takes QAState and returns a partial state update.
Nodes that produce a final answer also append it as an AIMessage to
`messages` — that's what makes it visible to classify_intent_node on
the NEXT turn (memory), since the checkpointer persists `messages`
across calls with the same thread_id.
"""

from concurrent.futures import ThreadPoolExecutor

from langchain_core.messages import AIMessage

from reconciler.main import fetch_period, write_results, get_connection
from reconciler.matcher import run_matching
from reconciler.summary_service import REASON_LABELS

from .llm import chat, classify
from .prompts import reason_detail_prompt
from .states import AgentState

MAX_PARALLEL_WORKERS = 5


# ---------- ensure_reconciled ----------

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


def ensure_reconciled_node(state: AgentState) -> dict:
    conn = get_connection()
    try:
        period = state["period"]
        if not _period_has_data(conn, period):
            return {"auto_run_notice": f"NO_DATA:No reconciliation data exists for {period} at all."}

        if _period_already_reconciled(conn, period):
            return {"auto_run_notice": None}

        gateway_rows, bank_rows = fetch_period(conn, period)
        matches, exceptions = run_matching(gateway_rows, bank_rows)
        write_results(conn, period, matches, exceptions)
        return {"auto_run_notice": f"(No reconciliation had been run yet for {period} — ran it now.) "}
    finally:
        conn.close()


def no_data_response_node(state: AgentState) -> dict:
    message = state["auto_run_notice"].removeprefix("NO_DATA:")
    return {"answer": message, "messages": [AIMessage(content=message)]}


# ---------- classify_intent ----------

def classify_intent_node(state: AgentState) -> dict:
    parsed = classify(state["messages"])

    update = {
        "intent": parsed.get("intent", "not_found"),
        "payment_ids": parsed.get("payment_ids") or [],
        "min_amount": parsed.get("min_amount"),
    }
    if parsed.get("period"):
        update["period"] = parsed["period"]  # explicit period in the question overrides the active one
    return update


# ---------- shared helper for the two record-level intents ----------

def _generate_reason_detail(cur, payment_id, period, reason_code, amount):
    detail = chat(reason_detail_prompt(reason_code, amount), max_tokens=150)
    cur.execute(
        "UPDATE exceptions SET reason_detail = %s WHERE payment_id = %s AND period = %s",
        (detail, payment_id, period),
    )
    return detail


def _lookup_record(period: str, payment_id: str) -> str:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT match_type, explanation FROM ledger_matches
                   WHERE payment_id = %s AND period = %s""",
                (payment_id, period),
            )
            match_row = cur.fetchone()
            if match_row:
                match_type, explanation = match_row
                return f"{payment_id} settled successfully ({match_type} match). {explanation}"

            cur.execute(
                """SELECT reason_code, reason_detail, recommended_action, amount
                   FROM exceptions WHERE payment_id = %s AND period = %s""",
                (payment_id, period),
            )
            exc_row = cur.fetchone()
            if not exc_row:
                return f"I couldn't find {payment_id} in this period's reconciliation data at all."

            reason_code, reason_detail, action, amount = exc_row
            if reason_detail is None:
                reason_detail = _generate_reason_detail(cur, payment_id, period, reason_code, amount)
                conn.commit()

            return f"{payment_id} didn't settle. {reason_detail} Recommended: {action}"
    finally:
        conn.close()


def _lookup_many(period: str, payment_ids: list[str]) -> str:
    """Runs lookups concurrently, capped at MAX_PARALLEL_WORKERS ,each
    lookup is its own DB connection + possibly one lazy LLM call, so
    this bounds how many of those run in flight at once."""
    if not payment_ids:
        return "I need at least one payment ID to look that up."

    if len(payment_ids) == 1:
        return _lookup_record(period, payment_ids[0])

    with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_WORKERS, len(payment_ids))) as pool:
        results = list(pool.map(lambda pid: (pid, _lookup_record(period, pid)), payment_ids))

    return "\n".join(f"- {text}" for _, text in results)


# ---------- one node per intent ----------

def lookup_record_node(state: AgentState) -> dict:
    answer = _lookup_many(state["period"], state.get("payment_ids") or [])
    return {"answer": answer, "messages": [AIMessage(content=answer)]}


def match_status_node(state: AgentState) -> dict:
    answer = _lookup_many(state["period"], state.get("payment_ids") or [])
    return {"answer": answer, "messages": [AIMessage(content=answer)]}


def summary_node(state: AgentState) -> dict:
    period = state["period"]
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM gateway_records WHERE period = %s", (period,))
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM ledger_matches WHERE period = %s", (period,))
            matched = cur.fetchone()[0]
            cur.execute("SELECT COALESCE(SUM(amount),0) FROM exceptions WHERE period = %s", (period,))
            at_risk = cur.fetchone()[0]
    finally:
        conn.close()

    if total == 0:
        answer = f"No reconciliation data exists for {period} yet."
    else:
        match_rate = round(matched / total * 100, 1)
        exceptions = total - matched
        answer = (
            f"For {period}: {match_rate}% auto-match rate ({matched}/{total}). "
            f"{exceptions} exceptions, ₹{at_risk} at risk."
        )
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
        filter_desc = f" over ₹{min_amount}" if min_amount else ""
        answer = f"No exceptions{filter_desc} found for {period}."
    else:
        lines = [
            f"- {pid}: {REASON_LABELS.get(reason, reason)}, ₹{amount} ({risk} risk)"
            for pid, reason, amount, risk in rows
        ]
        answer = f"Found {len(rows)} exception(s) for {period}:\n" + "\n".join(lines)

    return {"answer": answer, "messages": [AIMessage(content=answer)]}


def grouped_reasons_node(state: AgentState) -> dict:
    period = state["period"]
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT reason_code, COUNT(*) FROM exceptions
                   WHERE period = %s GROUP BY reason_code ORDER BY COUNT(*) DESC""",
                (period,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        answer = f"No exceptions to group for {period} — everything reconciled."
    else:
        lines = [f"- {REASON_LABELS.get(code, code)}: {count}" for code, count in rows]
        answer = f"Exception breakdown for {period}:\n" + "\n".join(lines)

    return {"answer": answer, "messages": [AIMessage(content=answer)]}


def not_found_node(state: AgentState) -> dict:
    payment_ids = state.get("payment_ids") or []
    if payment_ids:
        answer = f"I couldn't find any record of {', '.join(payment_ids)} in this period's data."
    else:
        answer = "I can only answer questions about this period's reconciliation results — could you rephrase?"
    return {"answer": answer, "messages": [AIMessage(content=answer)]}
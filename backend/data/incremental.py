from datetime import datetime, timezone
 
from reconciler.main import (
    fetch_period,
    fetch_incremental_period,
    fetch_already_matched_ids,
    fetch_merchant_records,
    get_last_run_at,
    write_results,
)
from reconciler.matcher import run_matching
from reconciler.merchant_crosscheck import cross_check_merchant
 
 
def _dedupe(exceptions):
    seen = set()
    out = []
    for e in exceptions:
        if e["payment_id"] in seen:
            continue
        seen.add(e["payment_id"])
        out.append(e)
    return out
 
 
def incremental_reconcile(conn, period: str, triggered_by=None, trigger_source="auto_periodic"):
    """Returns (ran: bool, matches_count, exceptions_count). ran=False means
    there was nothing new to do — caller can skip logging/UI refresh."""
    last_run_at = get_last_run_at(conn, period)
 
    if last_run_at is None:
        # Never run before — an incremental pass has nothing to diff against,
        # so do a full reconcile instead.
        gateway_rows, bank_rows = fetch_period(conn, period)
        if not gateway_rows:
            return False, 0, 0
        already_matched = set()
    else:
        gateway_rows, bank_rows = fetch_incremental_period(conn, period, last_run_at)
        if not gateway_rows:
            return False, 0, 0  # nothing new, no open exceptions — skip this cycle
        already_matched = fetch_already_matched_ids(conn, period)
 
    matches, exceptions = run_matching(gateway_rows, bank_rows, already_matched_payment_ids=already_matched)
 
    matched_payment_ids = {m["payment_id"] for m in matches} | already_matched
    merchant_rows = fetch_merchant_records(conn, period)
    exceptions = cross_check_merchant(gateway_rows, merchant_rows, matched_payment_ids, exceptions)
    exceptions = _dedupe(exceptions)
 
    write_results(conn, period, matches, exceptions, triggered_by=triggered_by, trigger_source=trigger_source)
    return True, len(matches), len(exceptions)
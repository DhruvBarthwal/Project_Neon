import asyncio
import logging
 
from reconciler.main import get_connection
from data.incremental import incremental_reconcile
from data.generator import trickle_once  # see note below
 
logger = logging.getLogger("scheduler")
 
RECONCILE_INTERVAL_SECONDS = 10
INSERT_INTERVAL_SECONDS = 30
ACTIVE_PERIODS = ["2026-06"]  # periods the scheduler should watch; adjust as needed
 
 
from reconciler.main import fetch_period, fetch_merchant_records, write_results
from reconciler.matcher import run_matching
from reconciler.merchant_crosscheck import cross_check_merchant

async def _reconcile_loop():
    while True:
        await asyncio.sleep(7200)  # slower interval, full runs are heavier
        for period in ACTIVE_PERIODS:
            try:
                conn = await asyncio.to_thread(get_connection)
                try:
                    def full_run():
                        gateway_rows, bank_rows = fetch_period(conn, period)
                        matches, exceptions = run_matching(gateway_rows, bank_rows)
                        matched_ids = {m["payment_id"] for m in matches}
                        merchant_rows = fetch_merchant_records(conn, period)
                        excs = cross_check_merchant(gateway_rows, merchant_rows, matched_ids, exceptions)
                        seen, deduped = set(), []
                        for e in excs:
                            if e["payment_id"] in seen: continue
                            seen.add(e["payment_id"]); deduped.append(e)
                        write_results(conn, period, matches, deduped, triggered_by="scheduler", trigger_source="auto_periodic")
                    await asyncio.to_thread(full_run)
                finally:
                    conn.close()
            except Exception:
                logger.exception("[auto-reconcile] failed for %s", period)
 
 
async def _insert_loop():
    while True:
        await asyncio.sleep(INSERT_INTERVAL_SECONDS)
        for period in ACTIVE_PERIODS:
            try:
                conn = await asyncio.to_thread(get_connection)
                try:
                    inserted = await asyncio.to_thread(trickle_once, conn, period)
                    logger.info("[auto-insert] %s: +%d row(s)", period, inserted)
                finally:
                    conn.close()
            except Exception:
                logger.exception("[auto-insert] failed for period %s", period)
 
 
def start_background_tasks():
    """Call this once from app.py's @app.on_event('startup') handler."""
    asyncio.create_task(_reconcile_loop())
    asyncio.create_task(_insert_loop())
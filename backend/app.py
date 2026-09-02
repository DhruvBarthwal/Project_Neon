#=========== LIBRARIES ===========#

import logging
import os
import nemoguardrails.llm.clients.base as _base
import time
import json
import psycopg2.extras

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.rails.llm.options import GenerationOptions
from dotenv import load_dotenv
from langgraph.types import Command
from datetime import datetime

# from agent.security.agent_identity import issue_agent_identity, verify_agent_identity
from agent.graph import graph

from reconciler.main import get_connection, fetch_period, write_results
from reconciler.matcher import run_matching
from reconciler import summary_service
from agent.graph import ask as qa_ask
from security.security import issue_agent_identity, get_current_agent
from reconciler.merchant_crosscheck import cross_check_merchant
from reconciler.main import fetch_merchant_records

#========= CONNECTION ==========#

app = FastAPI()

load_dotenv()

_orig_init = _base.BaseClient.__init__

logging.basicConfig(level=logging.DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

#=========== NEMO GUARDRAILS ============#

def _patched_init(self, *args, **kwargs):
    kwargs.setdefault("timeout", 90.0)
    kwargs.setdefault("connect_timeout", 15.0)
    _orig_init(self, *args, **kwargs)

_base.BaseClient.__init__ = _patched_init

config = RailsConfig.from_path("guardrails/config")
rails = LLMRails(config)

#=========== CLASSES =============#

class TextRequest(BaseModel):
    text : str
    convo_id: str
    period: str   # added — the Q&A graph needs to know which reconciliation batch to query


class RunReconciliationRequest(BaseModel):
    period: str


class TokenRequest(BaseModel):
    user_id: str
    role: str ="viewer"
    convo_id: str | None = None    
    
#============ ROUTES =============#

@app.get("/")
def home():
    return {"message" : "Backend is running...."}


@app.post("/auth/token")
def get_token(req: TokenRequest):
    token = issue_agent_identity(req.user_id, req.role, req.convo_id)
    return {"token": token}


@app.post("/intent")
async def getIntent(data : TextRequest):

    messages = [{
        "role" : "user",
        "content" : data.text
    }]
    
    t0 = time.time()
    
    # options = GenerationOptions(output_vars=True)
    # response = await rails.generate_async(messages=messages,options=options)
   
    # t1 = time.time()
    
    # print("DEBUG:", response.output_data)
    
    # output_data = response.output_data or {}
    # blocked = (
    #     output_data.get("triggered_input_rail") is not None
    #     or output_data.get("triggered_output_rail") is not None
    # )
       
    # if blocked:
    #     return {
    #             "is_safe": False,
    #             "message" : response.response
    #         }

    # ---- Q&A graph (Track 04) replaces the old graph.ainvoke logic below ----
    # thread_id = convo_id, same pattern as before, keeps memory across turns
    # for this conversation.
    
    answer = qa_ask(data.text, data.period, thread_id=data.convo_id)

    return {"is_safe": True, "status": "done", "response": answer}

    
@app.get("/api/reconciliation/periods")
def get_periods():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT period FROM gateway_records ORDER BY period ASC")
            periods_in_db = [r[0] for r in cur.fetchall()]

            cur.execute("SELECT DISTINCT period FROM reconciliation_runs")
            completed_periods = {r[0] for r in cur.fetchall()}

        if not periods_in_db:
            return []

        result = []
        for p in periods_in_db:
            try:
                dt = datetime.strptime(p, "%Y-%m")
                label = dt.strftime("%B %Y")
            except Exception:
                label = p

            result.append({
                "period": p,
                "label": label,
                "status": "done" if p in completed_periods else "not_run"
            })
        return result
    finally:
        conn.close()
        

@app.get("/api/reconciliation/summary")
def get_summary(period: str):
    conn = get_connection()
    try:
        summary = summary_service.build_summary(conn, period)
    finally:
        conn.close()
    
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No data for period {period}")
    return summary


@app.get("/api/reconciliation/audit")
def get_audit_log(period: str | None = None, agent : dict = Depends(get_current_agent)):
    return summary_service.list_runs(period)


@app.get("/api/reconciliation/trends")
def get_risk_trends():
    conn = get_connection()
    try:
        return summary_service.get_monthly_risk_trends(conn)
    finally:
        conn.close()
        
@app.post("/api/reconciliation/run")
def run_reconciliation(req: RunReconciliationRequest, agent: dict = Depends(get_current_agent)):
    conn = get_connection()
    try:
        gateway_rows, bank_rows = fetch_period(conn, req.period)
        
        if not gateway_rows:
            raise HTTPException(status_code=404, detail=f"No gateway records found for period {req.period}. Generate data first.")
 
        matches, exceptions = run_matching(gateway_rows, bank_rows)
 
        matched_payment_ids = {m["payment_id"] for m in matches}
        merchant_rows = fetch_merchant_records(conn, req.period)
        print("gateway_rows:", len(gateway_rows))
        print("merchant_rows:", len(merchant_rows))
        print("matched_payment_ids:", len(matched_payment_ids))
        print("exceptions before crosscheck:", len(exceptions))

        exceptions = cross_check_merchant(gateway_rows, merchant_rows, matched_payment_ids, exceptions)
        
        seen = set()
        deduped_exceptions = []
        for e in exceptions:
            if e["payment_id"] in seen:
                continue
            seen.add(e["payment_id"])
            deduped_exceptions.append(e)
        exceptions = deduped_exceptions         
        
        print("exceptions after crosscheck:", len(exceptions))
 
        write_results(conn, req.period, matches, exceptions, triggered_by=agent["sub"], trigger_source="manual")
        summary = summary_service.build_summary(conn, req.period)
    
    finally:
        conn.close()
    
    return summary


@app.get("/api/reconciliation/tables")
def get_reconciliation_tables(period: str):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # 1. Reconciled Ledger Matches
            cur.execute(
                """SELECT payment_id, match_type, matched_amount, bank_amount, risk, explanation 
                   FROM ledger_matches WHERE period = %s""",
                (period,),
            )
            ledger_matches = cur.fetchall()

            # 2. Raw Gateway Records
            cur.execute(
                """SELECT payment_id, order_id, amount, status, utr, created_at, scenario 
                   FROM gateway_records WHERE period = %s ORDER BY created_at DESC""",
                (period,),
            )
            gateway_records = cur.fetchall()

            # 3. Raw Bank Records
            cur.execute(
                """SELECT id, utr, amount, credited_at, narration, linked_payment_ids 
                   FROM bank_records WHERE period = %s ORDER BY credited_at DESC""",
                (period,),
            )
            bank_records = cur.fetchall()

            # 4. Raw Merchant Records
            cur.execute(
                """SELECT order_id, payment_id, amount, status, marked_paid_at, scenario 
                   FROM merchant_records WHERE period = %s ORDER BY order_id ASC""",
                (period,),
            )
            merchant_records = cur.fetchall()

        # Helper to safely serialize datetime objects to ISO strings
        def serialize_rows(rows):
            serialized = []
            for r in rows:
                item = dict(r)
                for k, v in item.items():
                    if hasattr(v, "isoformat"):
                        item[k] = v.isoformat()
                    elif isinstance(v, (float, int)):
                        item[k] = float(v)
                serialized.append(item)
            return serialized

        return {
            "period": period,
            "ledger_matches": serialize_rows(ledger_matches),
            "gateway_records": serialize_rows(gateway_records),
            "bank_records": serialize_rows(bank_records),
            "merchant_records": serialize_rows(merchant_records),
        }
    finally:
        conn.close()
        
@app.get("/api/reconciliation/transaction/{payment_id}")
def get_transaction_details(payment_id: str, period: str):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # 1. Gateway Record
            cur.execute(
                """SELECT payment_id, order_id, amount, status, utr, created_at, scenario
                   FROM gateway_records WHERE payment_id = %s AND period = %s""",
                (payment_id, period),
            )
            gateway = cur.fetchone()

            # 2. Reconciled Ledger Match (if exists)
            cur.execute(
                """SELECT match_type, matched_amount, bank_amount, risk, explanation
                   FROM ledger_matches WHERE payment_id = %s AND period = %s""",
                (payment_id, period),
            )
            matched = cur.fetchone()

            # 3. Exception Details (if exists)
            cur.execute(
                """SELECT reason_code, reason_detail, recommended_action, risk, amount
                   FROM exceptions WHERE payment_id = %s AND period = %s""",
                (payment_id, period),
            )
            exception = cur.fetchone()

            # 4. Bank Record (lookup via normalized UTR or linked_payment_ids)
            bank = None
            if gateway and gateway.get("utr"):
                cur.execute(
                    """SELECT id, utr, amount, credited_at, narration, linked_payment_ids
                       FROM bank_records 
                       WHERE (UPPER(utr) = UPPER(%s) OR linked_payment_ids LIKE %s)
                         AND period = %s
                       LIMIT 1""",
                    (gateway["utr"], f"%{payment_id}%", period),
                )
                bank = cur.fetchone()

            # 5. Merchant Order Record (lookup via order_id or payment_id)
            merchant = None
            order_id = gateway.get("order_id") if gateway else None
            cur.execute(
                """SELECT order_id, payment_id, amount, status, marked_paid_at, scenario
                   FROM merchant_records 
                   WHERE (order_id = %s OR payment_id = %s) AND period = %s
                   LIMIT 1""",
                (order_id, payment_id, period),
            )
            merchant = cur.fetchone()

            def clean_dict(d):
                if not d:
                    return None
                item = dict(d)
                for k, v in item.items():
                    if hasattr(v, "isoformat"):
                        item[k] = v.isoformat()
                    elif isinstance(v, (float, int)):
                        item[k] = float(v)
                return item

            return {
                "payment_id": payment_id,
                "period": period,
                "status": "exception" if exception else ("matched" if matched else "unprocessed"),
                "gateway": clean_dict(gateway),
                "bank": clean_dict(bank),
                "merchant": clean_dict(merchant),
                "reconciled_match": clean_dict(matched),
                "exception": clean_dict(exception),
            }
    finally:
        conn.close()
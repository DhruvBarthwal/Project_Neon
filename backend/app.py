#=========== LIBRARIES ===========#

import logging
import os
import nemoguardrails.llm.clients.base as _base
import time
import json

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.rails.llm.options import GenerationOptions
from dotenv import load_dotenv
from langgraph.types import Command

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
def get_periods(agent: dict = Depends(get_current_agent)):
    return summary_service.list_periods()


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
        exceptions = cross_check_merchant(gateway_rows, merchant_rows, matched_payment_ids, exceptions)
 
        write_results(conn, req.period, matches, exceptions, triggered_by=agent["sub"], trigger_source="manual")
        summary = summary_service.build_summary(conn, req.period)
    
    finally:
        conn.close()
    
    return summary
#=========== LIBRARIES ===========#

import asyncio 
import logging
import os
import nemoguardrails.llm.clients.base as _base
import time
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.rails.llm.options import GenerationOptions
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from langgraph.types import Command

from agent.eventToolBus.event_bus import EventBus
from agent.eventToolBus.events import ToolCallRequested, ToolCallCompleted, ToolCallFailed
from agent.security.agent_identity import issue_agent_identity, verify_agent_identity
from agent.adapters.mcp_adapter import mcp_adapter
from agent.graph.runner import graph

from reconciler.main import get_connection, fetch_period, write_results
from reconciler.matcher import run_matching
from reconciler import summary_service

#========= CONNECTION ==========#

@asynccontextmanager
async def lifespan(app: FastAPI):
    await mcp_adapter.connect("salesforce_mcp", command="python", args=["mcp_servers/salesforce_server.py"])
    await mcp_adapter.connect("sap_mcp", command="python", args=["mcp_servers/sap_server.py"])
    await mcp_adapter.connect("database_mcp", command="python", args=["mcp_servers/database_server.py"])
    await mcp_adapter.connect("devops_mcp", command="python", args=["mcp_servers/devops_server.py"])
    await mcp_adapter.connect("comms_mcp", command="python", args=["mcp_servers/comms_server.py"])
    await mcp_adapter.connect("kb_mcp", command="python", args=["mcp_servers/kb_server.py"])
    yield
    await mcp_adapter.close()
    
app = FastAPI(lifespan=lifespan)

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

#=========== EVENT BUS ===========#

bus = EventBus()

#=========== CLASSES =============#

class TextRequest(BaseModel):
    text : str
    user_department: str
    user_role: str
    user_id: str
    convo_id: str
    
class RunReconciliationRequest(BaseModel):
    period: str

#============ ROUTES =============#

@app.get("/")
def home():
    return {"message" : "Backend is running...."}


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
    
    identity_token = issue_agent_identity(data.user_department, data.user_id, data.convo_id)
    verify_agent_identity(identity_token)
    
    config = {"configurable": {"thread_id": data.convo_id}}
    snapshot = graph.get_state(config)
    
    if snapshot.next:
        result = await graph.ainvoke(Command(resume=data.text), config=config)
    else:
        result = await graph.ainvoke({
            "messages": [{"role":"user", "content": data.text}],
            "department": data.user_department,
            "user_role": data.user_role,
            "user_id": data.user_id,
            "convo_id": data.convo_id,
        },
           config=config                          
        )
    if "__interrupt__" in result:
         return {"is_safe": True, "status": "awaiting_confirmation", "question": result["__interrupt__"][0].value["question"]}
     
    last_message = result["messages"][-1]
    if isinstance(last_message.content, list):
        response_text = "".join(
            block.get("text", "") for block in last_message.content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    else:
        response_text = last_message.content

    return {"is_safe": True, "status": "done", "response": response_text}

    
@app.get("/api/reconciliation/periods")
def get_periods():
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


@app.post("/api/reconciliation/run")
def run_reconciliation(req: RunReconciliationRequest):
    conn = get_connection()
    try:
        gateway_rows, bank_rows = fetch_period(conn, req.period)
        if not gateway_rows:
            raise HTTPException(
                status_code=404,
                detail=f"No gateway records found for period {req.period}. Generate data first.",
            )    
        matches, exceptions = run_matching(gateway_rows, bank_rows)
        write_results(conn, req.period, matches, exceptions)
        summary = summary_service.build_summary(conn, req.period)
    finally:
        conn.close()
        
    return summary
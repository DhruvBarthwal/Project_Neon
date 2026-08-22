#=========== LIBRARIES ===========#

import asyncio 
import logging
import os
import nemoguardrails.llm.clients.base as _base
import time
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.rails.llm.options import GenerationOptions
from dotenv import load_dotenv
from google import genai
from google.genai import types
from contextlib import asynccontextmanager

from agent.eventToolBus.event_runner import run_graph
from agent.eventToolBus.event_bus import EventBus
from agent.eventToolBus.events import ToolCallRequested, ToolCallCompleted, ToolCallFailed
from agent.security.agent_identity import issue_agent_identity
from agent.planner.prompt import generate_prompt, template
from agent.adapters.mcp_adapter import MCPAdapter
#========= CONNECTION ==========#

mcp_adapter = MCPAdapter() 

@asynccontextmanager
async def lifespan(app: FastAPI):
    await mcp_adapter.connect(
        "salesforce_mcp",
        command="python",
        args=["mcp_servers/salesforce_server.py"]
    )
    yield
    await mcp_adapter.close()
    
app = FastAPI(lifespan=lifespan)

load_dotenv()

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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

async def tool_handler(event: ToolCallRequested):
    try:
        result = await mcp_adapter.execute(event.tool, event.mcp_server, event.parameters)
        await bus.publish(ToolCallCompleted(call_id=event.call_id, result=result))
    except Exception as e:
        await bus.publish(ToolCallFailed(call_id=event.call_id, error=str(e))) 

bus.subscribe("tool_call.requested", tool_handler)

#=========== CLASSES =============#

class TextRequest(BaseModel):
    text : str
    user_department: str
    user_role: str
    user_id: str
    convo_id: str
    
#========== LLM ==============#

async def run_planner(data: TextRequest) -> dict:
    system_prompt = generate_prompt(
        user_department=data.user_department,
        user_role=data.user_role,
        user_id=data.user_id,
        convo_id=data.convo_id,
        template=template,
    )

    response = await gemini_client.aio.models.generate_content(
        model="gemini-3.5-flash",
        contents=data.text,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
            response_mime_type="application/json", 
        ),
    )

    return json.loads(response.text)

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
      
    # options = GenerationOptions(output_vars=True)
    # response = await rails.generate_async(messages=messages,options=options)
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
    
    plan = await run_planner(data)
    
    runner = await run_graph(bus,plan, department=data.user_department, identity_token=identity_token)
    
    return {
        "is_safe": True,
        "plan": plan,
        "execution_results": runner
    }
    


@app.post("/response")
def getResponse(data : TextRequest):
    return {"message" : "Getting Results...."}

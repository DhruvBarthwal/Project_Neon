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
from agent.planner.prompt import generate_prompt, template
from google import genai
from google.genai import types

from agent.eventToolBus.event_runner import run_events
from agent.eventToolBus.event_bus import EventBus

#========= CONNECTION ==========#

app = FastAPI()

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
            response_mime_type="application/json",  # forces valid JSON, no fence-stripping needed
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
      
    options = GenerationOptions(output_vars=True)
    response = await rails.generate_async(messages=messages,options=options)
    
    
    output_data = response.output_data or {}
    blocked = (
        output_data.get("triggered_input_rail") is not None
        or output_data.get("triggered_output_rail") is not None
    )
       
    if blocked:
        return {
                "is_safe": False,
                "message" : response.response
            }
    
    plan = await run_planner(data)
    
    runner = run_events(EventBus,plan)
    
    return {
        "is_safe": True,
        "plan": plan
    }
    


@app.post("/response")
def getResponse(data : TextRequest):
    return {"message" : "Getting Results...."}

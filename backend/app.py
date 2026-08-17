#=========== LIBRARIES ===========#

import asyncio 
import logging
import os
import nemoguardrails.llm.clients.base as _base
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from nemoguardrails import LLMRails, RailsConfig
from dotenv import load_dotenv

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

config = RailsConfig.from_path("config")
rails = LLMRails(config)

#=========== CLASSES =============#

class TextRequest(BaseModel):
    text : str

#============ ROUTES =============#

@app.get("/")
def home():
    return {"message" : "Backend is running...."}


@app.post("/intent")
async def getIntent(data : TextRequest):
    
    print("1. Request received")
    
    messages = [{
        "role" : "user",
        "content" : data.text
    }]
    
    print("2. Sending to Guardrails")
    
    t0 = time.time()
    
    response = await rails.generate_async(messages=messages)
    
    elapsed = time.time() - t0
    
    print("Time:", elapsed)
    print("3. Response received")
    
    return {"message" : response}


@app.post("/response")
def getResponse(data : TextRequest):
    return {"message" : "Getting Results...."}

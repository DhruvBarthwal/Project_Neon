import os
import json
import re
from typing import List, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# General LLM for completions & reports
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name=MODEL_NAME,
    temperature=0.2,
)

# Classifier LLM pinned to strict JSON object output (no tool-calling crash)
classifier_llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name=MODEL_NAME,
    temperature=0.0,
    model_kwargs={"response_format": {"type": "json_object"}},
)

def chat(prompt: str, max_tokens: int = 3072) -> str:
    """General completion helper for structured audits & markdown tables."""
    response = llm.invoke(
        [HumanMessage(content=prompt)],
        max_tokens=max_tokens,
    )
    return str(response.content)

def classify(messages: list) -> dict:
    from .prompts import SYSTEM_PROMPT

    # 1. Extract ONLY the latest user message
    user_query = ""
    for m in reversed(messages):
        content = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else "")
        role = getattr(m, "type", None) or (m.get("role") if isinstance(m, dict) else "")
        if role in ("user", "human") and content:
            user_query = content
            break

    if not user_query:
        return {"intent": "not_found", "payment_ids": [], "utrs": []}

    prompt = f"""{SYSTEM_PROMPT}

Respond ONLY with a valid JSON object matching this structure:
{{
  "intent": "lookup_record" | "metric_query" | "match_status" | "summary" | "compare_months" | "filtered_list" | "grouped_reasons" | "table_navigation" | "batch_unbundling_audit" | "reconcile_cycle" | "not_found",
  "period": "YYYY-MM" or null,
  "compare_period": "YYYY-MM" or null,
  "target_table": "exceptions" | "ledger_matches" | "gateway" | "bank" | "merchant" or null,
  "payment_ids": ["pay_..."],
  "utrs": ["UTR..."],
  "min_amount": number or null
}}

User Query: "{user_query}"
"""

    try:
        response = classifier_llm.invoke([HumanMessage(content=prompt)])
        parsed = json.loads(response.content)
        
        # Ensure fallback lists exist
        if "payment_ids" not in parsed or not isinstance(parsed["payment_ids"], list):
            parsed["payment_ids"] = []
        if "utrs" not in parsed or not isinstance(parsed["utrs"], list):
            parsed["utrs"] = []

        return parsed

    except Exception as e:
        print(">>> GROQ CLASSIFY ERROR:", repr(e))
        return {"intent": "not_found", "payment_ids": [], "utrs": []}
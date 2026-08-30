import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from typing import Literal, Optional, List
from .prompts import SYSTEM_PROMPT, MAX_PAYMENT_IDS_PER_QUESTION
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(
    model= "openai/gpt-oss-120b"
)

class ClassifyIntent(BaseModel):
    """Classify a finance-reconciliation question into an intent and extract entities."""
 
    intent: Literal[
        "lookup_record", "match_status", "summary",
        "filtered_list", "grouped_reasons", "not_found",
    ] = Field(description="Which of the 6 fixed intents this question falls into")
    payment_ids: List[str] = Field(
        default_factory=list,
        description=f"Every payment ID the question asks about, up to {MAX_PAYMENT_IDS_PER_QUESTION}",
    )
    min_amount: Optional[float] = Field(default=None, description="for filtered_list amount thresholds")
    period: Optional[str] = Field(default=None, description="e.g. 2026-05, only if explicitly named")
    
classifier_llm = llm.bind_tools([ClassifyIntent], tool_choice="ClassifyIntent")


def classify(messages: list) -> dict:

    full_messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)
    response = classifier_llm.invoke(full_messages)
 
    if not response.tool_calls:
        return {"intent": "not_found", "payment_ids": [], "min_amount": None, "period": None}
 
    args = response.tool_calls[0]["args"]
    args["payment_ids"] = (args.get("payment_ids") or [])[:MAX_PAYMENT_IDS_PER_QUESTION]
    return args


def chat(prompt: str, max_tokens: int = 150) -> str:
    """Plain text explanation. No tool binding needed here"""
    response = llm.invoke(prompt, max_tokens=max_tokens)
    return response.content.strip()
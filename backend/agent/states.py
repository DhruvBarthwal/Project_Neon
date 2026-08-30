from typing import Annotated, List, Optional, TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[List, add_messages]
    period: str
    intent: Optional[str]
    payment_ids: List[str] 
    min_amount: Optional[str]
    auto_run_notice: Optional[str]
    answer: Optional[str]
from typing import Annotated, TypedDict, Optional
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    department: str
    convo_id: str
    user_id: str
    user_role: str
    summary: Optional[str]
    

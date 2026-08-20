from dataclasses import dataclass, field
from typing import Any
from enum import Enum
import uuid
import time

class EventType(str, Enum):
    TOOL_CALL_REQUESTED = "tool_call.requested"
    TOOL_CALL_COMPLETED = "tool_call.completed"
    TOOL_CALL_FAILED = "tool_call.failed"
    
@dataclass
class ToolCallRequested:
    call_id: str
    step_id: str
    mcp_server: str
    tool: str
    parameters: dict[str, Any]
    event_type: EventType = EventType.TOOL_CALL_REQUESTED
    
@dataclass
class ToolCallCompleted:
    call_id: str
    result: Any
    event_type: EventType = EventType.TOOL_CALL_COMPLETED
    
@dataclass
class ToolCallFailed:
    call_id: str
    error: str
    event_type: EventType = EventType.TOOL_CALL_FAILED
    
def new_call_id() ->str:
    return str(uuid.uuid4())
import os
import json
import asyncio

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import ToolMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt
from dotenv import load_dotenv

from .state import AgentState
from .tools import read_ticket, update_email
from agent.eventToolBus.event_bus import EventBus
from agent.eventToolBus.events import ToolCallCompleted
from agent.planner.tools_desc import DEPARTMENT_TOOL_PERMISSIONS, MASTER_TOOL_CATALOG
from agent.graph.tools import ALL_TOOLS
from agent.planner.prompt import build_system_prompt
from agent.adapters.mcp_adapter import mcp_adapter

load_dotenv()

bus  = EventBus()

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.2,
)

async def mcp_adapter_execute_safe(tool_name, mcp_server, args):
    return await mcp_adapter.execute(tool_name, mcp_server, args)

def find_tool_meta(tool_name: str):
    for mcp_server, tools in MASTER_TOOL_CATALOG.items():
        if tool_name in tools:
            return mcp_server, tools[tool_name]
    return None, None
    
def is_step_permitted(tool_name: str, mcp_server: str, department: str) -> bool:
    for entry in DEPARTMENT_TOOL_PERMISSIONS.get(department.lower(),[]):
        if entry["mcp"] == mcp_server and tool_name in entry["tools"]:
            return True
    return False

async def agent_node(state: AgentState):
    permitted = {t for entry in DEPARTMENT_TOOL_PERMISSIONS.get(state["department"].lower(), []) for t in entry["tools"]}
    tools_for_llm = [ALL_TOOLS[name] for name in permitted if name in ALL_TOOLS]
    
    system_prompt = build_system_prompt(state["department"], state["user_role"], state["user_id"], state["convo_id"])
    
    system_msg = {
        "role": "system",
        "content": system_prompt
    }
    
    bound_llm = llm.bind_tools(tools_for_llm)
    response = await bound_llm.ainvoke([system_msg, *state["messages"]])
    return {"messages": [response]}

async def tool_node(state: AgentState):
    last = state["messages"][-1]
    outputs = []
    
    for call in last.tool_calls:
        tool_name, args, call_id = call["name"], call["args"], call["id"]
        mcp_server, meta = find_tool_meta(tool_name)
        
        if not meta or not is_step_permitted(tool_name, mcp_server, state["department"]):
            outputs.append(ToolMessage(content=f"Denied: {tool_name} not permitted for {state['department']}", tool_call_id=call_id))
            continue
        
        if meta["risk_level"] == "MUTATION_HIGH_RISK":
            answer = interrupt({"question": f"Confirm: {tool_name} with {args}? (yes/no)"})
            while answer.strip().lower() not in {"yes", "no", "cancel", "confirm", "approve"}:
                answer = interrupt({"question": f"I need a clear yes or no — confirm {tool_name} with {args}?"})
            if answer.strip().lower() in {"no", "cancel"}:
                outputs.append(ToolMessage(content=f"Cancelled {tool_name} per user request.", tool_call_id=call_id))
                continue
            
        result = await mcp_adapter_execute_safe(tool_name, mcp_server, args)
        print(f"DEBUG raw result for {tool_name}: {result!r}")
        asyncio.create_task(bus.publish(ToolCallCompleted(call_id=call_id, result = result)))
        outputs.append(ToolMessage(content=json.dumps(result), tool_call_id=call_id))
            
    return {"messages": outputs}


async def mcp_adapter_execute_safe(tool_name, mcp_server, args):
    from agent.graph.tools import mcp_adapter
    return await mcp_adapter.execute(tool_name, mcp_server, args)

def route_after_agent(state: AgentState):
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END


builder = StateGraph(AgentState)
builder.add_node("agent", agent_node)
builder.add_node("tools", tool_node)
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", route_after_agent, {"tools": "tools", END:END})
builder.add_edge("tools","agent")

graph = builder.compile(checkpointer=InMemorySaver())
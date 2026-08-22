import asyncio
import re

from .event_bus import EventBus
from .events import ToolCallCompleted, ToolCallFailed, ToolCallRequested, new_call_id
from agent.planner.tools_desc import DEPARTMENT_TOOL_PERMISSIONS
from agent.security.agent_identity import verify_agent_identity

REF_PATTERN = re.compile(r"^\$ref\(([\w\-]+)\.([\w\-]+)\)$")


def resolve_parameters(parameters: dict, results: dict) -> dict:
    resolved = {}
    for key, value in parameters.items():
        if isinstance(value,str):
            match = REF_PATTERN.match(value)
            if match:
                ref_step, ref_key = match.groups()
                resolved[key] = results.get(ref_step, {}).get(ref_key)
                continue
        
            resolved[key] = value
    return resolved
 
 
def is_step_permitted(step: dict, department: str) -> bool:
    dept_permissions = DEPARTMENT_TOOL_PERMISSIONS.get(department.lower(),[])
    for entry in dept_permissions:
        if entry["mcp"] == step["mcp_server"] and step["tool"] in entry["tools"]:
            return True
    return False
                

async def run_graph(bus: EventBus, plan: dict, department: str, identity_token: str) -> None:
    try:
        claims = verify_agent_identity(identity_token)
    except Exception as e:
        print(f"Agent identity verification failed: {e}")
        return {"error": "invalid agent identity"}
    
    verified_department = claims["department"]
    
    if not plan.get("is_actionable", False):
        print("Plan not actionable:", plan.get("rejection_resason"))
        return
    
    steps = plan["execution_graph"]
    done_events = {step["step_id"]: asyncio.Event() for step in steps}
    results: dict[str, any] = {}
    
    call_id_to_step: dict[str, str] = {}
    
    async def on_completed(event: ToolCallCompleted):
        step_id = call_id_to_step[event.call_id]
        results[step_id] = event.result
        print(f"{step_id} completed")
        done_events[step_id].set()
    
    async def on_failed(event: ToolCallFailed):
        step_id = call_id_to_step[event.call_id]
        print(f"{step_id} failed: {event.error}")
        results[step_id] = None
        done_events[step_id].set()
        
    bus.subscribe("tool_call.completed",on_completed)
    bus.subscribe("tool_call.failed",on_failed)
    
    async def run_step(step: dict):
        for dep_id in step.get("depends_on",[]):
            await done_events[dep_id].wait()
            
        # RBAC Gate
        if not is_step_permitted(step, verified_department):
            print(f"BLOCKED: {step['step_id']} — {step['tool']} on {step['mcp_server']} not permitted for {verified_department}")
            results[step["step_id"]] = {"error": "RBAC denied", "tool": step["tool"], "mcp_server": step["mcp_server"]}
            done_events[step["step_id"].set()]
            return
        
        call_id = new_call_id()
        call_id_to_step[call_id] = step["step_id"]
        
        resolved_params = resolve_parameters(step["parameters"], results)
        
        print(f"Publishing {step['step_id']} (waited on {step.get('depends_on', [])})")
        await bus.publish(ToolCallRequested(
            call_id = call_id,
            step_id = step["step_id"],
            mcp_server = step["mcp_server"],
            tool = step["tool"],
            parameters = resolved_params
        ))
        
    await asyncio.gather(*(run_step(step) for step in steps))
    
    return results
from event_bus import EventBus
from events import ToolCallRequested, new_call_id

async def run_events(bus: EventBus, plan: dict) -> None:
    """Takes the planner's JSON output and publishes one
        ToolCallRequested event per step    
    """
    
    if not plan.get("is_actionable", False):
        print("Plan not actionable:", plan.get("rejection_reason"))
        return
    
    for step in plan["execution_graph"]:
        event = ToolCallRequested(
            call_id=new_call_id(),
            step_id=step["step_id"],
            mcp_server=step["mcp_server"],
            tool=step["tool"],
            parameters=step["parameters"]
        )
        print(f"Publishing: {step['step_id']} -> {step['tool']} on {step['mcp_server']}")
        await bus.publish(event)
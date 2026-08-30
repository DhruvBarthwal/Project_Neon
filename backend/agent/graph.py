from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from .states import AgentState
from . import nodes

def route_after_reconcile(state: AgentState) -> str:
    notice = state.get("auto_run_notice")
    if notice and notice.startswith("NO_DATA:"):
        return "no_data"
    return "continue"

def route_by_intent(state: AgentState) -> str:
    return state.get("intent","not_found")

def build_graph():
    graph = StateGraph(AgentState)
    
    graph.add_node("ensure_reconciled", nodes.ensure_reconciled_node)
    graph.add_node("no_data_response", nodes.no_data_response_node)
    graph.add_node("classify_intent", nodes.classify_intent_node)
    graph.add_node("lookup_record", nodes.lookup_record_node)
    graph.add_node("match_status", nodes.match_status_node)
    graph.add_node("summary", nodes.summary_node)
    graph.add_node("filtered_list", nodes.filtered_list_node)
    graph.add_node("grouped_reasons", nodes.grouped_reasons_node)
    graph.add_node("not_found", nodes.not_found_node)
    
    graph.set_entry_point("ensure_reconciled")
 
    graph.add_conditional_edges(
        "ensure_reconciled",
        route_after_reconcile,
        {"no_data": "no_data_response", "continue": "classify_intent"},
    )
    graph.add_edge("no_data_response", END)
 
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "lookup_record": "lookup_record",
            "match_status": "match_status",
            "summary": "summary",
            "filtered_list": "filtered_list",
            "grouped_reasons": "grouped_reasons",
            "not_found": "not_found",
        },
    )
    for intent_node in ["lookup_record", "match_status", "summary", "filtered_list", "grouped_reasons", "not_found"]:
        graph.add_edge(intent_node, END)
 
    return graph.compile(checkpointer=MemorySaver())

graph = build_graph()

def ask(question: str, period: str, thread_id: str) -> str:
    """thread_id should be stable per configuration"""
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        {"messages": [HumanMessage(content=question)], "period": period},
        config=config,
    )
    return result["answer"]
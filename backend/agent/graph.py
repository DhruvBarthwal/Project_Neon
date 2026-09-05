# In agent/graph.py

from langchain_core.messages import HumanMessage
from langgraph import graph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from .states import AgentState
from . import nodes


def route_after_reconcile(state: AgentState) -> str:
    notice = state.get("auto_run_notice") or ""
    if notice.startswith("NO_DATA:"):
        return "no_data"
    return "continue"


def planner_fanout(state: AgentState) -> list[str]:
    intents = state.get("intents") or []
    valid_nodes = [
        "lookup_record", "metric_query", "match_status",
        "batch_unbundling_audit", "table_navigation", "reconcile_cycle",
        "summary", "compare_months", "filtered_list", "grouped_reasons", "top_exception_analysis"
    ]
    targets = [i for i in intents if i in valid_nodes]
    return targets if targets else ["not_found"]


def build_graph():
    graph = StateGraph(AgentState)
    
    # 1. Base Setup Nodes
    graph.add_node("ensure_reconciled", nodes.ensure_reconciled_node)
    graph.add_node("no_data_response", nodes.no_data_response_node)
    graph.add_node("classify_intent", nodes.classify_intent_node)

    # 2. Worker / Tool Execution Nodes
    graph.add_node("lookup_record", nodes.lookup_record_node)
    graph.add_node("metric_query", nodes.metric_query_node)
    graph.add_node("match_status", nodes.match_status_node)
    graph.add_node("batch_unbundling_audit", nodes.batch_unbundling_audit_node)
    graph.add_node("table_navigation", nodes.table_navigation_node)
    graph.add_node("reconcile_cycle", nodes.reconcile_cycle_node)
    graph.add_node("summary", nodes.summary_node)
    graph.add_node("compare_months", nodes.compare_months_node)
    graph.add_node("filtered_list", nodes.filtered_list_node)
    graph.add_node("grouped_reasons", nodes.grouped_reasons_node)
    graph.add_node("top_exception_analysis", nodes.top_exception_analysis_node)
    graph.add_node("not_found", nodes.not_found_node)

    # 3. Aggregation & Synthesis Node
    graph.add_node("synthesize_plan", nodes.synthesize_plan_node)

    # Control Flow
    graph.set_entry_point("ensure_reconciled")

    # Fixed: uses defensive route_after_reconcile instead of lambda
    graph.add_conditional_edges(
        "ensure_reconciled",
        route_after_reconcile,
        {"no_data": "no_data_response", "continue": "classify_intent"},
    )
    graph.add_edge("no_data_response", END)

    # PARALLEL FAN-OUT: LangGraph triggers all returned worker nodes concurrently
    graph.add_conditional_edges(
        "classify_intent",
        planner_fanout,
        [
            "lookup_record", "metric_query", "match_status",
            "batch_unbundling_audit", "table_navigation", "reconcile_cycle",
            "summary", "compare_months", "filtered_list", "grouped_reasons", "top_exception_analysis", "not_found"
        ]
    )

    # FAN-IN: All parallel worker nodes converge into the synthesizer
    workers = [
        "lookup_record", "metric_query", "match_status",
        "batch_unbundling_audit", "table_navigation", "reconcile_cycle",
        "summary", "compare_months", "filtered_list", "grouped_reasons", "top_exception_analysis", "not_found"
    ]
    for w in workers:
        graph.add_edge(w, "synthesize_plan")

    graph.add_edge("synthesize_plan", END)

    return graph.compile(checkpointer=MemorySaver())


graph = build_graph()


def ask(question: str, period: str, thread_id: str, actor: str) -> str:
    config = {"configurable": {"thread_id": thread_id}}
    graph.update_state(config, {"sub_answers": []})
    result = graph.invoke(
        {
            "messages": [HumanMessage(content=question)],
            "period": period,
            "actor": actor,  # Strictly populated from verified JWT claims
            "sub_answers": [],
        },
        config=config,
    )
    return result.get("answer") or "No response generated."
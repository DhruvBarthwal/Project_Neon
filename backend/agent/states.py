from typing import Annotated, List, Optional, TypedDict
from langgraph.graph.message import add_messages

INTENTS = [
    "lookup_record",          # 1 or more payment IDs / UTRs
    "metric_query",           # Quick targeted question: match rate, count, total risk
    "summary",                # Comprehensive monthly closure report
    "compare_months",         # Delta analysis between 2 cycles
    "filtered_list",          # Threshold filtering (e.g. > 50000)
    "grouped_reasons",        # Exception category distributions
    "table_navigation",       # Deep-link to full tables
    "batch_unbundling_audit", # UTR lump-sum splits
    "reconcile_cycle",        # Trigger matching
    "not_found"               # off-topic queries
]

class AgentState(TypedDict):
    messages: Annotated[List, add_messages]
    period: str
    compare_period: Optional[str]
    target_table: Optional[str]
    utrs: List[str]
    intent: Optional[str]
    payment_ids: List[str]
    min_amount: Optional[str]
    auto_run_notice: Optional[str]
    answer: Optional[str]
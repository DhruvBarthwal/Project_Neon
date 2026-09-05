from typing import Annotated, List, Optional, TypedDict
from langgraph.graph.message import add_messages
import operator

INTENTS = [
    "lookup_record",          # 1 or more payment IDs / UTRs
    "metric_query",           # Quick targeted question: match rate, count, total risk
    "match_status",          # Check if a specific payment ID / UTR is matched
    "summary",                # Comprehensive monthly closure report
    "compare_months",         # Delta analysis between 2 cycles
    "filtered_list",          # Threshold filtering (e.g. > 50000)
    "grouped_reasons",        # Exception category distributions
    "table_navigation",       # Deep-link to full tables
    "batch_unbundling_audit", # UTR lump-sum splits
    "reconcile_cycle",  
    "top_exception_analysis",# Trigger matching
    "not_found"               # off-topic queries
]

class AgentState(TypedDict):
    messages: Annotated[List, add_messages]
    period: str
    compare_period: Optional[str]
    target_table: Optional[str]
    target_tables: List[str]          # supports multi-table requests, e.g. "gateway and bank"
    utrs: List[str]
    intents: List[str]
    payment_ids: List[str]
    min_amount: Optional[str]
    actor: Optional[str]
    auto_run_notice: Optional[str]
    sub_answers: Annotated[List[str], operator.add]
    answer: Optional[str]
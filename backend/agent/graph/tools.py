from langchain_core.tools import tool
from agent.adapters.mcp_adapter import mcp_adapter

@tool
async def read_ticket(ticket_id: str) -> dict:
    """Fetch customer issue, urgency, and SLA status"""
    return await mcp_adapter.execute("read_ticket", "salesforce_mcp", {"ticket_id": ticket_id})

@tool
async def update_email(ticket_id: str, new_email: str) -> dict:
    """Update customer contact email address"""
    return await mcp_adapter.execute("update_email", "salesforce_mcp", {"ticket_id": ticket_id, "new_email": new_email})

@tool
async def read_opportunity(opportunity_id: str) -> dict:
    """Read deal value, contract tier, and sales opportunity data"""
    return await mcp_adapter.execute("read_opportunity", "salesforce_mcp", {"opportunity_id": opportunity_id})

@tool
async def read_ledger(invoice_id: str) -> dict:
    """Fetch financial transaction ledger and balances"""
    return await mcp_adapter.execute("read_ledger", "sap_mcp", {"invoice_id": invoice_id})

@tool
async def create_invoice(customer_id: str, amount: float, items: list) -> dict:
    """Generate a new vendor or customer invoice"""
    return await mcp_adapter.execute("create_invoice", "sap_mcp", {"customer_id": customer_id, "amount": amount, "items": items})

@tool
async def refund_invoice(invoice_id: str, amount: float, reason: str) -> dict:
    """Execute refund on an existing invoice (Threshold gated)"""
    return await mcp_adapter.execute("refund_invoice", "sap_mcp", {"invoice_id": invoice_id, "amount": amount, "reason": reason})

@tool
async def read_payroll(employee_id: str) -> dict:
    """Read confidential employee salary and compensation"""
    return await mcp_adapter.execute("read_payroll", "database_mcp", {"employee_id": employee_id})

@tool
async def update_employee_record(employee_id: str, field: str, value: str) -> dict:
    """Update employee job title, department, or active status"""
    return await mcp_adapter.execute("update_employee_record", "database_mcp", {"employee_id": employee_id, "field": field, "value": value})

@tool
async def read_logs(service_name: str) -> dict:
    """Fetch microservice health, error rates, and cluster logs"""
    return await mcp_adapter.execute("read_logs", "devops_mcp", {"service_name": service_name})

@tool
async def restart_service(service_name: str) -> dict:
    """Restart a specific microservice pod or container"""
    return await mcp_adapter.execute("restart_service", "devops_mcp", {"service_name": service_name})

@tool
async def rollback_deploy(service_name: str, target_version: str) -> dict:
    """Roll back production deployment to a stable commit"""
    return await mcp_adapter.execute("rollback_deploy", "devops_mcp", {"service_name": service_name, "target_version": target_version})

@tool
async def send_notification(channel: str, message: str) -> dict:
    """Send alerts or messages to Slack/Teams channels"""
    return await mcp_adapter.execute("send_notification", "comms_mcp", {"channel": channel, "message": message})

@tool
async def search_knowledge_base(query: str) -> dict:
    """Semantic search over company SOPs, manuals, and FAQs"""
    return await mcp_adapter.execute("search_knowledge_base", "kb_mcp", {"query": query})

@tool
async def cancel_subscription(account_id: str) -> dict:
    """Cancel active recurring customer subscription"""
    return await mcp_adapter.execute("cancel_subscription", "kb_mcp", {"account_id": account_id})

@tool
async def read_company_calendar(date_range: str) -> dict:
    """Read official corporate calendar and on-call schedules"""
    return await mcp_adapter.execute("read_company_calendar", "kb_mcp", {"date_range": date_range})


ALL_TOOLS = {
    "read_ticket": read_ticket,
    "update_email": update_email,
    "read_opportunity": read_opportunity,
    "read_ledger": read_ledger,
    "create_invoice": create_invoice,
    "refund_invoice": refund_invoice,
    "read_payroll": read_payroll,
    "update_employee_record": update_employee_record,
    "read_logs": read_logs,
    "restart_service": restart_service,
    "rollback_deploy": rollback_deploy,
    "send_notification": send_notification,
    "search_knowledge_base": search_knowledge_base,
    "cancel_subscription": cancel_subscription,
    "read_company_calendar": read_company_calendar,
}
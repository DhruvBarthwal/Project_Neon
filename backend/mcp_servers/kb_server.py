from fastmcp import FastMCP

mcp = FastMCP("kb_mcp")

KB = {"reset password": "Go to Settings > Security > Reset Password."}
SUBSCRIPTIONS = {"ACC-1": {"status": "active"}}
CALENDAR = {"this week": "No scheduled on-call rotations."}

@mcp.tool()
def search_knowledge_base(query: str) -> dict:
    """Semantic search over company SOPs, manuals, and FAQs"""
    for key, answer in KB.items():
        if key in query.lower():
            return {"answer": answer}
    return {"answer": "No matching article found."}

@mcp.tool()
def cancel_subscription(account_id: str) -> dict:
    """Cancel active recurring customer subscription"""
    if account_id not in SUBSCRIPTIONS:
        return {"error": f"Account {account_id} not found"}
    SUBSCRIPTIONS[account_id]["status"] = "cancelled"
    return {"account_id": account_id, "status": "cancelled"}

@mcp.tool()
def read_company_calendar(date_range: str) -> dict:
    """Read official corporate calendar and on-call schedules"""
    return {"date_range": date_range, "info": CALENDAR.get(date_range, "No data for that range.")}

if __name__ == "__main__":
    mcp.run(transport="stdio")
from fastmcp import FastMCP

mcp = FastMCP("salesforce_mcp")

TICKETS = {
    "TCK-4821": {"customer_email": "old@example.com", "issue": "Login failure", "urgency": "high"},
}

@mcp.tool()
def read_ticket(ticket_id: str) -> dict:
    """Fetch customer issue, urgency, and SLA status"""
    ticket = TICKETS.get(ticket_id)
    if not ticket:
        return {"error" : f"Ticket {ticket_id} not found"}
    return ticket

@mcp.tool()
def update_email(ticket_id: str, new_email: str) -> dict:
    """Update customer contact email address"""
    if ticket_id not in TICKETS:
        return {"error": f"Ticket {ticket_id} not found"}
    TICKETS[ticket_id]["customer_email"] = new_email
    return {"status": "updated", "ticket_id": ticket_id,"new_email": new_email}

if __name__ == "__main__":
    mcp.run(transport="stdio")
    
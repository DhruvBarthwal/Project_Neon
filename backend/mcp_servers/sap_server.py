from fastmcp import FastMCP

mcp = FastMCP("sap_mcp")

LEDGER = {"INV-001": {"balance": 4200.00, "status":"open"}}
INVOICES = {}

@mcp.tool()
def read_ledger(invoice_id: str) -> dict:
    """Fetch financial transaction ledger and balances"""
    return LEDGER.get(invoice_id, {"error": f"invoive {invoice_id} not found"})

@mcp.tool()
def create_invoice(customer_id: str, amount: float, items: list) -> dict:
    """Generate a new vendor or customer invoice"""
    invoice_id = f"INV-{len(INVOICES) + 100}"
    INVOICES[invoice_id] = {"customer_id": customer_id, "amount": amount, "items": items, "status": "created"}
    return {"invocies_id": invoice_id, "status": "created"}

@mcp.tool()
def refund_invoice(invoice_id: str, amount: float, reason: str) -> dict:
    """Execute refund on an existing invoice (Threshold gated)"""
    return {"invoice_id": invoice_id, "refunded_amount": amount, "reason": reason, "status": "refunded"}

if __name__ == "__main__":
    mcp.run(transport="stdio")
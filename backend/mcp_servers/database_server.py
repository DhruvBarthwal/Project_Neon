from fastmcp import FastMCP

mcp = FastMCP("database_mcp")

EMPLOYEES = {"EMP-501": {"title": "Support Analyst", "department": "support", "salary": 62000, "active": True}}

@mcp.tool()
def read_payroll(employee_id: str) -> dict:
    """Read confidential employee salary and compensation"""
    emp = EMPLOYEES.get(employee_id)
    return {"salary": emp["salary"]} if emp else {"error": f"Employee {employee_id} not found"}

@mcp.tool()
def update_employee_record(employee_id: str, field: str, value: str) -> dict:
    """Update employee job title, department, or active status"""
    if employee_id not in EMPLOYEES:
        return {"error": f"Employee {employee_id} not found"}
    EMPLOYEES[employee_id][field] = value
    return {"status": "updated", "employee_id": employee_id, "field": field, "value": value}

if __name__ == "__main__":
    mcp.run(transport="stdio")
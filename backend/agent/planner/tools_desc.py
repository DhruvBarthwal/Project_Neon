MASTER_TOOL_CATALOG = {
    # 1. Salesforce MCP
    "salesforce_mcp": {
        "read_ticket": {
            "description": "Fetch customer issue, urgency, and SLA status",
            "risk_level": "READ_ONLY",
            "parameters": {"ticket_id": "string"}
        },
        "update_email": {
            "description": "Update customer contact email address",
            "risk_level": "MUTATION_LOW_RISK",
            "parameters": {"ticket_id": "string", "new_email": "string"}
        },
        "read_opportunity": {
            "description": "Read deal value, contract tier, and sales opportunity data",
            "risk_level": "READ_ONLY",
            "parameters": {"opportunity_id": "string"}
        }
    },
    # 2. SAP / ERP MCP
    "sap_mcp": {
        "read_ledger": {
            "description": "Fetch financial transaction ledger and balances",
            "risk_level": "READ_ONLY",
            "parameters": {"invoice_id": "string"}
        },
        "create_invoice": {
            "description": "Generate a new vendor or customer invoice",
            "risk_level": "MUTATION_LOW_RISK",
            "parameters": {"customer_id": "string", "amount": "number", "items": "array"}
        },
        "refund_invoice": {
            "description": "Execute refund on an existing invoice (Threshold gated)",
            "risk_level": "MUTATION_HIGH_RISK",
            "parameters": {"invoice_id": "string", "amount": "number", "reason": "string"}
        }
    },
    # 3. Database / HR MCP
    "database_mcp": {
        "read_payroll": {
            "description": "Read confidential employee salary and compensation",
            "risk_level": "READ_ONLY",
            "parameters": {"employee_id": "string"}
        },
        "update_employee_record": {
            "description": "Update employee job title, department, or active status",
            "risk_level": "MUTATION_LOW_RISK",
            "parameters": {"employee_id": "string", "field": "string", "value": "string"}
        }
    },
    # 4. DevOps MCP
    "devops_mcp": {
        "read_logs": {
            "description": "Fetch microservice health, error rates, and cluster logs",
            "risk_level": "READ_ONLY",
            "parameters": {"service_name": "string"}
        },
        "restart_service": {
            "description": "Restart a specific microservice pod or container",
            "risk_level": "MUTATION_LOW_RISK",
            "parameters": {"service_name": "string"}
        },
        "rollback_deploy": {
            "description": "Roll back production deployment to a stable commit",
            "risk_level": "MUTATION_HIGH_RISK",
            "parameters": {"service_name": "string", "target_version": "string"}
        }
    },
    # 5. Comms MCP (Global)
    "comms_mcp": {
        "send_notification": {
            "description": "Send alerts or messages to Slack/Teams channels",
            "risk_level": "MUTATION_LOW_RISK",
            "parameters": {"channel": "string", "message": "string"}
        }
    },
    # 6. Knowledge Base MCP (Global)
    "kb_mcp": {
        "search_knowledge_base": {
            "description": "Semantic search over company SOPs, manuals, and FAQs",
            "risk_level": "READ_ONLY",
            "parameters": {"query": "string"}
        },
        "cancel_subscription": {
            "description": "Cancel active recurring customer subscription",
            "risk_level": "MUTATION_LOW_RISK",
            "parameters": {"account_id": "string"}
        },
        "read_company_calendar": {
            "description": "Read official corporate calendar and on-call schedules",
            "risk_level": "READ_ONLY",
            "parameters": {"date_range": "string"}
        }
    }
}

# The Deterministic RBAC Department Scoping
DEPARTMENT_TOOL_PERMISSIONS = {
    "finance": [
        {"mcp": "sap_mcp", "tools": ["read_ledger", "create_invoice", "refund_invoice"]},
        {"mcp": "salesforce_mcp", "tools": ["read_opportunity"]},
        {"mcp": "kb_mcp", "tools": ["search_knowledge_base", "read_company_calendar"]},
        {"mcp": "comms_mcp", "tools": ["send_notification"]}
    ],
    "support": [
        {"mcp": "salesforce_mcp", "tools": ["read_ticket", "update_email", "read_opportunity"]},
        {"mcp": "kb_mcp", "tools": ["search_knowledge_base", "cancel_subscription", "read_company_calendar"]},
        {"mcp": "comms_mcp", "tools": ["send_notification"]}
    ],
    "devops": [
        {"mcp": "devops_mcp", "tools": ["read_logs", "restart_service", "rollback_deploy"]},
        {"mcp": "kb_mcp", "tools": ["search_knowledge_base", "read_company_calendar"]},
        {"mcp": "comms_mcp", "tools": ["send_notification"]}
    ],
    "hr": [
        {"mcp": "database_mcp", "tools": ["read_payroll", "update_employee_record"]},
        {"mcp": "kb_mcp", "tools": ["search_knowledge_base", "read_company_calendar"]},
        {"mcp": "comms_mcp", "tools": ["send_notification"]}
    ]
}
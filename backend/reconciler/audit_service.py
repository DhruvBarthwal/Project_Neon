import json
from reconciler.db import get_connection

def record_business_audit(
    period: str,
    event_type: str,
    target_identifier: str,
    outcome_status: str,
    intent: str = "lookup_record",
    exposure_amount: float = 0.00,
    actor: str = "analyst_copilot",
    metadata: dict = None,
):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_logs 
                (period, actor, event_type, intent, target_identifier, outcome_status, exposure_amount, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    period,
                    actor,
                    event_type,
                    intent,
                    target_identifier,
                    outcome_status,
                    exposure_amount,
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()
    finally:
        conn.close()
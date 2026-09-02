import random
from datetime import timedelta

from reconciler.main import get_connection, fetch_period

MERCHANT_SCENARIO_WEIGHTS = [
    ("merchant_synced", 0.85),
    ("webhook_lag", 0.10),
    ("unverified_claim", 0.03),
    ("merchant_failed_status", 0.02),
]


def _weighted_merchant_scenario():
    r = random.random()
    acc = 0.0
    for name, w in MERCHANT_SCENARIO_WEIGHTS:
        acc += w
        if r <= acc:
            return name
    return MERCHANT_SCENARIO_WEIGHTS[-1][0]


def generate_merchant_records(gateway_rows, period):
    merchant_rows = []

    for g in gateway_rows:
        if not g.get("order_id"):
            continue
        scenario = _weighted_merchant_scenario()

        if scenario == "merchant_synced":
            merchant_rows.append({
                "order_id": g["order_id"],
                "payment_id": g["payment_id"],
                "amount": g["amount"],
                "status": "paid" if g["status"] == "captured" else "failed",
                "marked_paid_at": g["created_at"] + timedelta(minutes=random.randint(1, 30))
                                   if g["status"] == "captured" else None,
                "period": period,
                "scenario": scenario,
            })

        elif scenario == "webhook_lag":
            merchant_rows.append({
                "order_id": g["order_id"],
                "payment_id": None,
                "amount": g["amount"],
                "status": "pending",
                "marked_paid_at": None,
                "period": period,
                "scenario": scenario,
            })

        elif scenario == "unverified_claim":
            merchant_rows.append({
                "order_id": g["order_id"],
                "payment_id": None,
                "amount": g["amount"],
                "status": "paid",
                "marked_paid_at": g["created_at"] - timedelta(hours=random.randint(1, 5)),
                "period": period,
                "scenario": scenario,
            })

        elif scenario == "merchant_failed_status":
            merchant_rows.append({
                "order_id": g["order_id"],
                "payment_id": g["payment_id"],
                "amount": g["amount"],
                "status": "failed",
                "marked_paid_at": None,
                "period": period,
                "scenario": scenario,
            })

    return merchant_rows


def insert_merchant_rows(conn, merchant_rows):
    with conn.cursor() as cur:
        for m in merchant_rows:
            cur.execute(
                """INSERT INTO merchant_records
                   (order_id, payment_id, amount, status, marked_paid_at, period, scenario)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (m["order_id"], m["payment_id"], m["amount"], m["status"],
                 m["marked_paid_at"], m["period"], m["scenario"]),
            )
    conn.commit()


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--period", type=str, required=True)
    args = ap.parse_args()

    conn = get_connection()
    try:
        gateway_rows, _ = fetch_period(conn, args.period)
        if not gateway_rows:
            print(f"No gateway records found for period {args.period}. Generate gateway data first.")
            raise SystemExit(1)

        merchant_rows = generate_merchant_records(gateway_rows, args.period)
        insert_merchant_rows(conn, merchant_rows)
        print(f"Inserted {len(merchant_rows)} merchant records for period {args.period}.")
    finally:
        conn.close()
from ..reconciler.main import get_connection

conn = get_connection()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM merchant_records")
    print("total merchant_records (all periods):", cur.fetchone()[0])
    cur.execute("SELECT DISTINCT period FROM merchant_records")
    print("periods present:", cur.fetchall())
conn.close()

if __name__ == "__main__":
    import argparse
    from reconciler.main import get_connection, fetch_period

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
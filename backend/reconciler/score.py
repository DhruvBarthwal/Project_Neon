import argparse
import os
import psycopg2
 
 
def get_connection():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", ""),
        dbname=os.environ.get("PGDATABASE", "finance_controller"),
    )
 
 
QUERY = """
SELECT
    g.scenario,
    g.expected_result,
    CASE
        WHEN EXISTS (SELECT 1 FROM ledger_matches m
                     WHERE m.payment_id = g.payment_id AND m.period = g.period)
            THEN 'match'
        WHEN EXISTS (SELECT 1 FROM exceptions e
                     WHERE e.payment_id = g.payment_id AND e.period = g.period)
            THEN 'exception'
        ELSE 'unaccounted'  -- shouldn't happen: row wasn't written anywhere
    END AS actual_result
FROM gateway_records g
WHERE g.period = %s;
"""
 
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", required=True)
    args = ap.parse_args()
 
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(QUERY, (args.period,))
        rows = cur.fetchall()  # (scenario, expected_result, actual_result)
    conn.close()
 
    by_scenario = {}
    for scenario, expected, actual in rows:
        s = by_scenario.setdefault(scenario, {"correct": 0, "total": 0})
        s["total"] += 1
        if expected == actual:
            s["correct"] += 1
 
    total_correct = sum(s["correct"] for s in by_scenario.values())
    total_rows = sum(s["total"] for s in by_scenario.values())
 
    print(f"\n=== Scoring report for {args.period} ===")
    for scenario, s in sorted(by_scenario.items()):
        pct = s["correct"] / s["total"] * 100
        flag = "" if pct == 100 else "  <-- check this"
        print(f"{scenario:<25} : {s['correct']:>3}/{s['total']:<3} correct ({pct:5.1f}%){flag}")
 
    print(f"\nOverall accuracy vs ground truth: {total_correct}/{total_rows} "
          f"({total_correct/total_rows*100:.1f}%)")
 
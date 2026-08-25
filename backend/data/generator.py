"""
Synthetic data generator for the Track 04 reconciliation engine.

Two modes:
  python generate_data.py --baseline 300 --period 2026-05
      -> generates one baseline batch (~300 rows) for a period and inserts it

  python generate_data.py --trickle --period 2026-05 --interval 5
      -> after the baseline exists, periodically inserts 1-2 new rows
         every `interval` seconds, purely for a "live dashboard" demo effect.
         This is still 100% synthetic data — just released gradually
         instead of all at once.

Every gateway row carries a hidden `scenario` + `expected_result` —
this is the ground truth used later to score the matcher's real
accuracy. The matcher itself must never read these two columns.
"""

import argparse
import os
import random
import string
import time
from datetime import datetime, timedelta

import psycopg2

def get_connection():
    """
    Connect using individual PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE
    env vars instead of one combined connection-string. This avoids a
    common Windows gotcha: if your password contains an '@', ':', or '#'
    character, a single "postgresql://user:pass@host/db" string gets
    mis-parsed (the special character breaks the split between the
    password and the host). Separate variables have no such problem.
    """
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", ""),
        dbname=os.environ.get("PGDATABASE", "finance_controller"),
    )

# Roughly the distribution discussed: mostly clean, then a
# deliberately messy tail so the exception list has real substance.
SCENARIO_WEIGHTS = [
    ("clean_exact",        0.55),
    ("fee_delta",          0.15),
    ("settlement_delay",   0.08),
    ("garbled_utr",        0.07),
    ("missing_bank_record",0.06),
    ("missing_gateway_record", 0.03),   # bank has it, gateway doesn't
    ("duplicate_retry",    0.03),
    ("lump_sum_member",    0.02),       # grouped separately, see below
    ("unresolvable",       0.01),
]

FEE_PCT = 0.02        # 2% gateway fee
GST_PCT = 0.18        # 18% GST on the fee


def rand_utr():
    return "UTR" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def garble(utr: str) -> str:
    variants = [
        utr.lower(),
        f" {utr} ",
        utr[:-2],                       # truncated
        utr.replace("UTR", "utr", 1),
    ]
    return random.choice(variants)


def weighted_scenario():
    r = random.random()
    acc = 0.0
    for name, w in SCENARIO_WEIGHTS:
        acc += w
        if r <= acc:
            return name
    return SCENARIO_WEIGHTS[-1][0]


def gen_row(i: int, period: str, base_date: datetime):
    payment_id = f"pay_{period.replace('-', '')}_{i:05d}"
    order_id = f"order_{period.replace('-', '')}_{i:05d}"
    amount = round(random.uniform(200, 15000), 2)
    utr = rand_utr()
    created_at = base_date + timedelta(
        hours=random.randint(0, 23 * 28), minutes=random.randint(0, 59)
    )

    scenario = weighted_scenario()
    gateway = {
        "payment_id": payment_id,
        "order_id": order_id,
        "amount": amount,
        "status": "captured",
        "utr": utr,
        "created_at": created_at,
        "period": period,
        "scenario": scenario,
        "expected_result": "match",
    }
    bank = None  # (utr, amount, credited_at, narration, linked_payment_ids)

    if scenario == "clean_exact":
        bank = (utr, amount, created_at + timedelta(hours=2), "NEFT credit", payment_id)

    elif scenario == "fee_delta":
        fee = round(amount * FEE_PCT, 2)
        gst = round(fee * GST_PCT, 2)
        net = round(amount - fee - gst, 2)
        bank = (utr, net, created_at + timedelta(hours=3), "Settlement net of fees", payment_id)

    elif scenario == "settlement_delay":
        bank = (utr, amount, created_at + timedelta(days=random.randint(2, 4)), "Delayed settlement", payment_id)

    elif scenario == "garbled_utr":
        bank = (garble(utr), amount, created_at + timedelta(hours=2), "NEFT credit", payment_id)

    elif scenario == "missing_bank_record":
        gateway["expected_result"] = "exception"
        bank = None

    elif scenario == "missing_gateway_record":
        # bank has a credit with no corresponding gateway row at all.
        # We still emit a gateway row (so ids stay simple) but mark it
        # as a row the *matcher* should treat as if it were absent by
        # giving the bank record an unrelated UTR/amount instead.
        gateway["expected_result"] = "exception"
        bank = (rand_utr(), round(random.uniform(200, 15000), 2),
                 created_at + timedelta(hours=2), "Unmatched inbound credit", None)

    elif scenario == "duplicate_retry":
        gateway["expected_result"] = "match"
        bank = (utr, amount, created_at + timedelta(hours=2), "NEFT credit", payment_id)
        # the retry row itself is appended separately by caller

    elif scenario == "lump_sum_member":
        gateway["expected_result"] = "match"
        bank = None  # handled in batches by gen_lump_sum_group()

    elif scenario == "unresolvable":
        gateway["expected_result"] = "exception"
        bank = None

    return gateway, bank


def gen_lump_sum_group(start_i: int, period: str, base_date: datetime, n_members=5, n_held_back=1):
    """One bank lump-sum credit covering several gateway payments,
    minus a couple held back (rolling reserve / pending refund)."""
    members = []
    total = 0.0
    credited_at = base_date + timedelta(hours=random.randint(0, 23 * 28))
    for j in range(n_members):
        amount = round(random.uniform(200, 5000), 2)
        payment_id = f"pay_{period.replace('-', '')}_ls{start_i}_{j:02d}"
        gw = {
            "payment_id": payment_id,
            "order_id": f"order_{period.replace('-', '')}_ls{start_i}_{j:02d}",
            "amount": amount,
            "status": "captured",
            "utr": None,   # lump-sum members have no individual UTR
            "created_at": credited_at - timedelta(hours=random.randint(1, 20)),
            "period": period,
            "scenario": "lump_sum_member",
            "expected_result": "match" if j < n_members - n_held_back else "exception",
        }
        members.append(gw)
        if j < n_members - n_held_back:
            total += amount

    lump_utr = rand_utr()
    linked = ",".join(g["payment_id"] for g in members[: n_members - n_held_back])
    bank_row = (lump_utr, round(total, 2), credited_at, "Bulk settlement payout", linked)
    for g in members:
        g["utr"] = lump_utr  # shared reference; matcher must unbundle, not exact-match
    return members, bank_row


def insert_rows(conn, gateway_rows, bank_rows):
    with conn.cursor() as cur:
        for g in gateway_rows:
            cur.execute(
                """INSERT INTO gateway_records
                   (payment_id, order_id, amount, status, utr, created_at,
                    period, scenario, expected_result)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (g["payment_id"], g["order_id"], g["amount"], g["status"], g["utr"],
                 g["created_at"], g["period"], g["scenario"], g["expected_result"]),
            )
        for b in bank_rows:
            if b is None:
                continue
            utr, amount, credited_at, narration, linked = b
            cur.execute(
                """INSERT INTO bank_records
                   (utr, amount, credited_at, narration, period, linked_payment_ids)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (utr, amount, credited_at, narration, g_period_for(bank_rows, b), linked),
            )
    conn.commit()


def g_period_for(bank_rows, b):
    # small helper since bank rows don't carry period directly above
    return CURRENT_PERIOD


def generate_baseline(conn, total_rows: int, period: str):
    global CURRENT_PERIOD
    CURRENT_PERIOD = period
    base_date = datetime(int(period.split("-")[0]), int(period.split("-")[1]), 1)

    gateway_rows, bank_rows = [], []
    n_lump_groups = max(1, total_rows // 100)  # a few lump-sum groups per ~100 rows
    remaining = total_rows

    i = 1
    for _ in range(n_lump_groups):
        members, bank_row = gen_lump_sum_group(i, period, base_date)
        gateway_rows.extend(members)
        bank_rows.append(bank_row)
        i += len(members)
        remaining -= len(members)

    while remaining > 0:
        gw, bank = gen_row(i, period, base_date)
        gateway_rows.append(gw)
        bank_rows.append(bank)
        if gw["scenario"] == "duplicate_retry":
            # append a second, near-identical row to simulate a retry
            retry = dict(gw)
            retry["payment_id"] = gw["payment_id"] + "_retry"
            retry["created_at"] = gw["created_at"] + timedelta(minutes=5)
            gateway_rows.append(retry)
            remaining -= 1
        i += 1
        remaining -= 1

    insert_rows(conn, gateway_rows, bank_rows)
    print(f"Inserted {len(gateway_rows)} gateway rows / {len([b for b in bank_rows if b])} bank rows for {period}")


def trickle(conn, period: str, interval: int):
    base_date = datetime.now()
    i = 100000
    print(f"Trickling new rows into {period} every {interval}s — Ctrl+C to stop")
    while True:
        time.sleep(interval)
        n = random.choice([1, 1, 2])
        gateway_rows, bank_rows = [], []
        for _ in range(n):
            gw, bank = gen_row(i, period, base_date)
            gateway_rows.append(gw)
            bank_rows.append(bank)
            i += 1
        global CURRENT_PERIOD
        CURRENT_PERIOD = period
        insert_rows(conn, gateway_rows, bank_rows)
        print(f"[{datetime.now().isoformat(timespec='seconds')}] +{n} row(s) added to {period}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=int, help="number of baseline rows to generate")
    ap.add_argument("--period", type=str, default="2026-05")
    ap.add_argument("--trickle", action="store_true", help="run the periodic trickle loop")
    ap.add_argument("--interval", type=int, default=5, help="seconds between trickle inserts")
    args = ap.parse_args()

    conn = get_connection()
    try:
        if args.baseline:
            generate_baseline(conn, args.baseline, args.period)
        if args.trickle:
            trickle(conn, args.period, args.interval)
    finally:
        conn.close()
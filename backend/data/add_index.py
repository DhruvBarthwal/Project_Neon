from reconciler.main import get_connection

conn = get_connection()
with conn.cursor() as cur:
    cur.execute("CREATE INDEX idx_exceptions_period_payment ON exceptions(period, payment_id);")
conn.commit()
conn.close()
print("Index created.")
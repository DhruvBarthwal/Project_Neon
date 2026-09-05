DROP TABLE IF EXISTS reconciliation_runs CASCADE;
DROP TABLE IF EXISTS merchant_records CASCADE;
DROP TABLE IF EXISTS exceptions CASCADE;
DROP TABLE IF EXISTS ledger_matches CASCADE;
DROP TABLE IF EXISTS bank_records CASCADE;
DROP TABLE IF EXISTS gateway_records CASCADE;

-- Source A: what the payment gateway / internal ledger says happened
CREATE TABLE gateway_records (
    id              SERIAL PRIMARY KEY,
    payment_id      TEXT NOT NULL,
    order_id        TEXT,
    amount          NUMERIC(12,2) NOT NULL,
    status          TEXT NOT NULL,              -- captured / failed / refunded
    utr             TEXT,                       -- bank reference, sometimes missing/garbled
    created_at      TIMESTAMP NOT NULL,
    period          TEXT NOT NULL,               -- '2026-05'
    -- hidden ground truth, used only for scoring — never read by the matcher
    scenario        TEXT NOT NULL,
    expected_result TEXT NOT NULL,               -- 'match' | 'exception'
    inserted_at     TIMESTAMP NOT NULL DEFAULT now()
);

-- Source B: what the bank statement shows
CREATE TABLE bank_records (
    id              SERIAL PRIMARY KEY,
    utr             TEXT,
    amount          NUMERIC(12,2) NOT NULL,
    credited_at     TIMESTAMP NOT NULL,
    narration       TEXT,
    period          TEXT NOT NULL,
    linked_payment_ids TEXT,
    inserted_at     TIMESTAMP NOT NULL DEFAULT now()
);

-- Result: everything that matched, however it matched
CREATE TABLE ledger_matches (
    id              SERIAL PRIMARY KEY,
    payment_id      TEXT NOT NULL,
    period          TEXT NOT NULL,
    match_type      TEXT NOT NULL,     -- exact | fuzzy | lump_sum | fee_aware
    matched_amount  NUMERIC(12,2),
    bank_amount     NUMERIC(12,2),
    risk            TEXT NOT NULL DEFAULT 'low',   -- low | medium | high | critical
    explanation     TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (payment_id, period)
);


CREATE TABLE exceptions (
    id                  SERIAL PRIMARY KEY,
    payment_id          TEXT,
    period              TEXT NOT NULL,
    reason_code         TEXT NOT NULL,   -- e.g. no_corresponding_bank_record
    reason_detail       TEXT,
    recommended_action  TEXT,
    risk                TEXT NOT NULL DEFAULT 'high',   -- low | medium | high | critical
    amount              NUMERIC(12,2),
    created_at          TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (payment_id, period)
);


CREATE TABLE reconciliation_runs (
    id              SERIAL PRIMARY KEY,
    period          TEXT NOT NULL,
    triggered_by    TEXT,               -- agent identity's `sub` claim, or 'auto' for the Q&A auto-run
    trigger_source  TEXT NOT NULL DEFAULT 'manual',  -- 'manual' | 'auto_qa'
    total_records   INTEGER NOT NULL,
    matched_count   INTEGER NOT NULL,
    exception_count INTEGER NOT NULL,
    match_rate      NUMERIC(5,2) NOT NULL,
    run_at          TIMESTAMP NOT NULL DEFAULT now()
);


CREATE TABLE merchant_records (
    id              SERIAL PRIMARY KEY,
    order_id        TEXT NOT NULL,
    payment_id      TEXT,               -- null if the merchant never received a webhook linking it
    amount          NUMERIC(12,2) NOT NULL,
    status          TEXT NOT NULL,       -- 'paid' | 'pending' | 'failed' 
    marked_paid_at  TIMESTAMP,
    period          TEXT NOT NULL,

    scenario        TEXT NOT NULL,
    inserted_at     TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_merchant_period ON merchant_records(period);
CREATE INDEX idx_merchant_order ON merchant_records(order_id);

CREATE INDEX idx_gateway_period ON gateway_records(period);
CREATE INDEX idx_bank_period ON bank_records(period);
CREATE INDEX idx_ledger_period ON ledger_matches(period);
CREATE INDEX idx_exceptions_period ON exceptions(period);
CREATE INDEX idx_exceptions_period_payment ON exceptions(period, payment_id);
CREATE INDEX idx_runs_period ON reconciliation_runs(period);
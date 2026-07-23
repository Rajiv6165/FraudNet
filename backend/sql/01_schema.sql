-- =========================================================================
-- FRAUDNET BASE SCHEMA DDL
-- =========================================================================

-- Enable uuid-ossp extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    home_country VARCHAR(3) NOT NULL,
    risk_tier VARCHAR(20) DEFAULT 'low' NOT NULL
);

-- Index user queries
CREATE INDEX IF NOT EXISTS idx_users_id ON users(id);

-- 2. Devices Table
CREATE TABLE IF NOT EXISTS devices (
    id VARCHAR(50) PRIMARY KEY,
    fingerprint VARCHAR(255) UNIQUE NOT NULL,
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_devices_fingerprint ON devices(fingerprint);

-- 3. Cards Table
CREATE TABLE IF NOT EXISTS cards (
    id SERIAL PRIMARY KEY,
    last_four VARCHAR(4) NOT NULL,
    issuer VARCHAR(50) NOT NULL,
    user_id INT NOT NULL,
    CONSTRAINT fk_cards_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cards_id ON cards(id);
CREATE INDEX IF NOT EXISTS idx_cards_last_four ON cards(last_four);

-- 4. Partitioned Transactions Table (Declarative RANGE Partitioning by Month)
CREATE TABLE IF NOT EXISTS transactions (
    id UUID DEFAULT gen_random_uuid(),
    user_id INT NOT NULL,
    card_id INT NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    merchant VARCHAR(100) NOT NULL,
    merchant_category VARCHAR(50) NOT NULL,
    country VARCHAR(3) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    status VARCHAR(20) DEFAULT 'approved' NOT NULL,
    
    PRIMARY KEY (id, created_at),
    CONSTRAINT fk_transactions_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_transactions_card_id FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
    CONSTRAINT fk_transactions_device_id FOREIGN KEY (device_id) REFERENCES devices(id)
) PARTITION BY RANGE (created_at);

-- Monthly Range Partitions
CREATE TABLE IF NOT EXISTS transactions_2026_05 PARTITION OF transactions
    FOR VALUES FROM ('2026-05-01 00:00:00+00') TO ('2026-06-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS transactions_2026_06 PARTITION OF transactions
    FOR VALUES FROM ('2026-06-01 00:00:00+00') TO ('2026-07-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS transactions_2026_07 PARTITION OF transactions
    FOR VALUES FROM ('2026-07-01 00:00:00+00') TO ('2026-08-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS transactions_2026_08 PARTITION OF transactions
    FOR VALUES FROM ('2026-08-01 00:00:00+00') TO ('2026-09-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS transactions_2026_09 PARTITION OF transactions
    FOR VALUES FROM ('2026-09-01 00:00:00+00') TO ('2026-10-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS transactions_2026_10 PARTITION OF transactions
    FOR VALUES FROM ('2026-10-01 00:00:00+00') TO ('2026-11-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS transactions_2026_11 PARTITION OF transactions
    FOR VALUES FROM ('2026-11-01 00:00:00+00') TO ('2026-12-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS transactions_2026_12 PARTITION OF transactions
    FOR VALUES FROM ('2026-12-01 00:00:00+00') TO ('2027-01-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS transactions_default PARTITION OF transactions DEFAULT;

-- Crucial indexes for performance of window functions and recursive CTE searches
CREATE INDEX IF NOT EXISTS idx_transactions_user_id_created_at ON transactions(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_transactions_device_id ON transactions(device_id);
CREATE INDEX IF NOT EXISTS idx_transactions_ip_address ON transactions(ip_address);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);

-- 5. Fraud Scores Table
CREATE TABLE IF NOT EXISTS fraud_scores (
    transaction_id UUID PRIMARY KEY,
    velocity_score NUMERIC(5, 2) DEFAULT 0.00 NOT NULL,
    deviation_score NUMERIC(5, 2) DEFAULT 0.00 NOT NULL,
    ring_score NUMERIC(5, 2) DEFAULT 0.00 NOT NULL,
    composite_score NUMERIC(5, 2) DEFAULT 0.00 NOT NULL,
    flagged BOOLEAN DEFAULT FALSE NOT NULL,
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fraud_scores_flagged ON fraud_scores(flagged);


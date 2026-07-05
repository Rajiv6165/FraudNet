# FraudNet — Core SQL-Native Reasoning Reference

This document highlights the PL/pgSQL routines running natively inside the database. These files are located in the [sql/](file:///c:/Users/rajiv/OneDrive/Desktop/Projects/Main%20Projects/FraudNet/backend/sql/) directory.

---

## 1. Trigger Binding
Every transaction inserted fires `process_transaction_fraud_scores()` in [03_triggers.sql](file:///c:/Users/rajiv/OneDrive/Desktop/Projects/Main%20Projects/FraudNet/backend/sql/03_triggers.sql) immediately before commit:

```sql
CREATE TRIGGER trg_process_transaction_fraud_scores
AFTER INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION process_transaction_fraud_scores();
```

---

## 2. Velocity Scoring
Calculated in [02_fraud_functions.sql](file:///c:/Users/rajiv/OneDrive/Desktop/Projects/Main%20Projects/FraudNet/backend/sql/02_fraud_functions.sql#L10), the velocity score aggregates transactions inside rolling 10-minute, 1-hour, and 24-hour windows:

```sql
SELECT COUNT(*), COALESCE(SUM(amount), 0.0)
INTO v_cnt_10m, v_sum_10m
FROM transactions
WHERE user_id = v_user_id 
  AND created_at BETWEEN v_tx_created_at - INTERVAL '10 minutes' AND v_tx_created_at;
```

It compares the current window activity against the user's historical average:
```sql
SELECT COALESCE(AVG(amount), 100.0) INTO v_avg_historical_amount
FROM transactions
WHERE user_id = v_user_id AND id != p_tx_id;
```

---

## 3. Z-Score Deviation & Novelty Analysis
Calculated in [02_fraud_functions.sql](file:///c:/Users/rajiv/OneDrive/Desktop/Projects/Main%20Projects/FraudNet/backend/sql/02_fraud_functions.sql#L83), this computes standard deviation of transaction amount for the user and checks for novel categories/countries:

```sql
SELECT COALESCE(AVG(amount), 0.0), COALESCE(STDDEV(amount), 0.0)
INTO v_avg_amount, v_stddev_amount
FROM transactions
WHERE user_id = v_user_id AND id != p_tx_id;
```

Novel country checking flags transactions occurring outside home countries if they've never been used before:
```sql
SELECT NOT EXISTS (
    SELECT 1 FROM transactions 
    WHERE user_id = v_user_id AND country = v_tx_country AND id != p_tx_id
) AND v_tx_country != v_home_country INTO v_is_novel_country;
```

---

## 4. Localized vs. Global Fraud Ring CTE
* **Global Ring Scan**: Used by `GET /rings` to find all clusters in the database: [02_fraud_functions.sql: detect_fraud_rings()](file:///c:/Users/rajiv/OneDrive/Desktop/Projects/Main%20Projects/FraudNet/backend/sql/02_fraud_functions.sql#L150).
* **Localized Row Scan**: Used inside transaction triggers to evaluate risk *instantly* for a single user without scanning the entire database: [02_fraud_functions.sql: detect_user_fraud_ring()](file:///c:/Users/rajiv/OneDrive/Desktop/Projects/Main%20Projects/FraudNet/backend/sql/02_fraud_functions.sql#L215).

```sql
WITH RECURSIVE bidirectional_links AS (
    SELECT DISTINCT t1.user_id AS user_a, t2.user_id AS user_b
    FROM transactions t1
    JOIN transactions t2 ON t1.device_id = t2.device_id WHERE t1.user_id != t2.user_id
    UNION
    SELECT DISTINCT t1.user_id AS user_a, t2.user_id AS user_b
    FROM transactions t1
    JOIN transactions t2 ON t1.ip_address = t2.ip_address WHERE t1.user_id != t2.user_id
    UNION
    SELECT DISTINCT c1.user_id AS user_a, c2.user_id AS user_b
    FROM cards c1
    JOIN cards c2 ON c1.last_four = c2.last_four WHERE c1.user_id != c2.user_id
),
graph_search(current_user, path) AS (
    SELECT p_user_id, ARRAY[p_user_id]
    UNION ALL
    SELECT bl.user_b, gs.path || bl.user_b
    FROM graph_search gs
    JOIN bidirectional_links bl ON gs.current_user = bl.user_a
    WHERE NOT (bl.user_b = ANY(gs.path))
)
```

---

## 5. Live Dashboard Refreshes
Defined in [04_materialized_view.sql](file:///c:/Users/rajiv/OneDrive/Desktop/Projects/Main%20Projects/FraudNet/backend/sql/04_materialized_view.sql):
```sql
CREATE MATERIALIZED VIEW live_risk_dashboard AS
SELECT 
    t.merchant_category,
    t.country,
    DATE_TRUNC('hour', t.created_at) AS transaction_hour,
    COUNT(t.id) AS transaction_count,
    COUNT(CASE WHEN fs.flagged = TRUE THEN 1 END) AS flagged_count,
    SUM(t.amount) AS total_volume,
    ROUND(COALESCE(AVG(fs.composite_score), 0.0), 2) AS avg_risk_score
FROM transactions t
LEFT JOIN fraud_scores fs ON t.id = fs.transaction_id
GROUP BY t.merchant_category, t.country, DATE_TRUNC('hour', t.created_at);
```
To enable `CONCURRENT` updates (non-blocking reads), we maintain a unique index:
```sql
CREATE UNIQUE INDEX idx_live_risk_dashboard_unique 
ON live_risk_dashboard (merchant_category, country, transaction_hour);
```

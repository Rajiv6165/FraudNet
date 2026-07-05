-- =========================================================================
-- FRAUDNET MATERIALIZED VIEWS
-- =========================================================================

-- -------------------------------------------------------------------------
-- live_risk_dashboard
-- Aggregates total counts, flagged count, total volume, and average risk
-- grouped by merchant category, country, and hour.
-- -------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS live_risk_dashboard;

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

-- A unique index is REQUIRED to perform REFRESH MATERIALIZED VIEW CONCURRENTLY
CREATE UNIQUE INDEX idx_live_risk_dashboard_unique 
ON live_risk_dashboard (merchant_category, country, transaction_hour);

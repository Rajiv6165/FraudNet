-- =========================================================================
-- FRAUDNET TRIGGER ACTIONS
-- =========================================================================

-- -------------------------------------------------------------------------
-- AFTER INSERT ON transactions
-- Computes the three risk dimensions, aggregates them into a composite risk,
-- inserts a fraud score row, and publishes a JSON payload via LISTEN/NOTIFY.
-- -------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION process_transaction_fraud_scores()
RETURNS TRIGGER AS $$
DECLARE
    v_velocity_score NUMERIC(5, 2);
    v_deviation_score NUMERIC(5, 2);
    v_ring_score NUMERIC(5, 2) := 0.0;
    v_composite_score NUMERIC(5, 2);
    
    v_ring_id VARCHAR;
    v_ring_size INT;
    v_ring_volume NUMERIC;
    
    v_flagged BOOLEAN := FALSE;
    v_notify_payload JSON;
BEGIN
    -- 1. Compute Velocity Score
    v_velocity_score := calculate_velocity_score(NEW.id);

    -- 2. Compute Behavioral Deviation Score
    v_deviation_score := calculate_deviation_score(NEW.id);

    -- 3. Query Localized Fraud Ring Membership
    SELECT ring_id, ring_size, ring_volume
    INTO v_ring_id, v_ring_size, v_ring_volume
    FROM detect_user_fraud_ring(NEW.user_id);

    -- Normalize ring score (ring membership is a strong baseline signal)
    -- Scaling: size 2 = 0.70, size 3 = 0.80, size 4 = 0.90, size 5+ = 1.00
    IF v_ring_size IS NOT NULL AND v_ring_size >= 2 THEN
        v_ring_score := LEAST(1.00, 0.70 + ((v_ring_size - 2)::NUMERIC * 0.10));
    ELSE
        v_ring_score := 0.00;
    END IF;

    -- 4. Calculate Weighted Composite Score
    v_composite_score := (v_velocity_score * 0.3) 
                         + (v_deviation_score * 0.4) 
                         + (v_ring_score * 0.3);
    v_composite_score := ROUND(v_composite_score, 2);

    -- 5. Flag Transaction if Threshold Exceeded
    IF v_composite_score >= 0.75 THEN
        v_flagged := TRUE;
    END IF;

    -- 6. Insert Into fraud_scores
    INSERT INTO fraud_scores (
        transaction_id,
        velocity_score,
        deviation_score,
        ring_score,
        composite_score,
        flagged,
        computed_at
    ) VALUES (
        NEW.id,
        v_velocity_score,
        v_deviation_score,
        v_ring_score,
        v_composite_score,
        v_flagged,
        NOW()
    );

    -- 7. Build Notification Payload (JSON format) containing transaction & score details
    -- This allows FastAPI to forward details immediately without doing a subsequent SELECT.
    v_notify_payload := json_build_object(
        'transaction_id', NEW.id,
        'user_id', NEW.user_id,
        'user_name', (SELECT name FROM users WHERE id = NEW.user_id),
        'amount', NEW.amount,
        'merchant', NEW.merchant,
        'merchant_category', NEW.merchant_category,
        'country', NEW.country,
        'created_at', NEW.created_at,
        'device_id', NEW.device_id,
        'ip_address', NEW.ip_address,
        'velocity_score', v_velocity_score,
        'deviation_score', v_deviation_score,
        'ring_score', v_ring_score,
        'composite_score', v_composite_score,
        'flagged', v_flagged
    );

    -- Notify listeners (FastAPI WebSockets) on 'transaction_flagged' channel
    PERFORM pg_notify('transaction_flagged', v_notify_payload::text);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Bind the trigger
-- Ensure to drop the trigger first if it exists to make this script idempotent
DROP TRIGGER IF EXISTS trg_process_transaction_fraud_scores ON transactions;

CREATE TRIGGER trg_process_transaction_fraud_scores
AFTER INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION process_transaction_fraud_scores();

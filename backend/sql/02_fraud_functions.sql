-- =========================================================================
-- FRAUDNET CORE DETECTION FUNCTIONS
-- =========================================================================

-- -------------------------------------------------------------------------
-- 1. VELOCITY SCORING FUNCTION
-- Computes short-term transaction count and volume anomalies compared to
-- the user's historical daily baselines.
-- -------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION calculate_velocity_score(p_tx_id UUID)
RETURNS NUMERIC AS $$
DECLARE
    v_user_id INT;
    v_tx_amount NUMERIC;
    v_tx_created_at TIMESTAMP WITH TIME ZONE;
    
    v_cnt_10m INT;
    v_cnt_1h INT;
    v_cnt_24h INT;
    
    v_sum_10m NUMERIC;
    v_sum_1h NUMERIC;
    v_sum_24h NUMERIC;
    
    v_avg_daily_count NUMERIC;
    v_avg_historical_amount NUMERIC;
    
    v_freq_factor NUMERIC;
    v_vol_factor NUMERIC;
    v_velocity_score NUMERIC;
BEGIN
    -- Get current transaction details
    SELECT user_id, amount, created_at
    INTO v_user_id, v_tx_amount, v_tx_created_at
    FROM transactions
    WHERE id = p_tx_id;

    IF v_user_id IS NULL THEN
        RETURN 0.0;
    END IF;

    -- Compute transaction counts & sums in rolling windows ending at the current transaction
    SELECT 
        COUNT(*),
        COALESCE(SUM(amount), 0.0)
    INTO v_cnt_10m, v_sum_10m
    FROM transactions
    WHERE user_id = v_user_id 
      AND created_at BETWEEN v_tx_created_at - INTERVAL '10 minutes' AND v_tx_created_at;

    SELECT 
        COUNT(*),
        COALESCE(SUM(amount), 0.0)
    INTO v_cnt_1h, v_sum_1h
    FROM transactions
    WHERE user_id = v_user_id 
      AND created_at BETWEEN v_tx_created_at - INTERVAL '1 hour' AND v_tx_created_at;

    SELECT 
        COUNT(*),
        COALESCE(SUM(amount), 0.0)
    INTO v_cnt_24h, v_sum_24h
    FROM transactions
    WHERE user_id = v_user_id 
      AND created_at BETWEEN v_tx_created_at - INTERVAL '24 hours' AND v_tx_created_at;

    -- Compute user historical baselines
    -- Average transaction amount for this user (prior to this transaction)
    SELECT COALESCE(AVG(amount), 100.0)
    INTO v_avg_historical_amount
    FROM transactions
    WHERE user_id = v_user_id AND id != p_tx_id;

    -- Average daily transaction count for this user
    SELECT COALESCE(COUNT(*)::NUMERIC / GREATEST(1.0, EXTRACT(epoch FROM (v_tx_created_at - MIN(created_at))) / 86400.0), 1.0)
    INTO v_avg_daily_count
    FROM transactions
    WHERE user_id = v_user_id;

    -- Calculate frequency deviation:
    -- If daily avg is 2 transactions, then 10 in 1 hour is a major anomaly.
    -- We normalize frequency factor where > 5 transactions in 10 mins or > 10 in 1 hour heavily weights the score.
    v_freq_factor := (v_cnt_10m::NUMERIC / 4.0) + (v_cnt_1h::NUMERIC / 10.0) + (v_cnt_24h::NUMERIC / GREATEST(v_avg_daily_count * 3.0, 15.0));

    -- Calculate volume deviation:
    -- Compare current 1-hour sum with user's historical average amount
    v_vol_factor := v_sum_1h / (v_avg_historical_amount * 5.0);

    -- Combine and clamp between 0.0 and 1.0
    v_velocity_score := LEAST(1.0, GREATEST(0.0, (v_freq_factor * 0.6) + (v_vol_factor * 0.4)));

    RETURN ROUND(v_velocity_score, 2);
END;
$$ LANGUAGE plpgsql;


-- -------------------------------------------------------------------------
-- 2. BEHAVIORAL DEVIATION SCORING FUNCTION
-- Scores a transaction based on Z-score deviation from the user's historical
-- amount baseline and flags novel transactions in category or country.
-- -------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION calculate_deviation_score(p_tx_id UUID)
RETURNS NUMERIC AS $$
DECLARE
    v_user_id INT;
    v_tx_amount NUMERIC;
    v_tx_category VARCHAR;
    v_tx_country VARCHAR;
    
    v_home_country VARCHAR;
    v_avg_amount NUMERIC;
    v_stddev_amount NUMERIC;
    v_z_score NUMERIC;
    
    v_is_novel_country BOOLEAN;
    v_is_novel_category BOOLEAN;
    
    v_amount_deviation_score NUMERIC;
    v_deviation_score NUMERIC;
BEGIN
    -- Retrieve transaction info
    SELECT user_id, amount, merchant_category, country
    INTO v_user_id, v_tx_amount, v_tx_category, v_tx_country
    FROM transactions
    WHERE id = p_tx_id;

    IF v_user_id IS NULL THEN
        RETURN 0.0;
    END IF;

    -- Fetch user home country
    SELECT home_country INTO v_home_country FROM users WHERE id = v_user_id;

    -- Calculate historical stats for the user (excluding current transaction)
    SELECT 
        COALESCE(AVG(amount), 0.0),
        COALESCE(STDDEV(amount), 0.0)
    INTO v_avg_amount, v_stddev_amount
    FROM transactions
    WHERE user_id = v_user_id AND id != p_tx_id;

    -- Standard deviation (Z-score) calculation
    IF v_stddev_amount = 0.0 THEN
        -- If no stddev (e.g. only 1 transaction before), compare directly to average
        v_z_score := CASE WHEN v_avg_amount > 0.0 THEN ABS(v_tx_amount - v_avg_amount) / v_avg_amount ELSE 0.0 END;
    ELSE
        v_z_score := ABS(v_tx_amount - v_avg_amount) / v_stddev_amount;
    END IF;

    -- Normalize amount deviation (Z-score >= 3.0 results in 1.0 score)
    v_amount_deviation_score := LEAST(1.0, v_z_score / 3.0);

    -- Identify novel country usage (never seen before for this user and doesn't match home country)
    SELECT NOT EXISTS (
        SELECT 1 FROM transactions 
        WHERE user_id = v_user_id AND country = v_tx_country AND id != p_tx_id
    ) AND v_tx_country != v_home_country
    INTO v_is_novel_country;

    -- Identify novel merchant category usage
    SELECT NOT EXISTS (
        SELECT 1 FROM transactions 
        WHERE user_id = v_user_id AND merchant_category = v_tx_category AND id != p_tx_id
    )
    INTO v_is_novel_category;

    -- Calculate composite deviation score
    -- Base weight: 50% amount Z-score, 30% novel country, 20% novel merchant category
    v_deviation_score := (v_amount_deviation_score * 0.5) 
                         + (CASE WHEN v_is_novel_country THEN 0.3 ELSE 0.0 END)
                         + (CASE WHEN v_is_novel_category THEN 0.2 ELSE 0.0 END);

    RETURN ROUND(v_deviation_score, 2);
END;
$$ LANGUAGE plpgsql;


-- -------------------------------------------------------------------------
-- 3. GLOBAL FRAUD RING DETECTION FUNCTION (Recursive CTE)
-- Walks the entire network of transactions and credit cards to trace all 
-- connected components (rings) of users sharing devices, IPs, or cards.
-- -------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION detect_fraud_rings()
RETURNS TABLE (
    ring_id VARCHAR,
    user_id INT,
    ring_size INT,
    ring_volume NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE bidirectional_links AS (
        -- Link 1: Users transacting on the exact same device ID
        SELECT DISTINCT t1.user_id AS user_a, t2.user_id AS user_b
        FROM transactions t1
        JOIN transactions t2 ON t1.device_id = t2.device_id
        WHERE t1.user_id != t2.user_id

        UNION

        -- Link 2: Users transacting from the exact same IP address
        SELECT DISTINCT t1.user_id AS user_a, t2.user_id AS user_b
        FROM transactions t1
        JOIN transactions t2 ON t1.ip_address = t2.ip_address
        WHERE t1.user_id != t2.user_id

        UNION

        -- Link 3: Users using credit cards with the same last 4 digits
        SELECT DISTINCT c1.user_id AS user_a, c2.user_id AS user_b
        FROM cards c1
        JOIN cards c2 ON c1.last_four = c2.last_four
        WHERE c1.user_id != c2.user_id
    ),
    graph_search(start_user, curr_user) AS (
        -- Base Case: Seed recursion with all users who have at least one link
        SELECT DISTINCT user_a, user_a
        FROM bidirectional_links

        UNION

        -- Recursive Step: Traverse to unvisited neighbors to build connected component
        SELECT gs.start_user, bl.user_b
        FROM graph_search gs
        JOIN bidirectional_links bl ON gs.curr_user = bl.user_a
    ),
    user_components AS (
        -- Group by starting user to aggregate all nodes reachable from them
        SELECT 
            start_user,
            MIN(curr_user) AS min_member_id, -- Represents the unique ring identifier
            ARRAY_AGG(DISTINCT curr_user) AS members
        FROM graph_search
        GROUP BY start_user
    ),
    unique_rings AS (
        -- Deduplicate components since user A->B and B->A resolve to the same members array
        SELECT DISTINCT
            min_member_id,
            members
        FROM user_components
    ),
    ring_metrics AS (
        -- Compute sizing and historical total spend across the members of each ring
        SELECT 
            ur.min_member_id,
            cardinality(ur.members) AS r_size,
            ur.members,
            COALESCE((
                SELECT SUM(amount) FROM transactions 
                WHERE transactions.user_id = ANY(ur.members)
            ), 0.0) AS r_volume
        FROM unique_rings ur
        WHERE cardinality(ur.members) >= 2 -- A fraud ring must have at least 2 connected users
    )
    SELECT 
        ('ring_' || rm.min_member_id)::VARCHAR AS ring_id,
        u.id AS user_id,
        rm.r_size AS ring_size,
        rm.r_volume AS ring_volume
    FROM ring_metrics rm
    -- Unnest the members array to return a row per user inside a fraud ring
    JOIN users u ON u.id = ANY(rm.members)
    ORDER BY ring_id, user_id;
END;
$$ LANGUAGE plpgsql;


-- -------------------------------------------------------------------------
-- 4. LOCALIZED USER FRAUD RING QUERY (Recursive CTE)
-- Optimized graph search starting only from a specific user, returning their 
-- ring size, volume and ID. Used within triggers for latency efficiency.
-- -------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION detect_user_fraud_ring(p_user_id INT)
RETURNS TABLE (
    ring_id VARCHAR,
    ring_size INT,
    ring_volume NUMERIC
) AS $$
DECLARE
    v_members INT[];
    v_min_member INT;
    v_size INT;
    v_volume NUMERIC;
BEGIN
    -- Recursive CTE to traverse graph starting ONLY from p_user_id
    WITH RECURSIVE bidirectional_links AS (
        -- Shared device ID
        SELECT DISTINCT t1.user_id AS user_a, t2.user_id AS user_b
        FROM transactions t1
        JOIN transactions t2 ON t1.device_id = t2.device_id
        WHERE t1.user_id != t2.user_id

        UNION

        -- Shared IP
        SELECT DISTINCT t1.user_id AS user_a, t2.user_id AS user_b
        FROM transactions t1
        JOIN transactions t2 ON t1.ip_address = t2.ip_address
        WHERE t1.user_id != t2.user_id

        UNION

        -- Shared Card Last 4
        SELECT DISTINCT c1.user_id AS user_a, c2.user_id AS user_b
        FROM cards c1
        JOIN cards c2 ON c1.last_four = c2.last_four
        WHERE c1.user_id != c2.user_id
    ),
    graph_search(curr_user) AS (
        -- Base Case: Start only at the target user
        SELECT p_user_id

        UNION

        -- Recursive Step: Find neighbors of visited nodes
        SELECT bl.user_b
        FROM graph_search gs
        JOIN bidirectional_links bl ON gs.curr_user = bl.user_a
    )
    SELECT 
        ARRAY_AGG(DISTINCT curr_user)
    INTO v_members
    FROM graph_search;

    v_size := cardinality(v_members);

    -- If the component only contains the user, they aren't part of any shared fraud ring.
    IF v_size <= 1 OR v_members IS NULL THEN
        RETURN NEXT; -- Returns NULL row fields
        RETURN;
    END IF;

    -- Determine min member ID for stable ring identifier
    SELECT MIN(val) INTO v_min_member FROM unnest(v_members) AS val;

    -- Calculate total transaction volume inside this ring
    SELECT COALESCE(SUM(amount), 0.0) INTO v_volume 
    FROM transactions 
    WHERE user_id = ANY(v_members);

    ring_id := 'ring_' || v_min_member;
    ring_size := v_size;
    ring_volume := v_volume;
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

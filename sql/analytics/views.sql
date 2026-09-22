-- ============================================================================
-- Analytical SQL Views: Core Business & Reliability Questions
-- Compatible with DuckDB, PostgreSQL, and AWS Athena
-- ============================================================================

-- View 1: SLA Breach Rates and Failure Volumetrics by Service Category
CREATE VIEW IF NOT EXISTS vw_service_reliability_summary AS
WITH service_metrics AS (
    SELECT
        s.service_id,
        s.service_name,
        s.service_category,
        s.tier_level,
        COUNT(e.event_id) AS total_events,
        SUM(CASE WHEN e.status_code >= 500 THEN 1 ELSE 0 END) AS error_event_count,
        ROUND(AVG(e.duration_ms), 2) AS avg_duration_ms,
        MAX(e.duration_ms) AS max_duration_ms
    FROM dim_service s
    LEFT JOIN fact_operational_event e ON s.service_id = e.service_id
    GROUP BY s.service_id, s.service_name, s.service_category, s.tier_level
)
SELECT
    service_id,
    service_name,
    service_category,
    tier_level,
    total_events,
    error_event_count,
    ROUND(CAST(error_event_count AS FLOAT) / NULLIF(total_events, 0) * 100.0, 2) AS error_rate_pct,
    avg_duration_ms,
    max_duration_ms
FROM service_metrics;

-- View 2: Location Bottleneck Analysis using Window Functions
CREATE VIEW IF NOT EXISTS vw_location_bottlenecks AS
WITH location_stats AS (
    SELECT
        l.location_id,
        l.region,
        l.country,
        COUNT(e.event_id) AS event_volume,
        SUM(CASE WHEN e.status_code >= 500 THEN 1 ELSE 0 END) AS server_errors,
        AVG(e.duration_ms) AS avg_latency
    FROM dim_location l
    JOIN fact_operational_event e ON l.location_id = e.location_id
    GROUP BY l.location_id, l.region, l.country
)
SELECT
    location_id,
    region,
    country,
    event_volume,
    server_errors,
    ROUND(CAST(server_errors AS FLOAT) / NULLIF(event_volume, 0) * 100.0, 2) AS error_rate_pct,
    ROUND(avg_latency, 2) AS avg_latency_ms,
    DENSE_RANK() OVER (ORDER BY server_errors DESC) AS failure_rank
FROM location_stats;

-- View 3: Customer Tier Incident Exposure
CREATE VIEW IF NOT EXISTS vw_customer_tier_exposure AS
SELECT
    c.tier AS customer_tier,
    c.contract_sla_tier,
    COUNT(DISTINCT c.customer_id) AS customer_count,
    COUNT(e.event_id) AS total_incident_events,
    SUM(CASE WHEN e.status_code >= 500 THEN 1 ELSE 0 END) AS critical_failures
FROM dim_customer c
LEFT JOIN fact_operational_event e ON c.customer_id = e.customer_id
GROUP BY c.tier, c.contract_sla_tier;

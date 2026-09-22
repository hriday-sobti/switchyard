-- ============================================================================
-- SWITCHYARD: ELT Dimensional Enrichment & Aggregation Transforms
-- Compatible with DuckDB, PostgreSQL, and AWS Athena
-- ============================================================================

-- Daily Operational Summary Aggregation
CREATE TABLE IF NOT EXISTS agg_daily_operational_summary AS
SELECT
    CAST(timestamp AS DATE) AS event_date,
    service_id,
    location_id,
    COUNT(event_id) AS total_events,
    SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) AS error_count,
    ROUND(AVG(duration_ms), 2) AS avg_duration_ms,
    ROUND(CAST(SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(event_id) * 100.0, 2) AS error_rate_pct
FROM fact_operational_event
GROUP BY CAST(timestamp AS DATE), service_id, location_id;

-- Customer Incident Exposure Profile
CREATE TABLE IF NOT EXISTS agg_customer_incident_profile AS
SELECT
    c.customer_id,
    c.customer_name,
    c.tier AS customer_tier,
    c.contract_sla_tier,
    COUNT(e.event_id) AS total_incident_events,
    SUM(CASE WHEN e.status_code >= 500 THEN 1 ELSE 0 END) AS critical_failures,
    MAX(e.timestamp) AS last_incident_time
FROM dim_customer c
JOIN fact_operational_event e ON c.customer_id = e.customer_id
WHERE e.status_code >= 400
GROUP BY c.customer_id, c.customer_name, c.tier, c.contract_sla_tier;

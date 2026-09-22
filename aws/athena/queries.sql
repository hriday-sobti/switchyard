-- ============================================================================
-- Amazon Athena Production Analytical Queries
-- Optimized for partition pruning and columnar scanning cost reduction
-- ============================================================================

-- Query 1: Partition-Pruned SLA Breach Rate over Date Boundary
-- Scanning cost optimization: Pruned on partition keys (year, month, day)
SELECT
    year,
    month,
    day,
    service_id,
    COUNT(*) AS total_events,
    SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) AS error_events,
    ROUND(CAST(SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) AS DOUBLE) / COUNT(*) * 100.0, 2) AS incident_rate_pct
FROM switchyard_analytics.fact_operational_event
WHERE year = '2026' AND month = '01' AND day BETWEEN '15' AND '21'
GROUP BY year, month, day, service_id
ORDER BY year, month, day, incident_rate_pct DESC;

-- Query 2: Enterprise Tier Incident Latency Distribution
SELECT
    c.tier AS customer_tier,
    s.service_name,
    COUNT(e.event_id) AS total_events,
    ROUND(AVG(e.duration_ms), 2) AS avg_latency_ms,
    APPROX_PERCENTILE(e.duration_ms, 0.95) AS p95_latency_ms,
    APPROX_PERCENTILE(e.duration_ms, 0.99) AS p99_latency_ms
FROM switchyard_analytics.fact_operational_event e
JOIN switchyard_analytics.dim_customer c ON e.customer_id = c.customer_id
JOIN switchyard_analytics.dim_service s ON e.service_id = s.service_id
WHERE e.year = '2026' AND e.month = '01'
GROUP BY c.tier, s.service_name
ORDER BY p99_latency_ms DESC;

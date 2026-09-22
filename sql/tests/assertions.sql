-- ============================================================================
-- SQL Integrity Assertions: Verifies zero anomalies across tables
-- ============================================================================

-- Assertion 1: Verify zero duplicate event IDs exist in operational events
SELECT event_id, COUNT(*) AS duplicate_count
FROM fact_operational_event
GROUP BY event_id
HAVING COUNT(*) > 1;

-- Assertion 2: Verify zero negative durations exist
SELECT COUNT(*) AS negative_duration_count
FROM fact_operational_event
WHERE duration_ms < 0;

-- Assertion 3: Verify all exceptions have valid foreign key event references
SELECT COUNT(*) AS orphan_exception_count
FROM fact_exception e
LEFT JOIN fact_operational_event o ON e.event_id = o.event_id
WHERE o.event_id IS NULL;

-- Assertion 4: Verify priority scores adhere to 0.0 - 100.0 boundary
SELECT COUNT(*) AS out_of_bounds_priority_count
FROM fact_exception
WHERE priority_score < 0.0 OR priority_score > 100.0;

-- ============================================================================
-- SWITCHYARD: Relational Operational Serving & Analytics Schema DDL
-- Compatible with PostgreSQL 15+ and SQLite3
-- ============================================================================

-- 1. DimCustomer
CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id VARCHAR(32) PRIMARY KEY,
    customer_name VARCHAR(128) NOT NULL,
    tier VARCHAR(16) NOT NULL,
    contract_sla_tier VARCHAR(16) NOT NULL,
    industry VARCHAR(64) NOT NULL
);

-- 2. DimService
CREATE TABLE IF NOT EXISTS dim_service (
    service_id VARCHAR(32) PRIMARY KEY,
    service_name VARCHAR(128) NOT NULL,
    service_category VARCHAR(32) NOT NULL,
    tier_level INTEGER NOT NULL,
    default_sla_minutes INTEGER NOT NULL
);

-- 3. DimLocation
CREATE TABLE IF NOT EXISTS dim_location (
    location_id VARCHAR(32) PRIMARY KEY,
    region VARCHAR(32) NOT NULL,
    datacenter_zone VARCHAR(32) NOT NULL,
    country VARCHAR(32) NOT NULL
);

-- 4. FactOperationalEvent
CREATE TABLE IF NOT EXISTS fact_operational_event (
    event_id VARCHAR(64) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    customer_id VARCHAR(32) NOT NULL REFERENCES dim_customer(customer_id),
    service_id VARCHAR(32) NOT NULL REFERENCES dim_service(service_id),
    location_id VARCHAR(32) NOT NULL REFERENCES dim_location(location_id),
    event_type VARCHAR(32) NOT NULL,
    duration_ms INTEGER,
    payload_bytes INTEGER,
    status_code INTEGER NOT NULL,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_event_ts ON fact_operational_event(timestamp);
CREATE INDEX IF NOT EXISTS idx_event_customer ON fact_operational_event(customer_id);
CREATE INDEX IF NOT EXISTS idx_event_service ON fact_operational_event(service_id);
CREATE INDEX IF NOT EXISTS idx_event_location ON fact_operational_event(location_id);

-- 5. FactSLARecord
CREATE TABLE IF NOT EXISTS fact_sla_record (
    sla_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL,
    customer_id VARCHAR(32) NOT NULL REFERENCES dim_customer(customer_id),
    service_id VARCHAR(32) NOT NULL REFERENCES dim_service(service_id),
    start_time TIMESTAMP NOT NULL,
    due_time TIMESTAMP NOT NULL,
    target_minutes INTEGER NOT NULL,
    elapsed_minutes REAL NOT NULL,
    remaining_minutes REAL NOT NULL,
    sla_status VARCHAR(16) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sla_case ON fact_sla_record(case_id);
CREATE INDEX IF NOT EXISTS idx_sla_status_due ON fact_sla_record(sla_status, due_time);

-- 6. FactException
CREATE TABLE IF NOT EXISTS fact_exception (
    exception_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL,
    event_id VARCHAR(64) NOT NULL REFERENCES fact_operational_event(event_id),
    customer_id VARCHAR(32) NOT NULL REFERENCES dim_customer(customer_id),
    service_id VARCHAR(32) NOT NULL REFERENCES dim_service(service_id),
    location_id VARCHAR(32) NOT NULL REFERENCES dim_location(location_id),
    financial_exposure REAL NOT NULL,
    priority_score REAL NOT NULL,
    priority_band VARCHAR(4) NOT NULL,
    lifecycle_state VARCHAR(16) NOT NULL,
    reason_drivers TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    assigned_team VARCHAR(64),
    assigned_agent VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_exc_priority_state ON fact_exception(priority_score DESC, lifecycle_state);
CREATE INDEX IF NOT EXISTS idx_exc_case ON fact_exception(case_id);

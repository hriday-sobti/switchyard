-- ============================================================================
-- AWS Glue Data Catalog DDL: External Tables over S3 Lakehouse
-- Database: switchyard_analytics
-- SerDe: org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe
-- ============================================================================

CREATE DATABASE IF NOT EXISTS switchyard_analytics
LOCATION 's3://switchyard-operational-lakehouse/processed/';

-- 1. FactOperationalEvent (Partitioned by year, month, day)
CREATE EXTERNAL TABLE IF NOT EXISTS switchyard_analytics.fact_operational_event (
    event_id STRING,
    timestamp TIMESTAMP,
    customer_id STRING,
    service_id STRING,
    location_id STRING,
    event_type STRING,
    duration_ms BIGINT,
    payload_bytes BIGINT,
    status_code BIGINT,
    error_message STRING,
    hour BIGINT,
    day_of_week STRING,
    is_weekend BOOLEAN
)
PARTITIONED BY (
    year STRING,
    month STRING,
    day STRING
)
STORED AS PARQUET
LOCATION 's3://switchyard-operational-lakehouse/processed/fact_operational_event/'
TBLPROPERTIES ('parquet.compression'='SNAPPY');

-- Repair partitions statement after file upload
-- MSCK REPAIR TABLE switchyard_analytics.fact_operational_event;

-- 2. DimCustomer (External Parquet Table)
CREATE EXTERNAL TABLE IF NOT EXISTS switchyard_analytics.dim_customer (
    customer_id STRING,
    customer_name STRING,
    tier STRING,
    contract_sla_tier STRING,
    industry STRING
)
STORED AS PARQUET
LOCATION 's3://switchyard-operational-lakehouse/processed/dim_customers.parquet';

-- 3. DimService (External Parquet Table)
CREATE EXTERNAL TABLE IF NOT EXISTS switchyard_analytics.dim_service (
    service_id STRING,
    service_name STRING,
    service_category STRING,
    tier_level INT,
    default_sla_minutes INT
)
STORED AS PARQUET
LOCATION 's3://switchyard-operational-lakehouse/processed/dim_services.parquet';

-- 4. DimLocation (External Parquet Table)
CREATE EXTERNAL TABLE IF NOT EXISTS switchyard_analytics.dim_location (
    location_id STRING,
    region STRING,
    datacenter_zone STRING,
    country STRING
)
STORED AS PARQUET
LOCATION 's3://switchyard-operational-lakehouse/processed/dim_locations.parquet';

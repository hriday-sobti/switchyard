# SWITCHYARD: Project Plan & Execution Roadmap

## Executive Overview
SWITCHYARD is an enterprise operational decision-support system and service reliability workbench. It bridges raw operational data lakes to actionable management decisions by:
1. Simulating high-volume operational events across customers, locations, services, and work orders.
2. Ingesting and performing rigorous, traceable data-quality validation with explicit defect quarantine.
3. Structuring historical data into partitioned columnar Parquet files for high-throughput analytical query processing (DuckDB locally, AWS Athena in the cloud).
4. Maintaining operational serving data in relational storage (PostgreSQL/DuckDB/SQLite) for current state, SLA risks, and priority queues.
5. Evaluating multi-dimensional SLA breaches and explainable priority scores using transparent business rules.
6. Exposing decision support via FastAPI endpoints, sliding-window operational statistics, and curated Power BI analytical models.

---

## Technical & Environmental Foundation
- **Operating System:** Windows 11 Home (64-bit AMD Ryzen 7 7735HS)
- **Runtime:** Python 3.14.6
- **Local Analytical Engine:** DuckDB 1.5.5 (in-process columnar SQL engine with direct Parquet execution)
- **Serving & Transactional Layer:** SQLAlchemy 2.0.54 with SQLite/PostgreSQL driver support (clean database abstraction layer)
- **Storage & Columnar Format:** PyArrow 25.0.1, Pandas 3.0.6, Parquet with Snappy compression
- **API Framework:** FastAPI 0.141.1, Uvicorn 0.53.0, Pydantic 2.13.5
- **Testing Suite:** Pytest 9.1.1
- **Cloud Architecture Mode:** AWS S3 prefix layout, AWS Glue Data Catalog DDL, and Amazon Athena partition-aware queries

---

## Phased Work Breakdown Structure

### Phase 0: Environment & Foundation
- [x] Environment inspection: OS, Python 3.14, toolchain, installed libraries.
- [x] Core tool installation (FastAPI, Uvicorn, DuckDB, PyArrow, Pydantic, SQLAlchemy).
- [x] Comprehensive Project Plan (`docs/PROJECT_PLAN.md`).
- [x] Technical Learning Notes (`docs/LEARNING_NOTES.md`).
- [x] Architecture & System Design (`docs/ARCHITECTURE.md`).
- [x] Business Requirements Document (`docs/BUSINESS_REQUIREMENTS.md`).
- [x] Functional Requirements Document (`docs/FUNCTIONAL_REQUIREMENTS.md`).
- [x] Business Rules Specification (`docs/BUSINESS_RULES.md`).
- [x] Data Dictionary & Grain Specifications (`docs/DATA_DICTIONARY.md`).
- [x] Data Lineage & Traceability (`docs/DATA_LINEAGE.md`).
- [x] Test Strategy & SIT/UAT Specifications (`docs/TEST_STRATEGY.md`, `docs/UAT_SCENARIOS.md`).
- [x] Architectural Decision Log (`docs/DECISIONS.md`).

### Phase 1: Data Engineering & Storage
- [x] Repository packaging: `pyproject.toml`, `.env.example`, `.gitignore`.
- [x] Pydantic Schemas for operational entities (`Customer`, `Location`, `Service`, `Agent`, `Order`, `ServiceRequest`, `WorkOrder`, `OperationalEvent`, `SLA`, `ExceptionRecord`).
- [x] Deterministic Synthetic Data Generator with configurable scale (`--scale 100k/1m/10m`) and controlled error injection (`--bad-data-rate 0.02`).
- [x] Data Quality Engine: 10 validation vectors (uniqueness, referential integrity, timestamp validity, status transitions, ranges) with quarantine sink.
- [x] Ingestion & Transformation Pipeline: Raw -> Quality Inspection -> Cleaning -> Parquet Conversion with time-based partitioning (`year=YYYY/month=MM/day=DD/`).
- [x] Relational Serving Layer: Operational schema for active exceptions, SLA records, audit logs, and priority queues.
- [x] Analytical SQL Layer: Star schema fact/dimension queries, CTEs, window functions, conditional aggregations for SLA breaches and bottleneck analysis.

### Phase 2: Core Business Logic & Algorithms
- [x] SLA Calculation Engine: Target determination, elapsed/remaining time, thresholds, and state machine (`ON_TRACK`, `AT_RISK`, `BREACHED`).
- [x] Explainable Business Rules Engine: Multi-factor scoring (SLA risk, customer tier/impact, financial exposure, age, operational criticality) with transparent reasoning drivers.
- [x] Algorithmic Data Structures:
  - Max-Heap Priority Queue for $O(\log n)$ insertion and $O(1)$ peek of highest-risk exceptions.
  - In-Memory Hash Maps for $O(1)$ entity/SLA metadata lookups.
  - Sliding Window Log/Deque for rolling 60-minute incident metrics, breach rates, and failure velocity.
- [x] Production-Grade FastAPI Application: Endpoints for health, operational summaries, paginated exceptions, SLA risk queries, data quality metrics, and operational trends.

### Phase 3: Verification, Integration, Benchmarking & Delivery
- [x] Comprehensive Test Suite:
  - Unit tests for SLA engine, priority scoring, heap priority queue, and sliding window.
  - Data quality tests asserting proper rejection of invalid timestamps, corrupt IDs, and broken transitions.
  - API integration tests asserting contract stability, pagination, and error responses.
  - System Integration Test (SIT) and User Acceptance Testing (UAT) automated runners.
- [x] AWS Integration Layer: S3 prefix topology, Glue Catalog table schemas, partition discovery, and Athena SQL queries with cost-reduction scanning metrics.
- [x] Power BI Semantic Model & Analytical Contracts: Star-schema data contracts, DAX measures, and dashboard layout specifications across 4 operational pages.
- [x] Performance Engineering: Comprehensive benchmark suite measuring data generation, Parquet compression, partitioned vs. unpartitioned scanning, and API latency (`docs/PERFORMANCE.md`).
- [x] Modeled Business Impact Simulator: Reproducible economic and operational hours scenario modeling (`scripts/impact_model.py`).
- [x] End-to-End Demo CLI: `python -m app.demo` executing sample generation, validation, transformation, prioritization, and serving in one command.
- [x] Final human-level review, placeholder sanitization, and production README.

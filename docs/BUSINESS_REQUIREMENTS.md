# SWITCHYARD: Requirements & Specifications Suite

## Section 1: Business Requirements (BR)

| Req ID | Title | Business Objective & Description | Success Metric |
| :--- | :--- | :--- | :--- |
| **BR-01** | Proactive SLA Risk Identification | Operations triage leads must identify in-flight service requests and work orders approaching SLA breach before failure occurs. | 100% of cases within warning threshold (<20% remaining time) flagged as `AT_RISK`. |
| **BR-02** | Multi-Factor Exception Prioritization | The system must calculate an operational priority score combining SLA urgency, customer contract tier, financial exposure, age, and service criticality. | Priority score ranges 0–100 mapped to deterministic priority bands (P1–P4). |
| **BR-03** | Transparent Decision Explainability | Managers must be able to inspect why an item is ranked high-priority through explicit operational drivers. | Every prioritized exception provides at least one explainable driver text string. |
| **BR-04** | KPI-to-Record Drill-Down | Users must be able to drill from high-level enterprise metrics into underlying operational event records. | Direct query mapping from aggregate metrics to discrete transactional entities. |
| **BR-05** | Structural Bottleneck Isolation | Operations leads must pinpoint specific locations, services, or operational teams with recurring SLA breaches. | Granular breakdown reports by location, service tier, and operational team. |
| **BR-06** | Active vs. Historical Disaggregation | The system must clearly decouple active mutable triage queues from immutable historical lakehouse records. | Sub-second active queue queries; zero analytical performance degradation on serving tables. |
| **BR-07** | Big Data Volume Scalability | The data generation and pipeline architecture must support multi-scale execution from 100K dev events up to 10M+ records. | Pipeline completes 10M event generation and partitioned Parquet write without out-of-memory errors. |
| **BR-08** | Traceable Data-Quality Quarantine | The system must enforce auditability: rejected rows must be categorized and preserved rather than silently dropped. | 100% of rejected records written to structured quarantine sinks with explicit error codes. |
| **BR-09** | Cross-Layer Data Consistency | Analytical queries across raw files, Parquet lakehouse, SQL database, and API responses must yield matching answers. | Zero unexplained discrepancies in metric calculations across layers. |
| **BR-10** | Operational Acceptance Verification | The system must provide predefined end-to-end verification scenarios to validate business acceptance. | Automated UAT scenarios execute and pass with audit logs. |

---

## Section 2: Functional Requirements (FR)

| Req ID | Title | Description | Module Mapping |
| :--- | :--- | :--- | :--- |
| **FR-01** | Operational Event Ingestion | Ingest batch operational events across orders, service requests, and work orders in JSON/CSV formats. | `pipelines.ingest` |
| **FR-02** | Schema & Mandatory Field Validation | Enforce non-null constraints on mandatory keys (`event_id`, `timestamp`, `customer_id`, `service_id`). | `pipelines.validate` |
| **FR-03** | Duplicate Event Detection | Detect and quarantine duplicate event IDs or identical operational state updates. | `pipelines.validate` |
| **FR-04** | SLA Target & State Calculation | Calculate target SLA duration, elapsed time, and status (`ON_TRACK`, `AT_RISK`, `BREACHED`). | `app.rules.sla_engine` |
| **FR-05** | Dynamic SLA Risk Assessment | Flag cases where elapsed time exceeds 80% of target duration but remains below 100%. | `app.rules.sla_engine` |
| **FR-06** | Multi-Factor Priority Calculation | Compute weighted priority score based on normalized risk vectors and assign priority band (P1–P4). | `app.rules.priority_engine` |
| **FR-07** | Max-Heap Priority Queue Maintenance | Maintain an in-memory priority queue supporting $O(\log n)$ insert and $O(1)$ top-risk inspection. | `app.core.priority_queue` |
| **FR-08** | RESTful API Service | Expose REST endpoints for health, operational summaries, paginated exceptions, and SLA metrics. | `app.api.routes` |
| **FR-09** | Summary Operational Metrics | Provide real-time aggregates: active exceptions count, breach rate, median resolution time, backlog. | `app.api.routes` |
| **FR-10** | Dimension & Facet Filtering | Support multi-parameter query filtering (by status, priority, location, service, customer). | `app.api.routes` |
| **FR-11** | Data Quality Reporting | Expose summary statistics on ingestion quality: rows processed, accepted, rejected, error breakdown. | `app.services.dq_service` |
| **FR-12** | Sliding-Window Metric Aggregation | Compute rolling 60-minute window statistics for incidents, breach counts, and failure velocity. | `app.core.sliding_window` |
| **FR-13** | Partitioned Parquet Lake Export | Write validated historical events to Parquet files partitioned by `year=YYYY/month=MM/day=DD/`. | `pipelines.partition` |

---

## Section 3: Traceability Matrix

| Business Req | Functional Req | Core Implementation Component | Primary Automated Test | UAT Scenario |
| :--- | :--- | :--- | :--- | :--- |
| **BR-01** | FR-04, FR-05 | `app/rules/sla_engine.py` | `tests/unit/test_sla_engine.py` | UAT-01 |
| **BR-02** | FR-06 | `app/rules/priority_engine.py` | `tests/unit/test_priority_engine.py` | UAT-02 |
| **BR-03** | FR-06 | `app/rules/priority_engine.py` | `tests/unit/test_priority_engine.py` | UAT-02 |
| **BR-04** | FR-09, FR-10 | `sql/analytics/` & `app/api/` | `tests/api/test_api_endpoints.py` | UAT-03 |
| **BR-05** | FR-09, FR-10 | `sql/analytics/bottlenecks.sql` | `tests/integration/test_sql_analytics.py` | UAT-04 |
| **BR-06** | FR-07, FR-13 | `app/core/priority_queue.py` | `tests/unit/test_priority_queue.py` | UAT-05 |
| **BR-07** | FR-01, FR-13 | `pipelines/generate.py` | `tests/integration/test_pipeline_scale.py` | UAT-06 |
| **BR-08** | FR-02, FR-03, FR-11 | `pipelines/validate.py` | `tests/data_quality/test_dq_engine.py` | UAT-07 |
| **BR-09** | FR-08, FR-13 | `sql/transformations/` | `tests/integration/test_cross_layer_consistency.py` | UAT-08 |
| **BR-10** | FR-01–FR-13 | `app/demo.py` & Test Suite | `tests/sit/test_end_to_end_scenario.py` | UAT-09 |

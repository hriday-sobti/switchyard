# SWITCHYARD: Test Strategy & Quality Assurance Framework

## 1. Testing Philosophy & Test Pyramid
SWITCHYARD enforces a deterministic, multi-tiered test strategy where tests validate observable contracts rather than brittle implementation details.

```
       / \
      /UAT\         <-- User Acceptance & Business Scenarios (Deterministic)
     /-----\
    /  SIT  \       <-- End-to-End System Integration Tests (Pipeline -> DB -> API)
   /---------\
  /   SQL &   \     <-- Data Quality, Parquet Validation, & Analytics Correctness
 / Data Quality\
/---------------\
/   Unit Tests  \   <-- Algorithms, SLA Engine, Priority Scoring, State Machine
-----------------
```

---

## 2. Test Suites & Objectives

### Tier 1: Unit Testing (`tests/unit/`)
- **`test_sla_engine.py`:**
  - Verify deterministic calculation of elapsed/remaining minutes across arbitrary timestamps.
  - Verify threshold boundaries ($79.9\%$ vs $80.0\%$ for `AT_RISK`, $99.9\%$ vs $100.0\%$ for `BREACHED`).
  - Verify robust handling of zero target duration or clock skew.
- **`test_priority_engine.py`:**
  - Validate normalized component scoring ($S_{SLA}, S_{Cust}, S_{Fin}, S_{Age}, S_{Crit}$).
  - Verify weight configuration sum integrity ($\sum w_i = 1.0$).
  - Assert that score boundaries correctly map to bands P1, P2, P3, P4.
  - Assert that driver text strings correctly reflect the dominant risk vectors.
- **`test_priority_queue.py`:**
  - Validate Max-Heap ordering ($O(1)$ peek always returns highest priority score).
  - Verify pop operations maintain heap invariants.
  - Test tie-breaking on equal priority scores using case age.
- **`test_sliding_window.py`:**
  - Verify rolling 60-minute window evicts expired events cleanly.
  - Assert correct aggregation of incident counts and breach frequencies under rapid event ingestion.

### Tier 2: Data Quality & Ingestion Testing (`tests/data_quality/`)
- **`test_dq_engine.py`:**
  - Verify duplicate event ID detection and quarantine.
  - Verify rejection of future timestamps and invalid ISO-8601 strings.
  - Test referential integrity failure quarantine (orphan foreign keys).
  - Test validation metrics summary (`rows_processed`, `rows_valid`, `rows_rejected`).

### Tier 3: SQL & Analytics Testing (`tests/integration/`)
- **`test_sql_analytics.py`:**
  - Run analytics queries against DuckDB and verify correctness of CTEs, window functions (`ROW_NUMBER()`, `DENSE_RANK()`), and aggregations.
  - Verify partition pruning efficiency when filtering by date partition.
- **`test_cross_layer_consistency.py`:**
  - Assert exact equality between metrics calculated directly from raw validated events, Parquet Lake, SQL views, and API response aggregates.

### Tier 4: API Testing (`tests/api/`)
- **`test_api_endpoints.py`:**
  - Validate `GET /health` returns HTTP 200 with service dependencies status.
  - Validate `GET /operations/summary` returns accurate counts and metrics.
  - Validate `GET /exceptions` pagination, sorting by priority score descending, and filtering.
  - Verify proper HTTP 404 on nonexistent exception ID.

### Tier 5: System Integration (SIT) & User Acceptance Testing (UAT) (`tests/sit/`)
- **`test_end_to_end_scenario.py`:**
  - Execute end-to-end flow: Generate batch data $\rightarrow$ Ingest & Validate $\rightarrow$ Partition Parquet $\rightarrow$ Populate Serving Layer $\rightarrow$ Query API $\rightarrow$ Verify priority queue and SLA risk alignment.

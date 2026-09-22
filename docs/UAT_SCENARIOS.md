# SWITCHYARD: User Acceptance Testing (UAT) Scenarios

## Scenario Catalog Overview
Every UAT scenario represents an end-to-end business narrative validated by automated fixtures and demonstrable in the operational UI/API.

---

### UAT-01: Proactive Triage of Imminent SLA Breach
- **Business Objective:** Ensure operations triage team is alerted to cases nearing SLA breach before customer escalation occurs.
- **Precondition:** System has received 1,000 operational events; Case `REQ-10492` has elapsed 85% of its SLA window (22 minutes remaining).
- **Action:** Operations manager navigates to Exception Queue / calls `GET /sla-risk`.
- **Expected Result:**
  - Case `REQ-10492` is listed with status `AT_RISK`.
  - Priority engine assigns priority band `P1` or `P2` with driver `"SLA breach imminent in 22 minutes"`.
  - Case appears in the top quartile of the triage queue.
- **Verification Mode:** Automated integration test `tests/sit/test_uat_scenarios.py::test_uat_01_proactive_sla_breach`.

---

### UAT-02: Transparent Priority Score Driver Inspection
- **Business Objective:** Confirm that an operations lead can inspect why a given exception has received Priority P1 over another.
- **Precondition:** Exception `EXC-88219` generated with high financial exposure ($120,000) and Enterprise Tier 1 customer.
- **Action:** Lead queries `GET /exceptions/EXC-88219`.
- **Expected Result:**
  - HTTP 200 returned with `priority_score >= 85.0` and `priority_band: P1`.
  - Field `priority_reasons` explicitly includes:
    1. `"Tier 1 Enterprise customer account"`
    2. `"Significant financial exposure ($120,000)"`
- **Verification Mode:** `tests/sit/test_uat_scenarios.py::test_uat_02_priority_reasons_transparency`.

---

### UAT-03: Drill-Down from High-Level KPI to Operational Records
- **Business Objective:** Validate that an executive viewing total SLA breach rate can drill down into the exact underlying transactional records.
- **Precondition:** Analytical queries compute total breach rate of 8.4% across 5,000 events.
- **Action:** Query API endpoint `/exceptions?status=BREACHED` and compare total count against analytical view `vw_sla_breach_summary`.
- **Expected Result:**
  - Exact count of breached items in the operational queue matches the aggregate metric count.
  - Every returned item provides direct foreign key links to `event_id`, `customer_id`, and `service_id`.
- **Verification Mode:** `tests/sit/test_uat_scenarios.py::test_uat_03_kpi_to_record_drilldown`.

---

### UAT-04: Isolation of Location & Service Bottlenecks
- **Business Objective:** Identify if a specific datacenter region or service category is responsible for disproportionate failures.
- **Precondition:** Generator injects simulated latency/timeout anomalies into location `LOC-US-EAST-01` on service `SRV-PAYMENTS`.
- **Action:** Execute analytical query `sql/analytics/bottlenecks.sql`.
- **Expected Result:**
  - `LOC-US-EAST-01` ranks #1 in breach percentage (>30% breach rate).
  - Power BI service performance matrix flags the anomaly with visual warning indicators.
- **Verification Mode:** `tests/sit/test_uat_scenarios.py::test_uat_04_bottleneck_isolation`.

---

### UAT-05: Non-Destructive Data-Quality Quarantine
- **Business Objective:** Ensure corrupt or malformed incoming data does not crash ingestion or corrupt serving tables, but is safely quarantined for audit.
- **Precondition:** Ingestion stream with `--bad-data-rate 0.05` contains 50 invalid records (duplicate IDs, negative durations, future dates).
- **Action:** Run ingestion pipeline `python -m pipelines.validate`.
- **Expected Result:**
  - Zero invalid records enter `data/processed/` or the operational database.
  - Exactly 50 records are written to `data/rejected/` with specific rejection codes (`ERR_DUPLICATE_ID`, `ERR_FUTURE_TIMESTAMP`).
  - Validation metrics report: `rows_processed: 1000, rows_valid: 950, rows_rejected: 50`.
- **Verification Mode:** `tests/sit/test_uat_scenarios.py::test_uat_05_data_quality_quarantine`.

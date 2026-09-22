# SWITCHYARD: Power BI Operations Workbench Dashboard Specification

## Visual Design System & Aesthetics
- **Theme:** Professional, restrained operational workbench.
- **Background:** Clean neutral light grey (`#F8F9FA`).
- **Primary Accent:** Slate Navy (`#1E293B`).
- **Semantic Colors:**
  - Healthy / On-Track: Subdued Muted Green (`#10B981`)
  - Warning / At-Risk: Subdued Amber (`#F59E0B`)
  - Critical / Breached: Distinct Crimson Red (`#EF4444`)
  - Neutral Secondary: Cool Steel (`#64748B`)

---

## Page Architecture

### Page 1: Operations Overview (Executive Triage)
- **Top Bar:** Page Title ("Operational Health Overview"), Global Date Slicer (Last 24 Hours / 7 Days), Last Refresh Timestamp (`Last Refresh: 10:42:18 UTC`).
- **Card Row (Executive KPIs):**
  1. `Active Backlog` (Count of open exceptions)
  2. `SLA At Risk` (Yellow indicator)
  3. `SLA Breached` (Red indicator)
  4. `Total Financial Exposure ($)`
- **Charts:**
  - Left: `Hourly Incident Volume Trend` (Line chart: Hour vs Total Events and Errors).
  - Right: `Exception Distribution by Priority Band` (Bar chart: P1, P2, P3, P4).
- **Bottom Section:** `Critical P1 Triage Table` showing Top 10 items from Max-Heap queue with driver reasons.

### Page 2: Exception Control & Triage
- **Purpose:** Primary operational triage queue for shift leads.
- **Slicers:** Priority Band, Lifecycle State, Service Category, Assigned Team.
- **Main Visual:** Interactive High-Density Table:
  - Columns: `Exception ID`, `Case ID`, `Priority Band`, `Priority Score`, `Customer Name`, `Service`, `SLA Status`, `Time Remaining`, `Drivers`, `Assigned Team`.
  - Conditional formatting: Score $\ge 85$ highlighted in soft red.

### Page 3: Service & Location Reliability (Bottlenecks)
- **Purpose:** Engineering root-cause and infrastructure bottleneck analysis.
- **Visuals:**
  - `Service Reliability Matrix`: Service Name, Tier, Total Events, Incident Count, Error Rate %, Avg Latency ms.
  - `Datacenter Regional Heatmap`: Map visual sized by Error Event count and colored by Error Rate.
  - `Latency Percentiles by Tier`: P95 and P99 latency comparison.

### Page 4: Data Quality & Ingestion Traceability
- **Purpose:** Transparency and audit defense for incoming data stream.
- **KPI Cards:**
  - `Rows Processed`, `Rows Accepted`, `Rows Quarantined`, `Acceptance Rate %`.
- **Breakdown Chart:**
  - `Quarantine Reason Distribution`: Bar chart of `ERR_DUPLICATE_ID`, `ERR_FUTURE_TIMESTAMP`, `ERR_FK_CUSTOMER_ORPHAN`, etc.

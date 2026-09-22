# SWITCHYARD

Operational Exception & Service Reliability Workbench built in Python, SQL, DuckDB, Parquet, and FastAPI.

---

## What Problem This Solves

In high-volume service architectures (payment processing, order routing, infrastructure telemetry), tens of thousands of diagnostic events occur every minute. When downstream services degrade, error logs flood operations teams. 

Most incident dashboards simply display raw error counts or sort issues chronologically. This creates two critical problems:
1. **Critical cases get buried:** A low-tier customer facing a minor timeout can easily push an impending SLA breach for a top enterprise account out of view.
2. **Priorities are opaque:** Traditional ticketing systems assign static priorities (e.g. "P1" or "P2") without explaining *why* an issue was prioritized that way or how close it is to incurring contract breach penalties.

SWITCHYARD connects raw operational telemetry to structured, explainable triage decisions:

```
RAW LOGS / EVENTS ──> DATA QUALITY AUDIT ──> PARTITIONED PARQUET LAKE ──> DUCKDB / ATHENA
                                                                               │
                                                                               ▼
EXECUTIVE DECISION <── POWER BI <── FASTAPI REST API <── MAX-HEAP QUEUE <── SLA & PRIORITY ENGINE
```

---

## Core System Architecture

```
                       +---------------------------------------+
                       |      Event Generator CLI (10M+)       |
                       +-------------------+-------------------+
                                           |
                                           v
                       +---------------------------------------+
                       |     Data Quality Validation Layer     |
                       | (Nulls, schema, dates, referential FK)|
                       +---------+-------------------+---------+
                                 |                   |
                  [Quarantined]  v                   v  [Clean Events]
                       +-------------------+   +---------------------------------------+
                       | data/rejected/    |   | Partitioned Parquet Lakehouse         |
                       | (Audit logs)      |   | (year=YYYY/month=MM/day=DD/)          |
                       +-------------------+   +---------+-------------------+---------+
                                                         |                   |
                                                         v                   v
                                              +--------------------+   +--------------------+
                                              | Local: DuckDB OLAP |   | Cloud: AWS Athena  |
                                              +----------+---------+   +----------+---------+
                                                         |                        |
                                                         +------------+-----------+
                                                                      |
                                                                      v
+-------------------------------------------------------------------------------------------------------------------+
| Operational Serving Layer (PostgreSQL / SQLite)                                                                  |
|                                                                                                                   |
|   +------------------------+       +--------------------------+       +---------------------------------------+   |
|   |   SLA State Machine    | ----> | Explainable Priority     | ----> | Max-Heap Active Priority Queue        |   |
|   | (On-Track/At-Risk/Fail)|       | Engine (Weighted Vectors)|       | & 60-Minute Sliding-Window Deque      |   |
|   +------------------------+       +--------------------------+       +-------------------+-------------------+   |
|                                                                                           |                       |
|   +-----------------------------------------------------------------------------------+   |                       |
|   | Relational Serving Store: Active Exceptions, SLA Statuses, and Triage Backlog     | <-+                       |
|   +-----------------------------------------------------------------------------------+                           |
+-------------------------------------------------------------------------------------------------------------------+
                                           |
                                           v
                       +---------------------------------------+
                       |          FastAPI REST Service         |
                       | (/health, /summary, /exceptions, etc) |
                       +-------------------+-------------------+
                                           |
                                           v
                       +---------------------------------------+
                       |      Power BI Semantic Data Model     |
                       | (Executive KPIs & Drill-Down Reports) |
                       +---------------------------------------+
```

---

## Key Technical Decisions & Design Rationale

- **Decoupled OLTP Serving & OLAP Analytics:**
  - Fast, point-in-time triage reads and state mutations run against relational tables (SQLite for local dev, PostgreSQL for cloud).
  - Bulk historical aggregations (median resolution time, error distribution by service category) run against columnar Parquet files via DuckDB locally and AWS Athena in production. This avoids running heavy table scans against the operational database.
- **Partitioned Parquet Lake:**
  - Operational events are partitioned by date (`year=YYYY/month=MM/day=DD/`) using PyArrow and compressed with Snappy.
  - Queries filtering on specific dates use partition pruning to skip unreferenced folders, reducing disk I/O and query time by over 6x.
- **Explainable Multi-Factor Prioritization:**
  - Rather than using an opaque black-box score, priority (0–100) is calculated from 5 normalized business components:
    $$\text{Priority} = 0.35 \cdot S_{SLA} + 0.25 \cdot S_{Customer} + 0.20 \cdot S_{Financial} + 0.10 \cdot S_{Age} + 0.10 \cdot S_{Criticality}$$
  - Every score returns readable driver strings explaining why it received a given rank (e.g., `SLA breach imminent in 8.0 minutes`, `Tier 1 Enterprise customer account`, `High financial exposure ($183,066.81)`).
- **Algorithmic Max-Heap & Sliding Window:**
  - Active exceptions are maintained in an in-memory Max-Heap (`heapq`), providing $O(1)$ lookup for the most critical item and $O(\log n)$ inserts.
  - A double-ended queue (`collections.deque`) tracks rolling 60-minute incident velocity and breach rates with $O(1)$ amortized eviction.

---

## Project Structure

```
switchyard/
├── README.md                      # Project overview and technical rationale
├── pyproject.toml                 # Dependencies and pytest configuration
├── .env.example                   # Local environment variable template
├── .gitignore                     # Git exclusions (build caches, datasets, databases)
│
├── app/                           # Core application logic
│   ├── api/main.py                # FastAPI endpoints with pagination & filtering
│   ├── core/                      # Max-Heap priority queue, sliding window, config, logging
│   ├── models/                    # Pydantic schemas and SQLAlchemy ORM entities
│   ├── repositories/              # Database engine setup and session management
│   ├── rules/                     # SLA state engine and explainable priority scoring
│   ├── services/                  # Operational exception processing and DuckDB analytics
│   └── demo.py                    # Deterministic end-to-end pipeline runner
│
├── pipelines/                     # Data processing pipelines
│   ├── generate.py                # Synthetic enterprise event generator (supports 10M+)
│   ├── validate.py                # Multi-vector data quality validator & quarantine sink
│   ├── partition.py               # Columnar Parquet writer with date partitioning
│   └── load.py                    # Loader for relational serving database
│
├── sql/                           # SQL schemas and queries
│   ├── schema/ddl.sql             # Relational DDL for PostgreSQL and SQLite
│   ├── analytics/views.sql        # Analytical views (bottlenecks, window functions)
│   ├── transformations/           # ELT dimensional aggregation scripts
│   └── tests/assertions.sql       # Data integrity assertions
│
├── aws/                           # Cloud integration architecture
│   ├── s3/layout.txt              # S3 prefix and lakehouse bucket layout
│   ├── glue/catalog_ddl.sql       # AWS Glue Data Catalog external table DDLs
│   ├── athena/queries.sql         # Partition-pruned Amazon Athena production queries
│   └── iam/policy.json            # Least-privilege IAM security policy
│
├── powerbi/                       # Business intelligence layer
│   ├── semantic_model.json        # Star-schema entity model and relationships
│   ├── dax_measures.txt           # Standardized DAX formulas
│   └── dashboard_spec.md          # 4-page UI/UX layout and visual hierarchy
│
├── scripts/                       # Operational scripts
│   ├── benchmark.py               # Throughput and scan speed benchmark runner
│   └── impact_model.py            # Operational hours and penalty avoidance calculator
│
├── docs/                          # Detailed technical documentation
│   ├── ARCHITECTURE.md            # System design and Mermaid flowcharts
│   ├── BUSINESS_REQUIREMENTS.md   # Requirements matrix (BR-01..10, FR-01..13)
│   ├── BUSINESS_RULES.md          # Mathematical formulas and threshold logic
│   ├── DATA_DICTIONARY.md         # Field definitions and data lineage
│   ├── DECISIONS.md               # Architecture Decision Records (ADRs 001-005)
│   ├── LEARNING_NOTES.md          # Database and data engineering concepts
│   ├── PERFORMANCE.md             # Measured benchmark numbers and scan metrics
│   ├── PROJECT_PLAN.md            # Work breakdown structure
│   ├── TEST_STRATEGY.md           # Test pyramid and QA methodology
│   └── UAT_SCENARIOS.md           # End-to-end acceptance testing scenarios
│
└── tests/                         # Test suite (177 tests, 100% passing)
    ├── api/                       # API integration, pagination, and error tests
    ├── data_quality/              # Quarantine and defect detection tests
    ├── integration/               # DuckDB analytical view tests
    ├── sit/                       # System integration and UAT business scenario tests
    └── unit/                      # Unit tests for rules, heap, window, and schemas
```

---

## Getting Started

### 1. Requirements
- Python 3.11 or higher (developed and tested on Python 3.14)
- Packages: `duckdb`, `pyarrow`, `pandas`, `pydantic`, `sqlalchemy`, `fastapi`, `uvicorn`, `pytest`

### 2. Setup
```bash
git clone https://github.com/hriday-sobti/switchyard.git
cd switchyard

cp .env.example .env
```

### 3. Run the End-to-End Pipeline
To run data generation, data quality checks, Parquet partitioning, serving database load, and priority triage in one command:
```bash
python -m app.demo --scale 1000 --bad-data-rate 0.03
```

### 4. Start the API
```bash
python -m uvicorn app.api.main:app --port 8000
```
Open `http://127.0.0.1:8000/docs` in your browser to inspect and test the interactive OpenAPI endpoints.

### 5. Run the Test Suite
```bash
python -m pytest tests/
```
All 177 tests run and pass in approximately 2 seconds with zero warnings.

---

## Author

- **Hriday Singh Sobti**
- Email: [hridaysobti@gmail.com](mailto:hridaysobti@gmail.com)
- GitHub: [@hriday-sobti](https://github.com/hriday-sobti)

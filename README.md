# SWITCHYARD: Operational Exception & Service Reliability Workbench

SWITCHYARD is an enterprise operational decision-support system and service reliability workbench. It transforms high-velocity, noisy operational event streams into prioritized, explainable management decisions.

The system addresses the fundamental enterprise operational challenge: in high-volume environments with millions of events, critical exceptions and impending SLA breaches get buried in operational noise. SWITCHYARD provides complete, verifiable data lineage from raw data lakes to executive dashboards.

```
DATA → INFORMATION → PRIORITY → DECISION
```

---

## Key Capabilities

- **High-Throughput Synthetic Data Engine:** Deterministic generation of enterprise operational graphs (customers, services, locations, orders, SLA records, telemetry events) supporting development (100K), integration (1M), and benchmark scales (10M+ events).
- **Controlled Data-Quality Quarantine:** Automated detection of duplicates, future timestamps, invalid state transitions, and referential integrity violations with structured quarantine auditing.
- **Partitioned Columnar Lakehouse:** High-efficiency Apache Parquet storage with date partitioning (`year=YYYY/month=MM/day=DD/`), queried via DuckDB locally and Amazon Athena in AWS.
- **Transparent Multi-Factor Prioritization:** Explainable 0–100 priority scoring combining SLA urgency, customer tier, financial exposure, waiting age, and operational criticality with clear driver explanations.
- **Algorithmic Core:** In-memory Max-Heap priority queue for $O(1)$ top-risk triage, hash lookups, and sliding-window deques for rolling 60-minute operational statistics.
- **Operational Serving & REST API:** Sub-second FastAPI service delivering operational summaries, SLA risk alerts, paginated exception queues, and drill-down capabilities.
- **Power BI Analytical Model:** Star-schema semantic model with curated DAX measures across 4 operational pages (Operations Overview, Exception Control, Bottleneck Analysis, Data Quality).
- **Modeled Business Impact Engine:** Scenario-based simulation of operational hours saved, backlog reduction, and breach prevention.

---

## Architecture Overview

```
                      +---------------------------------------+
                      |   Synthetic Event Generator (10M+)   |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |    Data Quality & Quarantine Engine   |
                      |  (Checks: nulls, dates, FKs, states)  |
                      +---------+-------------------+---------+
                                |                   |
                 [Quarantined]  v                   v  [Validated]
                      +-------------------+   +---------------------------------------+
                      | data/rejected/    |   | Partitioned Parquet Lakehouse         |
                      | (Audit logs)      |   | (year=YYYY/month=MM/day=DD/)          |
                      +-------------------+   +---------+-------------------+---------+
                                                        |                   |
                                                        v                   v
                                             +--------------------+   +--------------------+
                                             | Local Mode: DuckDB |   | Cloud Mode: Athena |
                                             +----------+---------+   +----------+---------+
                                                        |                        |
                                                        +------------+-----------+
                                                                     |
                                                                     v
+------------------------------------------------------------------------------------------------------------------+
| Operational Serving Layer                                                                                        |
|                                                                                                                  |
|  +------------------------+      +--------------------------+      +------------------------------------------+  |
|  |   SLA State Machine    | ---> | Explainable Priority     | ---> | Algorithmic Core:                        |  |
|  | (On-Track/At-Risk/Fail)|      | Engine (Weighted Drivers)|      | Max-Heap Queue + Sliding-Window Deque    |  |
|  +------------------------+      +--------------------------+      +--------------------+---------------------+  |
|                                                                                         |                        |
|  +----------------------------------------------------------------------------------+   |                        |
|  | Relational Store (PostgreSQL / SQLite Serving DB): Active Exceptions & Audit     | <-+                        |
|  +----------------------------------------------------------------------------------+                            |
+------------------------------------------------------------------------------------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |        FastAPI REST Service           |
                      | (/health, /summary, /exceptions, etc) |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |       Power BI Operations Workbench   |
                      | (Executive KPIs & Drill-Down Reports) |
                      +---------------------------------------+
```

---

## Quickstart Guide

### 1. Requirements
- Python 3.11+ (Tested on Python 3.14.6)
- Core dependencies: `duckdb`, `pyarrow`, `pandas`, `pydantic`, `sqlalchemy`, `fastapi`, `uvicorn`, `pytest`

### 2. Environment Setup
```bash
# Clone repository
git clone https://github.com/your-org/switchyard.git
cd switchyard

# Configure environment variables
cp .env.example .env
```

### 3. One-Command End-to-End Demo
To generate sample data, execute data-quality validation, partition into Parquet, populate the operational serving layer, and calculate priority scores:
```bash
python -m app.demo --scale 1000 --bad-data-rate 0.03
```

### 4. Running the Serving API
```bash
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive OpenAPI documentation will be accessible at: `http://127.0.0.1:8000/docs`.

### 5. Running the Complete Test Suite
```bash
python -m pytest tests/ -v
```

---

## Repository Structure

```
switchyard/
├── README.md                      # Human-authored technical system overview
├── pyproject.toml                 # Build configuration and dependency specification
├── .env.example                   # Safe template for environment variables
├── .gitignore                     # Repository hygiene exclusions
│
├── app/                           # Core application & serving engine
│   ├── api/                       # FastAPI router and request/response models
│   ├── core/                      # Priority queue, sliding window, and configuration
│   ├── models/                    # Pydantic schemas and SQLAlchemy entity models
│   ├── repositories/              # Relational database access layer
│   ├── rules/                     # Deterministic SLA and Explainable Priority engines
│   ├── services/                  # Operational service orchestration
│   └── demo.py                    # Repeatable, deterministic demo runner
│
├── data/                          # Data lake directories (Git-excluded for scale)
│   ├── sample/                    # Representative test fixtures
│   ├── schemas/                   # JSON schemas for data exchange
│   ├── generated/                 # Raw synthetic event batches
│   └── rejected/                  # Quarantined bad-data sink with error manifests
│
├── pipelines/                     # Data lakehouse pipeline stages
│   ├── generate.py                # High-volume synthetic enterprise generator
│   ├── validate.py                # Multi-vector data quality validator
│   ├── transform.py               # Dimensional enrichment and transformation
│   ├── partition.py               # Time-based columnar Parquet writer
│   └── load.py                    # Operational serving loader
│
├── sql/                           # Structured SQL engineering
│   ├── schema/                    # DDL for star schema and operational tables
│   ├── transformations/           # ELT enrichment scripts
│   ├── analytics/                 # Business queries (bottlenecks, breach rates)
│   └── tests/                     # SQL data integrity assertions
│
├── aws/                           # Cloud lakehouse integration
│   ├── s3/                        # Bucket layout and prefix specifications
│   ├── glue/                      # Glue Data Catalog table DDL definitions
│   ├── athena/                    # Production Athena analytical queries
│   └── iam/                       # Least-privilege IAM security policies
│
├── tests/                         # Complete multi-tiered test suite
│   ├── unit/                      # Algorithms, SLA logic, and priority scoring tests
│   ├── integration/               # Pipeline execution and SQL analytical tests
│   ├── data_quality/              # Quarantine and validation vector tests
│   ├── api/                       # REST endpoint contract and pagination tests
│   └── sit/                       # End-to-end system integration and UAT tests
│
├── powerbi/                       # Power BI analytical workbench
│   ├── semantic_model.json        # Star-schema entity and relationship definition
│   ├── dax_measures.txt           # Standardized business metric formulas
│   └── dashboard_spec.md          # 4-page UI/UX visual hierarchy specification
│
├── scripts/                       # Operational utility scripts
│   ├── benchmark.py               # Performance and scalability benchmark runner
│   └── impact_model.py            # Simulated economic and operational impact calculator
│
└── docs/                          # Comprehensive architectural documentation
    ├── PROJECT_PLAN.md            # Execution plan and milestones
    ├── ARCHITECTURE.md            # In-depth system design & Mermaid diagrams
    ├── BUSINESS_REQUIREMENTS.md   # Formal BR and FR requirements
    ├── BUSINESS_RULES.md          # Prioritization and SLA logic specifications
    ├── DATA_DICTIONARY.md         # Field-level dictionary and lineage
    ├── TEST_STRATEGY.md           # Multi-tiered testing philosophy
    ├── UAT_SCENARIOS.md           # User acceptance criteria and scenarios
    ├── DECISIONS.md               # Architectural decision records (ADRs)
    ├── PERFORMANCE.md             # Measured performance benchmarks
    └── LEARNING_NOTES.md          # Theoretical and architectural compendium
```

---

## Author & Contributor

- **Author:** Hriday Singh Sobti
- **Contact:** [hridaysobti@gmail.com](mailto:hridaysobti@gmail.com)
- **GitHub:** [@hriday-sobti](https://github.com/hriday-sobti)

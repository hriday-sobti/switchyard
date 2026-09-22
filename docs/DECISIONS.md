# SWITCHYARD: Architectural Decisions Log (ADR)

## ADR-001: Storage Format for Analytical Historical Lakehouse
- **Status:** Accepted
- **Context:** SWITCHYARD requires an analytical storage format capable of handling millions of operational records with fast scan performance, compact storage footprint, and seamless cloud data-lake compatibility.
- **Decision:** Use **Apache Parquet** with **Snappy compression** organized into hierarchical date partitions (`year=YYYY/month=MM/day=DD/`).
- **Consequences & Tradeoffs:**
  - *Benefits:* Columnar projection eliminates scanning unneeded attributes; min/max metadata enables predicate pushdown; native compatibility with DuckDB locally and AWS Athena in cloud mode; up to 80% compression versus raw CSV.
  - *Costs:* Files are binary and require specialized tools (PyArrow, DuckDB) rather than raw text editors to inspect.

---

## ADR-002: Decoupled Dual-Engine Architecture (OLTP Serving vs. OLAP Analytical)
- **Status:** Accepted
- **Context:** Operations teams require sub-second point updates and reads for triage queues, while executive analysts require bulk aggregations across millions of historical events.
- **Decision:** Separate the serving layer from the analytical lakehouse:
  - **Operational Serving:** Relational database (SQLAlchemy with SQLite / PostgreSQL) storing mutable active exceptions and prioritized queues.
  - **Analytical Lakehouse:** Partitioned Parquet queried via DuckDB (locally) and Athena (AWS).
- **Consequences & Tradeoffs:**
  - *Benefits:* Zero contention between analytical queries and operational triage updates; optimal storage model for each workload.
  - *Costs:* Requires an explicit synchronization and transformation pipeline to populate both layers from the validated event stream.

---

## ADR-003: Explainable Rule-Based Priority Scoring Over Black-Box ML
- **Status:** Accepted
- **Context:** We evaluated whether to use an unsupervised ranking model, deep learning, or an explainable weighted multi-factor rule engine for operational exception prioritization.
- **Decision:** Implement a **transparent multi-factor rule engine** with normalized dimension scoring ($S_{SLA}, S_{Cust}, S_{Fin}, S_{Age}, S_{Crit}$) and explicit driver generation.
- **Consequences & Tradeoffs:**
  - *Benefits:* 100% deterministic, audit-defensible, and directly explainable to frontline triage leads (`"Why is this P1?"`); easily calibrated via centralized configuration without retraining data drift.
  - *Costs:* Does not automatically discover latent non-linear relationships without manual rule tuning.

---

## ADR-004: In-Memory Algorithmic Data Structures for Real-Time Triage
- **Status:** Accepted
- **Context:** The triage engine must maintain thousands of active exceptions sorted by priority and compute trailing temporal metrics (e.g., rolling 60-minute breach frequency) without hammering the database.
- **Decision:** Implement a **Max-Heap Priority Queue** (`heapq`) and a **Sliding-Window Deque** (`collections.deque`) in memory.
- **Consequences & Tradeoffs:**
  - *Benefits:* $O(1)$ lookup for the most urgent exception; $O(\log n)$ updates; $O(1)$ amortized sliding-window eviction.
  - *Costs:* State must be periodically re-synced from the relational operational store on service restart.

---

## ADR-005: Local-First AWS Cloud Parity Architecture
- **Status:** Accepted
- **Context:** The system must run flawlessly on a local workstation without requiring continuous paid cloud infrastructure, while simultaneously providing complete architectural parity with an enterprise AWS S3 + Glue + Athena deployment.
- **Decision:** Design an abstract storage and query interface:
  - Local mode: Local directory hierarchy (`data/processed/`) queried via DuckDB SQL.
  - AWS mode: S3 prefixes (`s3://bucket/processed/`) registered in Glue Catalog and queried via Amazon Athena ANSI SQL.
- **Consequences & Tradeoffs:**
  - *Benefits:* Enables instant local development, deterministic CI testing, and zero mandatory cloud spending, with identical query semantics.

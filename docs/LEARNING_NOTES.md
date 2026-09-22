# Engineering Notes: Architecture & Data Foundations
## 1. Relational vs. Analytical Modeling (OLTP vs. OLAP)

### Relational OLTP (Online Transaction Processing)
- **Primary Goal:** High concurrency, sub-millisecond atomic transactions (ACID), normalized structure (3NF) to eliminate data redundancy and anomalies during writes (`INSERT`, `UPDATE`, `DELETE`).
- **Access Pattern:** High volume of small, key-based point reads and writes.
- **Role in SWITCHYARD:** PostgreSQL/SQLite serves as the operational state store for current active exceptions, live SLA statuses, prioritized worker queues, and operational configurations. Writes occur as events mutate case states.

### Columnar OLAP (Online Analytical Processing)
- **Primary Goal:** High-throughput read execution over millions or billions of records, aggregation across specific vertical columns (e.g., `SUM(financial_exposure)`, `AVG(elapsed_minutes)`).
- **Access Pattern:** Heavy scans over selected columns, infrequent updates, batch appends.
- **Role in SWITCHYARD:** Historical event logs, SLA event histories, and operational metrics are stored in Apache Parquet files organized into star-schema fact and dimension tables. Scanned via DuckDB locally and AWS Athena in cloud mode.

---

## 2. Columnar Storage & Apache Parquet Internals

### Why Parquet Over CSV or JSON?
1. **Columnar Projection:** In an operational event table with 40 attributes, an analytical query computing average resolution time per service only reads 2 columns (`service_id`, `resolution_duration`). In row-based formats (CSV, JSON), 100% of the byte stream must be read from disk and parsed. Parquet reads only the target column chunks.
2. **Metadata & Statistics:** Parquet files embed file-level and row-group-level metadata containing minimum/maximum values, null counts, and row counts. Engines like DuckDB and Athena perform **predicate pushdown** (skipping entire row groups whose min/max boundary excludes the filter criteria) without decompressing the data.
3. **Compression Efficiency:** Columnar data groups identical types together (e.g., arrays of timestamps, categorical string IDs), yielding massive compression ratios (often 4x-10x) using Snappy or ZSTD compared to uncompressed CSVs.
4. **Binary Encoding:** Numbers and timestamps are stored in binary encodings (dictionary encoding, bit-packing, run-length encoding) rather than ASCII text strings, eliminating CPU parsing overhead.

---

## 3. Data Lake Storage & Partitioning Strategies

### Partitioning Principles
- **What is Partitioning?** Organizing data in hierarchical directories based on low-to-medium cardinality categorical or temporal keys (e.g., `s3://bucket/processed/events/year=2026/month=01/day=15/`).
- **Partition Pruning:** When an analytical query includes `WHERE event_date >= '2026-01-01' AND event_date < '2026-02-01'`, the query engine inspects directory paths and completely bypasses scanning directories outside of January 2026.
- **High-Cardinality Anti-Pattern:** Partitioning on `customer_id` or `uuid` produces millions of tiny files ("small file problem"), exhausting filesystem inodes and overwhelming catalog metadata lookups.
- **SWITCHYARD Strategy:** Partition operational events by ingestion/event date (`year=YYYY/month=MM/day=DD`). Dimension tables and low-volume reference entities are stored unpartitioned.

---

## 4. Business Rule Engine & Explainable Prioritization

### Explainable vs. Black-Box Prioritization
In critical enterprise operations, assigning priority via black-box models (e.g., deep neural networks) causes operational friction because triage managers cannot explain why a lower-value customer's case is being escalated over an enterprise account. 
SWITCHYARD implements an explainable rule engine combining normalized multi-attribute scoring with human-readable reasoning drivers:
1. **SLA Risk Factor ($S$):** Exponential/steep linear penalty as remaining time approaches zero or goes negative.
2. **Customer Impact ($C$):** Based on contract tier (Tier 1 Enterprise vs. Tier 3 Basic) and historical service volume.
3. **Financial Impact ($F$):** Logarithmic/sigmoid normalization of direct revenue at risk.
4. **Case Aging ($A$):** Linear scale reflecting unassigned waiting duration.
5. **Operational Criticality ($O$):** Inherent severity of the underlying service failure (e.g., core database outage vs. minor UI glitch).

$$\text{Priority Score} = w_S \cdot S + w_C \cdot C + w_F \cdot F + w_A \cdot A + w_O \cdot O$$
where $\sum w_i = 1.0$.

Each component generates an explainable driver string if its contribution exceeds threshold values (e.g., `SLA breach imminent in 18 minutes`, `Enterprise Tier 1 customer`).

---

## 5. Algorithmic Foundations

### Max-Heap Priority Queue
- **Purpose:** Maintain real-time sorting of thousands of active exceptions so the highest-priority item can be popped or inspected in $O(1)$ time.
- **Complexity:** Insertion $O(\log n)$, Pop Max $O(\log n)$, Peek Max $O(1)$.
- **Implementation:** Python's built-in `heapq` module (inverted for max-heap behavior) wrapping structured exception items.

### Hash Maps (Dictionaries)
- **Purpose:** Instant lookup of operational entities, SLA policies, and current state caches.
- **Complexity:** Average $O(1)$ lookup, insertion, and deletion.

### Sliding-Window Log / Ring Buffer
- **Purpose:** Compute rolling temporal metrics (e.g., SLA breach count in the trailing 60 minutes, rolling error rate).
- **Mechanism:** Maintain a monotonic timestamp-ordered double-ended queue (`collections.deque`). As new events arrive at $t_{now}$, evict all elements where $t < t_{now} - W$.

---

## 6. AWS Data Lake Architecture: S3, Glue, and Athena

### Amazon S3 Object Storage Layout
```
s3://switchyard-lake/
├── raw/
│   ├── operational_events/year=2026/month=01/day=15/
│   └── service_requests/
├── processed/
│   ├── fact_operational_events/year=2026/month=01/day=15/
│   ├── fact_sla_records/
│   └── dim_customer/
└── rejected/
    └── invalid_events/year=2026/month=01/day=15/
```

### AWS Glue Data Catalog
- Acts as a managed Hive Metastore for AWS. Stores table schemas, column types, physical S3 locations, and partition keys.
- Crawlers or explicit DDL statements register schema definitions without copying physical data.

### Amazon Athena
- Serverless distributed query engine based on Trino/Presto.
- Executes ANSI SQL directly against Parquet files in S3 using the Glue Catalog.
- Pricing model: Billed per Terabyte of data scanned ($5.00/TB). Partition pruning and columnar Parquet projection directly minimize operational cloud costs.

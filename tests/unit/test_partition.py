"""
Tests validating columnar Parquet partition creation and DuckDB querying.
"""
from pathlib import Path
import duckdb
from app.core.config import settings
from pipelines.partition import ParquetPartitionPipeline


def test_parquet_partition_structure(tmp_path: Path):
    pipeline = ParquetPartitionPipeline(processed_dir=tmp_path)
    sample_events = [
        {"event_id": "EVT-1", "customer_id": "C1", "service_id": "S1", "location_id": "L1", "timestamp": "2026-01-15T12:00:00+00:00", "status_code": 200, "duration_ms": 100, "payload_bytes": 500, "event_type": "TEST", "error_message": None},
        {"event_id": "EVT-2", "customer_id": "C1", "service_id": "S1", "location_id": "L1", "timestamp": "2026-01-16T15:30:00+00:00", "status_code": 500, "duration_ms": 2500, "payload_bytes": 1024, "event_type": "FAIL", "error_message": "Err"},
    ]

    out_dir = pipeline.transform_and_partition_events(sample_events)
    assert out_dir.exists()

    # Query with DuckDB using partition discovery
    con = duckdb.connect()
    rel = con.execute(f"SELECT COUNT(*), AVG(duration_ms) FROM read_parquet('{out_dir}/**/*.parquet', hive_partitioning=true)").fetchall()

    count, avg_duration = rel[0]
    assert count == 2
    assert avg_duration == 1300.0

    # Query with partition pruning filter
    filtered = con.execute(f"SELECT event_id FROM read_parquet('{out_dir}/**/*.parquet', hive_partitioning=true) WHERE day = '16'").fetchall()
    assert len(filtered) == 1
    assert filtered[0][0] == "EVT-2"

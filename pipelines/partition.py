"""
Dimensional transformation and columnar partitioned Parquet conversion pipeline for SWITCHYARD.
Takes validated event streams, enriches with temporal dimension attributes,
and writes structured fact and dimension Parquet files partitioned by year=YYYY/month=MM/day=DD/.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from app.core.config import settings
from app.core.logging import logger


class ParquetPartitionPipeline:
    def __init__(self, processed_dir: Path = None):
        self.processed_dir = processed_dir or settings.DATA_PROCESSED_DIR
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def transform_and_partition_events(self, valid_events: List[Dict[str, Any]]) -> Path:
        """
        Convert validated JSON event dictionaries into partitioned Parquet files:
        partition keys: year, month, day.
        """
        if not valid_events:
            logger.warning("No valid events provided to transform_and_partition_events.")
            return self.processed_dir

        df = pd.DataFrame(valid_events)

        # Parse timestamp and derive calendar partition keys
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df["year"] = df["timestamp"].dt.year.astype(str)
        df["month"] = df["timestamp"].dt.month.map("{:02d}".format)
        df["day"] = df["timestamp"].dt.day.map("{:02d}".format)

        # Additional analytical dimension attributes
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.day_name()
        df["is_weekend"] = df["timestamp"].dt.dayofweek >= 5

        # Define explicit PyArrow schema to guarantee column types
        schema = pa.schema([
            ("event_id", pa.string()),
            ("timestamp", pa.timestamp("ms", tz="UTC")),
            ("customer_id", pa.string()),
            ("service_id", pa.string()),
            ("location_id", pa.string()),
            ("event_type", pa.string()),
            ("duration_ms", pa.int64()),
            ("payload_bytes", pa.int64()),
            ("status_code", pa.int64()),
            ("error_message", pa.string()),
            ("year", pa.string()),
            ("month", pa.string()),
            ("day", pa.string()),
            ("hour", pa.int64()),
            ("day_of_week", pa.string()),
            ("is_weekend", pa.bool_()),
        ])

        table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
        events_output_dir = self.processed_dir / "fact_operational_event"
        events_output_dir.mkdir(parents=True, exist_ok=True)

        pq.write_to_dataset(
            table,
            root_path=str(events_output_dir),
            partition_cols=["year", "month", "day"],
            compression="SNAPPY",
            use_dictionary=True,
            version="2.6",
        )

        logger.info(f"Successfully wrote {len(df)} partitioned event records to {events_output_dir}")
        return events_output_dir

    def convert_reference_tables(self, raw_dir: Path = None):
        """
        Convert reference dimensions (Customers, Services, Locations, Agents) to Parquet.
        """
        raw_dir = raw_dir or settings.DATA_RAW_DIR

        dimensions = ["customers", "services", "locations", "agents"]
        for dim in dimensions:
            json_file = raw_dir / f"dim_{dim}.json"
            if json_file.exists():
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                df = pd.DataFrame(data)
                target_file = self.processed_dir / f"dim_{dim}.parquet"
                df.to_parquet(target_file, engine="pyarrow", compression="SNAPPY", index=False)
                logger.info(f"Converted {dim} to {target_file} ({len(df)} rows)")


def run_pipeline(raw_dir: Path = None, processed_dir: Path = None):
    from pipelines.validate import run_validation

    valid_records, metrics = run_validation(raw_dir=raw_dir)
    pipeline = ParquetPartitionPipeline(processed_dir=processed_dir)
    pipeline.transform_and_partition_events(valid_records)
    pipeline.convert_reference_tables(raw_dir=raw_dir)
    logger.info("Transformation and Parquet partitioning pipeline complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SWITCHYARD Parquet Transformation & Partitioning Pipeline")
    args = parser.parse_args()
    run_pipeline()

"""
Data Quality and Validation Engine for SWITCHYARD.
Inspects raw operational event streams, isolates anomalies, categorizes rejection codes,
and safely routes valid records to staging and invalid records to the quarantine sink.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from app.core.config import settings
from app.core.logging import logger


class DataQualityEngine:
    def __init__(
        self,
        valid_customer_ids: Optional[set] = None,
        valid_service_ids: Optional[set] = None,
        valid_location_ids: Optional[set] = None,
    ):
        self.valid_customer_ids = valid_customer_ids or set()
        self.valid_service_ids = valid_service_ids or set()
        self.valid_location_ids = valid_location_ids or set()

    def validate_events(self, raw_events: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Validate incoming event batch across multiple data-quality vectors:
        - Uniqueness of event_id
        - Non-null mandatory attributes
        - Valid ISO timestamp & non-future timestamp
        - Referential integrity against dimensions
        - Valid duration ranges (>= 0)
        - Valid status codes (100 - 599)
        """
        valid_records: List[Dict[str, Any]] = []
        rejected_records: List[Dict[str, Any]] = []

        seen_event_ids = set()
        now_utc = datetime.now(timezone.utc)

        error_counts: Dict[str, int] = {
            "ERR_DUPLICATE_ID": 0,
            "ERR_NULL_MANDATORY": 0,
            "ERR_INVALID_TIMESTAMP": 0,
            "ERR_FUTURE_TIMESTAMP": 0,
            "ERR_NEGATIVE_DURATION": 0,
            "ERR_INVALID_STATUS_CODE": 0,
            "ERR_FK_CUSTOMER_ORPHAN": 0,
            "ERR_FK_SERVICE_ORPHAN": 0,
            "ERR_FK_LOCATION_ORPHAN": 0,
        }

        for record in raw_events:
            reasons = []

            # 1. Uniqueness check
            event_id = record.get("event_id")
            if not event_id:
                reasons.append("ERR_NULL_MANDATORY")
            elif event_id in seen_event_ids:
                reasons.append("ERR_DUPLICATE_ID")
            else:
                seen_event_ids.add(event_id)

            # 2. Mandatory null checks
            cust_id = record.get("customer_id")
            srv_id = record.get("service_id")
            loc_id = record.get("location_id")
            ts_str = record.get("timestamp")

            if not cust_id or not srv_id or not loc_id or not ts_str:
                reasons.append("ERR_NULL_MANDATORY")

            # 3. Timestamp verification
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts > now_utc:
                        reasons.append("ERR_FUTURE_TIMESTAMP")
                except Exception:
                    reasons.append("ERR_INVALID_TIMESTAMP")

            # 4. Range and value checks
            duration = record.get("duration_ms")
            if duration is not None and duration < 0:
                reasons.append("ERR_NEGATIVE_DURATION")

            status_code = record.get("status_code")
            if status_code is None or status_code < 100 or status_code > 599:
                reasons.append("ERR_INVALID_STATUS_CODE")

            # 5. Referential Integrity (if reference catalogs loaded)
            if self.valid_customer_ids and cust_id and cust_id not in self.valid_customer_ids:
                reasons.append("ERR_FK_CUSTOMER_ORPHAN")
            if self.valid_service_ids and srv_id and srv_id not in self.valid_service_ids:
                reasons.append("ERR_FK_SERVICE_ORPHAN")
            if self.valid_location_ids and loc_id and loc_id not in self.valid_location_ids:
                reasons.append("ERR_FK_LOCATION_ORPHAN")

            if reasons:
                # Quarantined record with audit metadata
                quarantine_entry = {
                    "raw_record": record,
                    "rejection_reasons": reasons,
                    "quarantined_at": now_utc.isoformat(),
                }
                rejected_records.append(quarantine_entry)
                for r in reasons:
                    error_counts[r] = error_counts.get(r, 0) + 1
            else:
                valid_records.append(record)

        summary_metrics = {
            "rows_processed": len(raw_events),
            "rows_valid": len(valid_records),
            "rows_rejected": len(rejected_records),
            "acceptance_rate_pct": round(len(valid_records) / max(1, len(raw_events)) * 100.0, 2),
            "error_distribution": error_counts,
        }

        return valid_records, rejected_records, summary_metrics


def run_validation(raw_dir: Path = None, rejected_dir: Path = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    raw_dir = raw_dir or settings.DATA_RAW_DIR
    rejected_dir = rejected_dir or settings.DATA_REJECTED_DIR
    rejected_dir.mkdir(parents=True, exist_ok=True)

    events_path = raw_dir / "raw_operational_events.json"
    if not events_path.exists():
        raise FileNotFoundError(f"Raw operational events file not found at {events_path}")

    with open(events_path, "r", encoding="utf-8") as f:
        raw_events = json.load(f)

    # Load reference IDs for referential integrity checking
    valid_customers = set()
    cust_file = raw_dir / "dim_customers.json"
    if cust_file.exists():
        with open(cust_file, "r", encoding="utf-8") as f:
            valid_customers = {c["customer_id"] for c in json.load(f)}

    valid_services = set()
    srv_file = raw_dir / "dim_services.json"
    if srv_file.exists():
        with open(srv_file, "r", encoding="utf-8") as f:
            valid_services = {s["service_id"] for s in json.load(f)}

    valid_locations = set()
    loc_file = raw_dir / "dim_locations.json"
    if loc_file.exists():
        with open(loc_file, "r", encoding="utf-8") as f:
            valid_locations = {l["location_id"] for l in json.load(f)}

    dq = DataQualityEngine(
        valid_customer_ids=valid_customers,
        valid_service_ids=valid_services,
        valid_location_ids=valid_locations
    )

    valid_records, rejected_records, metrics = dq.validate_events(raw_events)

    # Save quarantine output
    quarantine_path = rejected_dir / "quarantined_events.json"
    with open(quarantine_path, "w", encoding="utf-8") as f:
        json.dump(rejected_records, f, indent=2)

    # Save metrics report
    metrics_path = rejected_dir / "dq_metrics_summary.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    logger.info(f"DQ Complete: Processed={metrics['rows_processed']}, Valid={metrics['rows_valid']}, Rejected={metrics['rows_rejected']} ({metrics['acceptance_rate_pct']}%)")
    return valid_records, metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SWITCHYARD Data Quality and Validation Engine")
    args = parser.parse_args()
    run_validation()

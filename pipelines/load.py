"""
Loader pipeline stage: Populates operational serving database (PostgreSQL/SQLite)
from validated events and reference dimensions.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any
from app.core.config import settings
from app.core.logging import logger
from app.models.entities import Customer, Service, Location, OperationalEvent
from app.repositories.database import init_db, get_db_context


def load_reference_data(raw_dir: Path = None):
    raw_dir = raw_dir or settings.DATA_RAW_DIR
    init_db()

    with get_db_context() as db:
        # 1. Customers
        cust_file = raw_dir / "dim_customers.json"
        if cust_file.exists():
            with open(cust_file, "r", encoding="utf-8") as f:
                custs = json.load(f)
            for c in custs:
                if not db.query(Customer).filter_by(customer_id=c["customer_id"]).first():
                    db.add(Customer(**c))

        # 2. Services
        srv_file = raw_dir / "dim_services.json"
        if srv_file.exists():
            with open(srv_file, "r", encoding="utf-8") as f:
                srvs = json.load(f)
            for s in srvs:
                if not db.query(Service).filter_by(service_id=s["service_id"]).first():
                    db.add(Service(**s))

        # 3. Locations
        loc_file = raw_dir / "dim_locations.json"
        if loc_file.exists():
            with open(loc_file, "r", encoding="utf-8") as f:
                locs = json.load(f)
            for l in locs:
                if not db.query(Location).filter_by(location_id=l["location_id"]).first():
                    db.add(Location(**l))

    logger.info("Operational database loaded reference dimensions.")


def load_operational_events(valid_records: List[Dict[str, Any]], batch_size: int = 500):
    init_db()
    with get_db_context() as db:
        count = 0
        for r in valid_records:
            if not db.query(OperationalEvent).filter_by(event_id=r["event_id"]).first():
                evt = OperationalEvent(
                    event_id=r["event_id"],
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    customer_id=r["customer_id"],
                    service_id=r["service_id"],
                    location_id=r["location_id"],
                    event_type=r["event_type"],
                    duration_ms=r.get("duration_ms"),
                    payload_bytes=r.get("payload_bytes"),
                    status_code=r["status_code"],
                    error_message=r.get("error_message"),
                )
                db.add(evt)
                count += 1
                if count % batch_size == 0:
                    db.flush()

    logger.info(f"Loaded {count} operational events into serving database.")


def run_loader():
    from pipelines.validate import run_validation
    valid_records, _ = run_validation()
    load_reference_data()
    load_operational_events(valid_records)


if __name__ == "__main__":
    run_loader()

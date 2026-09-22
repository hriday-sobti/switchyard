"""
Deterministic high-volume synthetic enterprise data generator for SWITCHYARD.
Generates interconnected graphs of Customers, Services, Locations, Agents,
Operational Events, SLA Records, and Exceptions with configurable quality defect injection.
"""
import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Any
from app.core.config import settings
from app.core.logging import logger

INDUSTRIES = ["Finance", "Healthcare", "E-Commerce", "Telecommunications", "Logistics", "Energy"]
CUSTOMER_TIERS = ["Enterprise", "Commercial", "Retail"]
CONTRACT_TIERS = ["Gold", "Silver", "Bronze"]

SERVICES_MASTER = [
    {"service_id": "SRV-1001", "service_name": "Realtime Settlement Engine", "service_category": "Core Banking", "tier_level": 1, "default_sla_minutes": 60},
    {"service_id": "SRV-1002", "service_name": "Card Authorization Gateway", "service_category": "Payments", "tier_level": 1, "default_sla_minutes": 30},
    {"service_id": "SRV-1003", "service_name": "KYC Identity Verifier", "service_category": "Compliance", "tier_level": 2, "default_sla_minutes": 180},
    {"service_id": "SRV-1004", "service_name": "Batch Reconciliation Processor", "service_category": "Operations", "tier_level": 2, "default_sla_minutes": 360},
    {"service_id": "SRV-1005", "service_name": "Customer Notification Hub", "service_category": "Messaging", "tier_level": 3, "default_sla_minutes": 720},
    {"service_id": "SRV-1006", "service_name": "Document Storage Repository", "service_category": "Storage", "tier_level": 3, "default_sla_minutes": 1440},
]

LOCATIONS_MASTER = [
    {"location_id": "LOC-USE-01", "region": "US-East", "datacenter_zone": "us-east-1a", "country": "USA"},
    {"location_id": "LOC-USE-02", "region": "US-East", "datacenter_zone": "us-east-1b", "country": "USA"},
    {"location_id": "LOC-USW-01", "region": "US-West", "datacenter_zone": "us-west-2a", "country": "USA"},
    {"location_id": "LOC-EUC-01", "region": "EU-Central", "datacenter_zone": "eu-central-1a", "country": "Germany"},
    {"location_id": "LOC-APS-01", "region": "APAC-South", "datacenter_zone": "ap-south-1a", "country": "India"},
]

TEAMS_MASTER = ["Core Infrastructure", "Payment Operations", "Triage Tier-1", "Security Escalations", "Database Reliability"]


class SyntheticDataGenerator:
    def __init__(self, seed: int = 42, bad_data_rate: float = 0.02):
        self.seed = seed
        self.bad_data_rate = bad_data_rate
        self.rng = random.Random(seed)

    def generate_reference_data(self, customer_count: int = 50) -> Dict[str, List[Dict[str, Any]]]:
        """Generate deterministic reference entities."""
        customers = []
        for i in range(1, customer_count + 1):
            tier = self.rng.choices(CUSTOMER_TIERS, weights=[0.2, 0.4, 0.4])[0]
            contract = "Gold" if tier == "Enterprise" else ("Silver" if tier == "Commercial" else "Bronze")
            customers.append({
                "customer_id": f"CUST-{i:06d}",
                "customer_name": f"Enterprise Account {i:03d}" if tier == "Enterprise" else f"Client Corp {i:04d}",
                "tier": tier,
                "contract_sla_tier": contract,
                "industry": self.rng.choice(INDUSTRIES),
            })

        agents = []
        for i in range(1, 31):
            agents.append({
                "agent_id": f"AGT-{i:04d}",
                "agent_name": f"Operator {i:02d}",
                "team_name": self.rng.choice(TEAMS_MASTER),
                "skill_level": self.rng.randint(1, 5),
                "shift": self.rng.choice(["Morning", "Afternoon", "Night"]),
            })

        return {
            "customers": customers,
            "services": SERVICES_MASTER,
            "locations": LOCATIONS_MASTER,
            "agents": agents,
        }

    def generate_operational_stream(
        self,
        ref_data: Dict[str, List[Dict[str, Any]]],
        event_count: int = 1000,
        start_date: datetime = None,
        duration_days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Generate operational events with controlled defect injection.
        """
        if start_date is None:
            start_date = datetime(2026, 1, 15, 0, 0, 0, tzinfo=timezone.utc)

        events = []
        customers = ref_data["customers"]
        services = ref_data["services"]
        locations = ref_data["locations"]

        seen_event_ids = []

        for i in range(1, event_count + 1):
            inject_defect = self.rng.random() < self.bad_data_rate

            offset_seconds = self.rng.randint(0, duration_days * 86400)
            event_time = start_date + timedelta(seconds=offset_seconds)
            cust = self.rng.choice(customers)
            srv = self.rng.choice(services)
            loc = self.rng.choice(locations)

            event_id = f"EVT-{i:08d}"
            status_code = self.rng.choices([200, 201, 400, 404, 500, 503, 504], weights=[0.85, 0.05, 0.03, 0.02, 0.03, 0.01, 0.01])[0]
            duration_ms = self.rng.randint(15, 1200) if status_code < 400 else self.rng.randint(1500, 15000)
            payload_bytes = self.rng.randint(256, 1048576)

            event_record = {
                "event_id": event_id,
                "timestamp": event_time.isoformat(),
                "customer_id": cust["customer_id"],
                "service_id": srv["service_id"],
                "location_id": loc["location_id"],
                "event_type": "PROCESSING_FAILED" if status_code >= 500 else ("REQUEST_RECEIVED" if self.rng.random() < 0.5 else "STATUS_CHANGE"),
                "duration_ms": duration_ms,
                "payload_bytes": payload_bytes,
                "status_code": status_code,
                "error_message": f"Service exception HTTP {status_code}" if status_code >= 400 else None,
            }

            if inject_defect:
                defect_type = self.rng.choice([
                    "DUPLICATE_ID",
                    "NULL_CUSTOMER",
                    "FUTURE_TIMESTAMP",
                    "NEGATIVE_DURATION",
                    "INVALID_STATUS",
                    "ORPHAN_SERVICE",
                ])
                if defect_type == "DUPLICATE_ID" and seen_event_ids:
                    event_record["event_id"] = self.rng.choice(seen_event_ids)
                elif defect_type == "NULL_CUSTOMER":
                    event_record["customer_id"] = None
                elif defect_type == "FUTURE_TIMESTAMP":
                    event_record["timestamp"] = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
                elif defect_type == "NEGATIVE_DURATION":
                    event_record["duration_ms"] = -self.rng.randint(100, 5000)
                elif defect_type == "INVALID_STATUS":
                    event_record["status_code"] = 999
                elif defect_type == "ORPHAN_SERVICE":
                    event_record["service_id"] = "SRV-NONEXISTENT-9999"

            seen_event_ids.append(event_record["event_id"])
            events.append(event_record)

        return events


def run_generation(scale: int = 1000, bad_data_rate: float = 0.02, output_dir: Path = None):
    output_dir = output_dir or settings.DATA_RAW_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting synthetic generation: Scale={scale}, BadDataRate={bad_data_rate}")
    generator = SyntheticDataGenerator(seed=42, bad_data_rate=bad_data_rate)

    ref_data = generator.generate_reference_data(customer_count=max(20, scale // 50))
    events = generator.generate_operational_stream(ref_data, event_count=scale)

    for name, data in ref_data.items():
        ref_path = output_dir / f"dim_{name}.json"
        with open(ref_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    events_path = output_dir / "raw_operational_events.json"
    with open(events_path, "w", encoding="utf-8") as f:
        json.dump(events, f)

    logger.info(f"Generation complete. Saved {len(events)} events and reference tables to {output_dir}")
    return ref_data, events


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SWITCHYARD Synthetic Enterprise Data Generator")
    parser.add_argument("--scale", type=int, default=1000, help="Number of operational events to generate (e.g. 1000, 100000, 1000000)")
    parser.add_argument("--bad-data-rate", type=float, default=0.02, help="Percentage of controlled defects (default 0.02 = 2 percent)")
    args = parser.parse_args()

    run_generation(scale=args.scale, bad_data_rate=args.bad_data_rate)

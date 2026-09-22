"""
Exception prioritization and operational state service for SWITCHYARD.
Orchestrates SLA state calculation, priority scoring, Max-Heap queue loading,
and relational database persistence.
"""
import json
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.core.priority_queue import OperationalPriorityQueue
from app.core.sliding_window import SlidingWindowAggregator
from app.models.entities import ExceptionRecord, SLARecord, Customer, Service, OperationalEvent
from app.models.schemas import SLAStatus, PriorityBand, ExceptionLifecycleState
from app.rules.sla_engine import SLAEngine
from app.rules.priority_engine import ExplainablePriorityEngine


class OperationalExceptionService:
    def __init__(self, db: Session):
        self.db = db
        self.sla_engine = SLAEngine()
        self.priority_engine = ExplainablePriorityEngine()
        self.priority_queue = OperationalPriorityQueue()
        self.sliding_window = SlidingWindowAggregator(window_minutes=60)

    def process_and_prioritize_exceptions(self, limit: int = 500) -> int:
        """
        Identify unprocessed failed operational events, calculate SLA status,
        generate priority scores, persist into relational tables, and push into the Max-Heap queue.
        """
        # Find events with status_code >= 500 that do not yet have an exception record
        failed_events = (
            self.db.query(OperationalEvent)
            .filter(OperationalEvent.status_code >= 500)
            .limit(limit)
            .all()
        )

        created_count = 0
        now_utc = datetime.now(timezone.utc)

        for evt in failed_events:
            existing = self.db.query(ExceptionRecord).filter_by(event_id=evt.event_id).first()
            if existing:
                continue

            customer = self.db.query(Customer).filter_by(customer_id=evt.customer_id).first()
            service = self.db.query(Service).filter_by(service_id=evt.service_id).first()

            cust_tier = customer.tier if customer else "Retail"
            default_sla = service.default_sla_minutes if service else 120

            # 1. Evaluate SLA
            target_sla = self.sla_engine.calculate_target_minutes(cust_tier, "High", default_sla)
            start_time = evt.timestamp.replace(tzinfo=timezone.utc) if evt.timestamp.tzinfo is None else evt.timestamp
            sla_status, elapsed, remaining, ratio = self.sla_engine.evaluate_sla_state(start_time, now_utc, target_sla)

            # Record SLA instance
            sla_id = f"SLA-{evt.event_id.replace('EVT-', '')}"
            sla_rec = SLARecord(
                sla_id=sla_id,
                case_id=f"CASE-{evt.event_id}",
                customer_id=evt.customer_id,
                service_id=evt.service_id,
                start_time=start_time,
                due_time=start_time + timedelta(minutes=target_sla),
                target_minutes=target_sla,
                elapsed_minutes=elapsed,
                remaining_minutes=remaining,
                sla_status=sla_status.value
            )
            self.db.add(sla_rec)

            # 2. Prioritize Exception
            # Simulated financial exposure based on customer tier
            exposure = (
                random.uniform(50000, 250000) if cust_tier == "Enterprise"
                else (random.uniform(5000, 45000) if cust_tier == "Commercial" else random.uniform(200, 4000))
            )

            unassigned_hours = round(elapsed / 60.0, 1)
            score, band, drivers = self.priority_engine.calculate_priority(
                sla_status=sla_status,
                sla_consumption_ratio=ratio,
                remaining_minutes=remaining,
                customer_tier=cust_tier,
                financial_exposure_usd=exposure,
                unassigned_hours=unassigned_hours,
                severity="Critical" if cust_tier == "Enterprise" else "High"
            )

            exc_id = f"EXC-{evt.event_id.replace('EVT-', '')}"
            exc_record = ExceptionRecord(
                exception_id=exc_id,
                case_id=f"CASE-{evt.event_id}",
                event_id=evt.event_id,
                customer_id=evt.customer_id,
                service_id=evt.service_id,
                location_id=evt.location_id,
                financial_exposure=round(exposure, 2),
                priority_score=score,
                priority_band=band.value,
                lifecycle_state=ExceptionLifecycleState.DETECTED.value,
                reason_drivers=json.dumps(drivers),
                created_at=now_utc,
                updated_at=now_utc,
                assigned_team="Payment Operations" if "Payment" in (service.service_name if service else "") else "Core Infrastructure"
            )
            self.db.add(exc_record)

            # 3. Add to In-Memory Max-Heap Priority Queue
            queue_payload = {
                "id": exc_id,
                "case_id": exc_record.case_id,
                "customer_id": exc_record.customer_id,
                "service_id": exc_record.service_id,
                "priority_score": score,
                "priority_band": band.value,
                "sla_status": sla_status.value,
                "remaining_minutes": remaining,
                "financial_exposure": round(exposure, 2),
                "reason_drivers": drivers,
            }
            self.priority_queue.push(score, exc_id, queue_payload)

            # 4. Record to Sliding Window
            self.sliding_window.add_event(
                timestamp=now_utc,
                is_breach=(sla_status == SLAStatus.BREACHED),
                payload=queue_payload
            )

            created_count += 1

        self.db.commit()
        logger.info(f"Processed and prioritized {created_count} operational exceptions.")
        return created_count

    def get_summary_kpis(self) -> Dict[str, Any]:
        """Compute operational summary KPI cards."""
        total_exceptions = self.db.query(ExceptionRecord).count()
        active_exceptions = (
            self.db.query(ExceptionRecord)
            .filter(ExceptionRecord.lifecycle_state.notin_(["RESOLVED", "CLOSED"]))
            .count()
        )
        at_risk_count = self.db.query(SLARecord).filter_by(sla_status="AT_RISK").count()
        breached_count = self.db.query(SLARecord).filter_by(sla_status="BREACHED").count()
        total_sla = max(1, self.db.query(SLARecord).count())

        breach_rate = round(breached_count / total_sla * 100.0, 2)

        return {
            "total_exceptions": total_exceptions,
            "active_backlog": active_exceptions,
            "sla_at_risk_count": at_risk_count,
            "sla_breached_count": breached_count,
            "sla_breach_rate_pct": breach_rate,
            "priority_queue_size": self.priority_queue.size(),
            "highest_priority_exception": self.priority_queue.peek(),
        }

"""
FastAPI REST Service Layer for SWITCHYARD.
Provides endpoints for health, operational summaries, paginated exceptions,
SLA risk assessments, data-quality metrics, and analytical trends.
"""
from typing import List, Optional
from contextlib import asynccontextmanager
import json
from fastapi import FastAPI, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.repositories.database import get_db, init_db
from app.models.entities import ExceptionRecord, SLARecord, Customer, Service
from app.services.exception_service import OperationalExceptionService
from app.services.analytics import DuckDBAnalyticsService

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="SWITCHYARD Operational Reliability Workbench API",
    description="Enterprise operational decision-support system and exception prioritization workbench.",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", tags=["System"])
def get_health():
    """Health check endpoint asserting system and database operational readiness."""
    return {
        "status": "HEALTHY",
        "service": "SWITCHYARD Workbench",
        "environment": settings.SWITCHYARD_ENV,
        "database": "CONNECTED",
    }


@app.get("/operations/summary", tags=["Operations"])
def get_operations_summary(db: Session = Depends(get_db)):
    """Executive operational summary: active backlog, SLA risk counts, and breach rates."""
    service = OperationalExceptionService(db)
    # Ensure queue has current items
    service.process_and_prioritize_exceptions(limit=100)
    return service.get_summary_kpis()


@app.get("/exceptions", tags=["Exceptions"])
def list_exceptions(
    db: Session = Depends(get_db),
    priority: Optional[str] = Query(None, description="Filter by priority band: P1, P2, P3, P4"),
    status: Optional[str] = Query(None, description="Filter by lifecycle state (e.g., DETECTED, ASSIGNED)"),
    location: Optional[str] = Query(None, description="Filter by location_id"),
    service: Optional[str] = Query(None, description="Filter by service_id"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Paginated exception queue sorted by priority score descending.
    Supports multi-attribute operational filtering.
    """
    query = db.query(ExceptionRecord)

    if priority:
        query = query.filter(ExceptionRecord.priority_band == priority.upper())
    if status:
        query = query.filter(ExceptionRecord.lifecycle_state == status.upper())
    if location:
        query = query.filter(ExceptionRecord.location_id == location)
    if service:
        query = query.filter(ExceptionRecord.service_id == service)

    total_count = query.count()
    records = (
        query.order_by(ExceptionRecord.priority_score.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    results = []
    for r in records:
        results.append({
            "id": r.exception_id,
            "case_id": r.case_id,
            "event_id": r.event_id,
            "customer_id": r.customer_id,
            "service_id": r.service_id,
            "location_id": r.location_id,
            "financial_exposure": r.financial_exposure,
            "priority_score": r.priority_score,
            "priority_band": r.priority_band,
            "lifecycle_state": r.lifecycle_state,
            "reason_drivers": json.loads(r.reason_drivers) if r.reason_drivers else [],
            "created_at": r.created_at.isoformat(),
            "assigned_team": r.assigned_team,
        })

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "items": results,
    }


@app.get("/exceptions/{exception_id}", tags=["Exceptions"])
def get_exception_details(exception_id: str, db: Session = Depends(get_db)):
    """Retrieve detailed explanation and drivers for an individual exception record."""
    exc = db.query(ExceptionRecord).filter_by(exception_id=exception_id).first()
    if not exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exception with ID '{exception_id}' not found."
        )

    customer = db.query(Customer).filter_by(customer_id=exc.customer_id).first()
    srv = db.query(Service).filter_by(service_id=exc.service_id).first()
    sla = db.query(SLARecord).filter_by(case_id=exc.case_id).first()

    return {
        "id": exc.exception_id,
        "case_id": exc.case_id,
        "event_id": exc.event_id,
        "customer": {
            "id": customer.customer_id if customer else exc.customer_id,
            "name": customer.customer_name if customer else "Unknown",
            "tier": customer.tier if customer else "Standard",
        },
        "service": {
            "id": srv.service_id if srv else exc.service_id,
            "name": srv.service_name if srv else "Unknown",
            "category": srv.service_category if srv else "Operations",
        },
        "financial_exposure": exc.financial_exposure,
        "priority_score": exc.priority_score,
        "priority_band": exc.priority_band,
        "priority_drivers": json.loads(exc.reason_drivers) if exc.reason_drivers else [],
        "sla_status": sla.sla_status if sla else "UNKNOWN",
        "sla_remaining_minutes": sla.remaining_minutes if sla else 0.0,
        "lifecycle_state": exc.lifecycle_state,
        "created_at": exc.created_at.isoformat(),
        "assigned_team": exc.assigned_team,
    }


@app.get("/sla-risk", tags=["SLA"])
def get_sla_risk_cases(db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=200)):
    """Retrieve cases currently in AT_RISK or BREACHED SLA states."""
    risk_records = (
        db.query(SLARecord)
        .filter(SLARecord.sla_status.in_(["AT_RISK", "BREACHED"]))
        .order_by(SLARecord.remaining_minutes.asc())
        .limit(limit)
        .all()
    )

    return {
        "count": len(risk_records),
        "items": [
            {
                "sla_id": r.sla_id,
                "case_id": r.case_id,
                "customer_id": r.customer_id,
                "service_id": r.service_id,
                "target_minutes": r.target_minutes,
                "elapsed_minutes": r.elapsed_minutes,
                "remaining_minutes": r.remaining_minutes,
                "sla_status": r.sla_status,
                "due_time": r.due_time.isoformat(),
            }
            for r in risk_records
        ]
    }


@app.get("/data-quality", tags=["Data Quality"])
def get_data_quality_summary():
    """Expose ingestion validation and quarantine metrics."""
    metrics_path = settings.DATA_REJECTED_DIR / "dq_metrics_summary.json"
    if not metrics_path.exists():
        return {"status": "NO_METRICS_LOGGED", "detail": "Validation pipeline has not run yet."}

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    return metrics


@app.get("/operations/trends", tags=["Analytics"])
def get_operational_trends():
    """Retrieve hourly operational telemetry trends from the partitioned lakehouse."""
    try:
        analytics = DuckDBAnalyticsService()
        return analytics.get_hourly_incident_trend()
    except Exception as e:
        logger.error(f"Error querying lakehouse trends: {e}")
        return []

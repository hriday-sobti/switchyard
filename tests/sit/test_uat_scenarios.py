"""
Automated User Acceptance Testing (UAT) and System Integration Testing (SIT) Suite.
Validates the end-to-end business narrative of SWITCHYARD.
"""
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.api.main import app
from app.repositories.database import get_db_context
from app.models.entities import ExceptionRecord, SLARecord, Customer, Service, OperationalEvent
from app.services.exception_service import OperationalExceptionService

client = TestClient(app)


def test_uat_01_proactive_sla_breach_detection():
    """
    UAT-01: Operations manager identifies high-risk cases approaching SLA breach.
    """
    response = client.get("/sla-risk")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    # Verify records have valid SLA fields
    if data["items"]:
        item = data["items"][0]
        assert item["sla_status"] in ["AT_RISK", "BREACHED"]
        assert "remaining_minutes" in item


def test_uat_02_priority_reasons_transparency():
    """
    UAT-02: Lead investigates an exception to inspect driver reasons explaining priority.
    """
    response = client.get("/exceptions?limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) > 0

    first_item = data["items"][0]
    exc_id = first_item["id"]

    detail_resp = client.get(f"/exceptions/{exc_id}")
    assert detail_resp.status_code == 200
    details = detail_resp.json()

    assert "priority_drivers" in details
    assert len(details["priority_drivers"]) > 0
    # Every driver must be human-readable explanatory text
    assert isinstance(details["priority_drivers"][0], str)
    assert len(details["priority_drivers"][0]) > 5


def test_uat_03_kpi_to_record_drilldown():
    """
    UAT-03: Drill down from total backlog KPI to underlying exception records.
    """
    summary_resp = client.get("/operations/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    total_exceptions = summary["total_exceptions"]

    # Drill down to listing
    list_resp = client.get(f"/exceptions?limit={min(100, max(1, total_exceptions))}")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] == total_exceptions


def test_uat_04_bottleneck_isolation():
    """
    UAT-04: Confirm bottleneck analytics identify failure distribution.
    """
    from app.services.analytics import DuckDBAnalyticsService
    analytics = DuckDBAnalyticsService()
    bottlenecks = analytics.get_location_bottlenecks()
    assert len(bottlenecks) > 0
    assert bottlenecks[0]["failure_rank"] == 1


def test_uat_05_data_quality_quarantine_traceability():
    """
    UAT-05: Ensure rejected records are audited in quarantine summary.
    """
    resp = client.get("/data-quality")
    assert resp.status_code == 200
    data = resp.json()
    assert "rows_processed" in data
    assert "rows_valid" in data
    assert "rows_rejected" in data
    assert data["rows_rejected"] >= 0
    assert "error_distribution" in data

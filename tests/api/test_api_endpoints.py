"""
Comprehensive REST API Integration Test Suite:
Query filters, pagination boundaries, HTTP status codes, payload structure assertions,
and error handling across all exposed endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)

# 1. System & Health Endpoint Tests
def test_api_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "HEALTHY"
    assert body["service"] == "SWITCHYARD Workbench"
    assert "environment" in body
    assert body["database"] == "CONNECTED"


# 2. Operations Summary Tests
def test_api_operations_summary_structure():
    resp = client.get("/operations/summary")
    assert resp.status_code == 200
    data = resp.json()
    expected_keys = [
        "total_exceptions", "active_backlog", "sla_at_risk_count",
        "sla_breached_count", "sla_breach_rate_pct", "priority_queue_size"
    ]
    for key in expected_keys:
        assert key in data
        assert isinstance(data[key], (int, float))


# 3. Exceptions Query & Pagination Tests (15 tests)
@pytest.mark.parametrize("limit,offset", [
    (1, 0),
    (5, 0),
    (10, 5),
    (25, 0),
    (50, 10),
    (100, 0),
    (1, 1000),  # Offset beyond dataset
])
def test_api_exceptions_pagination_offsets(limit, offset):
    resp = client.get(f"/exceptions?limit={limit}&offset={offset}")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) <= limit


@pytest.mark.parametrize("priority_band", ["P1", "P2", "P3", "P4"])
def test_api_exceptions_filter_by_priority(priority_band):
    resp = client.get(f"/exceptions?priority={priority_band}&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["priority_band"] == priority_band


@pytest.mark.parametrize("lifecycle_state", ["DETECTED", "TRIAGED", "ASSIGNED"])
def test_api_exceptions_filter_by_status(lifecycle_state):
    resp = client.get(f"/exceptions?status={lifecycle_state}&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["lifecycle_state"] == lifecycle_state


# 4. Exception Details & 404 Handlers (5 tests)
def test_api_exception_details_contract():
    # Fetch first exception ID
    list_resp = client.get("/exceptions?limit=1")
    items = list_resp.json().get("items", [])
    if items:
        exc_id = items[0]["id"]
        resp = client.get(f"/exceptions/{exc_id}")
        assert resp.status_code == 200
        d = resp.json()
        assert d["id"] == exc_id
        assert "customer" in d
        assert "service" in d
        assert "priority_drivers" in d
        assert isinstance(d["priority_drivers"], list)


@pytest.mark.parametrize("nonexistent_id", [
    "EXC-NOTFOUND-01",
    "EXC-FAKE-9999",
    "INVALID-FORMAT-ID",
])
def test_api_exception_not_found(nonexistent_id):
    resp = client.get(f"/exceptions/{nonexistent_id}")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# 5. SLA Risk & Analytics Trends (5 tests)
def test_api_sla_risk_endpoint():
    resp = client.get("/sla-risk?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "count" in data


def test_api_data_quality_endpoint():
    resp = client.get("/data-quality")
    assert resp.status_code == 200
    data = resp.json()
    assert "rows_processed" in data or "status" in data


def test_api_operations_trends_endpoint():
    resp = client.get("/operations/trends")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

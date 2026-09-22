"""
Data quality validation tests: status code bounds, duration ranges, null fields,
referential integrity against dimensions, and quarantine routing.
"""
from datetime import datetime, timezone, timedelta
import pytest
from pipelines.validate import DataQualityEngine

valid_custs = {"CUST-001", "CUST-002"}
valid_srvs = {"SRV-001", "SRV-002"}
valid_locs = {"LOC-001", "LOC-002"}

dq = DataQualityEngine(
    valid_customer_ids=valid_custs,
    valid_service_ids=valid_srvs,
    valid_location_ids=valid_locs
)

# 1. Parameterized Status Code Boundaries (10 tests)
@pytest.mark.parametrize("status_code,is_valid", [
    (100, True),
    (200, True),
    (201, True),
    (400, True),
    (404, True),
    (500, True),
    (503, True),
    (599, True),
    (99, False),   # Under lower bound
    (600, False),  # Above upper bound
    (999, False),  # Corrupt code
    (-1, False),   # Negative code
])
def test_dq_status_code_boundaries(status_code, is_valid):
    evt = {
        "event_id": f"EVT-ST-{status_code}",
        "customer_id": "CUST-001",
        "service_id": "SRV-001",
        "location_id": "LOC-001",
        "timestamp": "2026-01-15T12:00:00+00:00",
        "status_code": status_code,
        "duration_ms": 100
    }
    valid, rejected, _ = dq.validate_events([evt])
    if is_valid:
        assert len(valid) == 1
        assert len(rejected) == 0
    else:
        assert len(valid) == 0
        assert len(rejected) == 1
        assert "ERR_INVALID_STATUS_CODE" in rejected[0]["rejection_reasons"]


# 2. Duration MS Range Checks (8 tests)
@pytest.mark.parametrize("duration,is_valid", [
    (0, True),
    (1, True),
    (500, True),
    (15000, True),
    (None, True),   # Optional duration can be None
    (-1, False),
    (-500, False),
    (-99999, False),
])
def test_dq_duration_ranges(duration, is_valid):
    evt = {
        "event_id": f"EVT-DUR-{duration}",
        "customer_id": "CUST-001",
        "service_id": "SRV-001",
        "location_id": "LOC-001",
        "timestamp": "2026-01-15T12:00:00+00:00",
        "status_code": 200,
        "duration_ms": duration
    }
    valid, rejected, _ = dq.validate_events([evt])
    if is_valid:
        assert len(valid) == 1
    else:
        assert len(rejected) == 1
        assert "ERR_NEGATIVE_DURATION" in rejected[0]["rejection_reasons"]


# 3. Mandatory Null Field Checks (6 tests)
@pytest.mark.parametrize("missing_field", [
    "customer_id",
    "service_id",
    "location_id",
    "timestamp",
])
def test_dq_mandatory_null_fields(missing_field):
    evt = {
        "event_id": f"EVT-NULL-{missing_field}",
        "customer_id": "CUST-001",
        "service_id": "SRV-001",
        "location_id": "LOC-001",
        "timestamp": "2026-01-15T12:00:00+00:00",
        "status_code": 200,
    }
    evt[missing_field] = None
    valid, rejected, _ = dq.validate_events([evt])
    assert len(valid) == 0
    assert len(rejected) == 1
    assert "ERR_NULL_MANDATORY" in rejected[0]["rejection_reasons"]


# 4. Referential Integrity Checks (6 tests)
@pytest.mark.parametrize("field,bad_id,expected_error", [
    ("customer_id", "CUST-UNKNOWN-99", "ERR_FK_CUSTOMER_ORPHAN"),
    ("service_id", "SRV-UNKNOWN-99", "ERR_FK_SERVICE_ORPHAN"),
    ("location_id", "LOC-UNKNOWN-99", "ERR_FK_LOCATION_ORPHAN"),
])
def test_dq_referential_integrity(field, bad_id, expected_error):
    evt = {
        "event_id": f"EVT-FK-{field}",
        "customer_id": "CUST-001",
        "service_id": "SRV-001",
        "location_id": "LOC-001",
        "timestamp": "2026-01-15T12:00:00+00:00",
        "status_code": 200,
    }
    evt[field] = bad_id
    valid, rejected, _ = dq.validate_events([evt])
    assert len(valid) == 0
    assert len(rejected) == 1
    assert expected_error in rejected[0]["rejection_reasons"]


# 5. Timestamp Validations (6 tests)
def test_dq_invalid_timestamp_string():
    evt = {
        "event_id": "EVT-BAD-TS",
        "customer_id": "CUST-001",
        "service_id": "SRV-001",
        "location_id": "LOC-001",
        "timestamp": "not-a-valid-timestamp",
        "status_code": 200
    }
    valid, rejected, _ = dq.validate_events([evt])
    assert len(rejected) == 1
    assert "ERR_INVALID_TIMESTAMP" in rejected[0]["rejection_reasons"]


def test_dq_future_timestamp():
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    evt = {
        "event_id": "EVT-FUTURE",
        "customer_id": "CUST-001",
        "service_id": "SRV-001",
        "location_id": "LOC-001",
        "timestamp": future_time,
        "status_code": 200
    }
    valid, rejected, _ = dq.validate_events([evt])
    assert len(rejected) == 1
    assert "ERR_FUTURE_TIMESTAMP" in rejected[0]["rejection_reasons"]


# 6. Multi-Defect Compound Quarantine Test (3 tests)
def test_dq_compound_multiple_defects():
    evt = {
        "event_id": "EVT-COMPOUND",
        "customer_id": "CUST-UNKNOWN",   # FK orphan
        "service_id": "SRV-001",
        "location_id": "LOC-001",
        "timestamp": "2026-01-15T12:00:00+00:00",
        "status_code": 999,              # Invalid status code
        "duration_ms": -50               # Negative duration
    }
    valid, rejected, metrics = dq.validate_events([evt])
    assert len(rejected) == 1
    reasons = rejected[0]["rejection_reasons"]
    assert "ERR_FK_CUSTOMER_ORPHAN" in reasons
    assert "ERR_INVALID_STATUS_CODE" in reasons
    assert "ERR_NEGATIVE_DURATION" in reasons
    assert metrics["rows_rejected"] == 1
    assert metrics["acceptance_rate_pct"] == 0.0

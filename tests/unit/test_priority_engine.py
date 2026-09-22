"""
Comprehensive Unit Tests for Priority Scoring Engine:
Multi-factor weights, normalization curves, band thresholds (P1-P4), and driver strings.
"""
import pytest
from app.rules.priority_engine import ExplainablePriorityEngine
from app.models.schemas import PriorityBand, SLAStatus

engine = ExplainablePriorityEngine()
@pytest.mark.parametrize("sla_st,ratio,rem_min,cust_tier,fin_usd,age_hrs,sev,expected_band", [
    (SLAStatus.BREACHED, 1.5, -30, "Enterprise", 200000, 10, "Critical", PriorityBand.P1),
    (SLAStatus.AT_RISK, 0.95, 5, "Enterprise", 150000, 6, "Critical", PriorityBand.P1),
    (SLAStatus.AT_RISK, 0.88, 12, "Enterprise", 80000, 4, "High", PriorityBand.P2),
    (SLAStatus.BREACHED, 1.1, -10, "Commercial", 50000, 8, "High", PriorityBand.P2),
    (SLAStatus.AT_RISK, 0.82, 18, "Commercial", 40000, 3, "High", PriorityBand.P2),
    (SLAStatus.ON_TRACK, 0.70, 30, "Enterprise", 60000, 2, "High", PriorityBand.P2),
    (SLAStatus.BREACHED, 1.05, -5, "Retail", 15000, 5, "Critical", PriorityBand.P2),
    (SLAStatus.AT_RISK, 0.85, 15, "Commercial", 20000, 2, "Medium", PriorityBand.P3),
    (SLAStatus.ON_TRACK, 0.60, 40, "Commercial", 25000, 2, "Medium", PriorityBand.P3),
    (SLAStatus.ON_TRACK, 0.40, 60, "Enterprise", 10000, 1, "Medium", PriorityBand.P3),
    (SLAStatus.ON_TRACK, 0.50, 50, "Retail", 5000, 3, "High", PriorityBand.P4),
    (SLAStatus.AT_RISK, 0.80, 20, "Retail", 1000, 1, "Low", PriorityBand.P3),
    (SLAStatus.ON_TRACK, 0.30, 70, "Commercial", 3000, 1, "Low", PriorityBand.P4),
    (SLAStatus.ON_TRACK, 0.20, 80, "Retail", 500, 0.5, "Low", PriorityBand.P4),
    (SLAStatus.ON_TRACK, 0.10, 90, "Retail", 100, 0.2, "Low", PriorityBand.P4),
    (SLAStatus.ON_TRACK, 0.05, 95, "Retail", 50, 0.1, "Low", PriorityBand.P4),
    (SLAStatus.ON_TRACK, 0.0, 100, "Retail", 10, 0.0, "Low", PriorityBand.P4),
    (SLAStatus.ON_TRACK, 0.15, 85, "Commercial", 100, 0.2, "Low", PriorityBand.P4),
    (SLAStatus.ON_TRACK, 0.25, 75, "Retail", 200, 0.5, "Low", PriorityBand.P4),
    (SLAStatus.BREACHED, 1.02, -2, "Retail", 50, 0.1, "Low", PriorityBand.P3),
])
def test_priority_band_classifications(sla_st, ratio, rem_min, cust_tier, fin_usd, age_hrs, sev, expected_band):
    score, band, drivers = engine.calculate_priority(
        sla_status=sla_st,
        sla_consumption_ratio=ratio,
        remaining_minutes=rem_min,
        customer_tier=cust_tier,
        financial_exposure_usd=fin_usd,
        unassigned_hours=age_hrs,
        severity=sev
    )
    assert band == expected_band
    assert 0.0 <= score <= 100.0


# 2. Driver Text Generation Tests (10 tests)
def test_driver_sla_breached():
    _, _, drivers = engine.calculate_priority(SLAStatus.BREACHED, 1.2, -15.5, "Retail", 100, 0, "Low")
    assert any("SLA breached (overdue by 15.5 min)" in d for d in drivers)


def test_driver_sla_imminent():
    _, _, drivers = engine.calculate_priority(SLAStatus.AT_RISK, 0.85, 12.4, "Retail", 100, 0, "Low")
    assert any("SLA breach imminent in 12.4 minutes" in d for d in drivers)


def test_driver_enterprise_customer():
    _, _, drivers = engine.calculate_priority(SLAStatus.ON_TRACK, 0.1, 100, "Enterprise", 100, 0, "Low")
    assert any("Tier 1 Enterprise customer account" in d for d in drivers)


def test_driver_high_financial_exposure():
    _, _, drivers = engine.calculate_priority(SLAStatus.ON_TRACK, 0.1, 100, "Retail", 75000, 0, "Low")
    assert any("High financial exposure ($75,000.00)" in d for d in drivers)


def test_driver_case_aging():
    _, _, drivers = engine.calculate_priority(SLAStatus.ON_TRACK, 0.1, 100, "Retail", 100, 8.5, "Low")
    assert any("Unassigned waiting time (8.5 hrs)" in d for d in drivers)


def test_driver_mission_critical_service():
    _, _, drivers = engine.calculate_priority(SLAStatus.ON_TRACK, 0.1, 100, "Retail", 100, 0, "Critical")
    assert any("Mission-critical service failure" in d for d in drivers)


def test_driver_default_fallback():
    _, _, drivers = engine.calculate_priority(SLAStatus.ON_TRACK, 0.1, 100, "Retail", 100, 0, "Low")
    assert drivers == ["Standard operational queue ranking"]


# 3. Weight Validation & Clamping Edge Cases (5 tests)
def test_invalid_weight_sum_raises_error():
    with pytest.raises(ValueError):
        ExplainablePriorityEngine(weight_sla=0.5, weight_customer=0.5, weight_financial=0.5, weight_age=0.1, weight_criticality=0.1)


def test_score_clamping_upper_bound():
    score, band, _ = engine.calculate_priority(SLAStatus.BREACHED, 5.0, -1000, "Enterprise", 10000000, 100, "Critical")
    assert score == 100.0
    assert band == PriorityBand.P1


def test_score_clamping_lower_bound():
    score, band, _ = engine.calculate_priority(SLAStatus.ON_TRACK, 0.0, 100, "Retail", 0.0, 0.0, "Low")
    assert score >= 0.0
    assert band == PriorityBand.P4

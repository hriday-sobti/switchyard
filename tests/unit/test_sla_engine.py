"""
Unit tests for SLA calculations, boundary ratios, and customer tier matrices.
"""
from datetime import datetime, timezone, timedelta
import pytest
from app.rules.sla_engine import SLAEngine
from app.models.schemas import SLAStatus, CustomerTier, SeverityLevel

engine = SLAEngine(warning_threshold_ratio=0.80, breach_threshold_ratio=1.00)
base_time = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

# 1. Tier Matrix Tests (12 combinations)
@pytest.mark.parametrize("cust_tier,sev,default_sla,expected", [
    ("Enterprise", "Critical", 180, 60),
    ("Enterprise", "High", 180, 120),
    ("Enterprise", "Medium", 180, 180),
    ("Enterprise", "Low", 180, 180),
    ("Commercial", "Critical", 240, 180),
    ("Commercial", "High", 240, 240),
    ("Commercial", "Medium", 240, 240),
    ("Commercial", "Low", 240, 240),
    ("Retail", "Critical", 360, 360),
    ("Retail", "High", 360, 360),
    ("Retail", "Medium", 360, 360),
    ("Retail", "Low", 360, 360),
    ("Enterprise", "Critical", 30, 30),  # default is smaller than tier standard
    ("Enterprise", "High", 90, 90),     # default is smaller than 120
    ("Commercial", "Critical", 100, 100) # default is smaller than 180
])
def test_sla_target_matrix_combinations(cust_tier, sev, default_sla, expected):
    assert SLAEngine.calculate_target_minutes(cust_tier, sev, default_sla) == expected


# 2. Consumption Ratio & State Transitions (20 granular boundary tests)
@pytest.mark.parametrize("elapsed_min,target_min,expected_status", [
    (0, 100, SLAStatus.ON_TRACK),
    (10, 100, SLAStatus.ON_TRACK),
    (50, 100, SLAStatus.ON_TRACK),
    (75, 100, SLAStatus.ON_TRACK),
    (79.0, 100, SLAStatus.ON_TRACK),
    (79.9, 100, SLAStatus.ON_TRACK),
    (80.0, 100, SLAStatus.AT_RISK),     # Boundary exact 80%
    (80.1, 100, SLAStatus.AT_RISK),
    (85.0, 100, SLAStatus.AT_RISK),
    (90.0, 100, SLAStatus.AT_RISK),
    (95.0, 100, SLAStatus.AT_RISK),
    (99.0, 100, SLAStatus.AT_RISK),
    (99.9, 100, SLAStatus.AT_RISK),
    (100.0, 100, SLAStatus.BREACHED),   # Boundary exact 100%
    (100.1, 100, SLAStatus.BREACHED),
    (105.0, 100, SLAStatus.BREACHED),
    (150.0, 100, SLAStatus.BREACHED),
    (500.0, 100, SLAStatus.BREACHED),
    (24.0, 30, SLAStatus.AT_RISK),      # 80% of 30min = 24min
    (30.0, 30, SLAStatus.BREACHED),     # 100% of 30min = 30min
])
def test_sla_boundary_transitions(elapsed_min, target_min, expected_status):
    cur_time = base_time + timedelta(minutes=elapsed_min)
    status, elapsed, remaining, ratio = engine.evaluate_sla_state(base_time, cur_time, target_min)
    assert status == expected_status
    assert elapsed == pytest.approx(elapsed_min, rel=1e-2)
    assert remaining == pytest.approx(target_min - elapsed_min, rel=1e-2)


# 3. Robustness against Clock Skew and Zero Target (5 tests)
def test_sla_clock_skew_future_start():
    # start time is in the future compared to current time
    future_start = base_time + timedelta(minutes=10)
    status, elapsed, remaining, ratio = engine.evaluate_sla_state(future_start, base_time, 60)
    assert status == SLAStatus.ON_TRACK
    assert elapsed == 0.0
    assert remaining == 60.0
    assert ratio == 0.0


def test_sla_naive_timestamps():
    # Naive timestamps without tzinfo should be safely handled
    t_start = datetime(2026, 1, 15, 10, 0, 0)
    t_now = datetime(2026, 1, 15, 11, 0, 0)
    status, elapsed, remaining, ratio = engine.evaluate_sla_state(t_start, t_now, 60)
    assert status == SLAStatus.BREACHED
    assert elapsed == 60.0
    assert remaining == 0.0


def test_sla_fractional_minutes():
    cur = base_time + timedelta(seconds=90)
    status, elapsed, remaining, ratio = engine.evaluate_sla_state(base_time, cur, 10)
    assert elapsed == 1.5
    assert remaining == 8.5
    assert ratio == 0.15


def test_sla_custom_thresholds():
    custom_engine = SLAEngine(warning_threshold_ratio=0.70, breach_threshold_ratio=0.90)
    cur = base_time + timedelta(minutes=72)
    status, elapsed, remaining, ratio = custom_engine.evaluate_sla_state(base_time, cur, 100)
    assert status == SLAStatus.AT_RISK


def test_sla_extreme_elapsed():
    cur = base_time + timedelta(days=30)
    status, elapsed, remaining, ratio = engine.evaluate_sla_state(base_time, cur, 60)
    assert status == SLAStatus.BREACHED
    assert elapsed == 43200.0
    assert remaining < 0

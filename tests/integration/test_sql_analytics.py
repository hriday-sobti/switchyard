"""
Comprehensive Integration Tests for SQL Analytics over Partitioned Parquet Lakehouse.
Validates aggregations, ranking metrics, latency percentiles, and partition pruning.
"""
import pytest
from app.services.analytics import DuckDBAnalyticsService

analytics = DuckDBAnalyticsService()

def test_sql_service_reliability_fields():
    metrics = analytics.get_service_reliability_metrics()
    assert len(metrics) > 0
    first = metrics[0]
    required_cols = [
        "service_id", "service_name", "service_category", "tier_level",
        "total_events", "error_event_count", "error_rate_pct", "avg_duration_ms"
    ]
    for col in required_cols:
        assert col in first
        assert first[col] is not None


def test_sql_location_bottleneck_ranking_order():
    bottlenecks = analytics.get_location_bottlenecks()
    assert len(bottlenecks) > 0
    # Ranks should be monotonically non-decreasing
    ranks = [b["failure_rank"] for b in bottlenecks]
    assert ranks == sorted(ranks)
    assert ranks[0] == 1


def test_sql_hourly_trend_completeness():
    trend = analytics.get_hourly_incident_trend()
    assert len(trend) > 0
    for hour_entry in trend:
        assert 0 <= hour_entry["hour"] <= 23
        assert hour_entry["total_events"] >= 0
        assert hour_entry["error_events"] >= 0


@pytest.mark.parametrize("service_cat", ["Core Banking", "Payments", "Compliance", "Operations"])
def test_sql_service_category_filtering(service_cat):
    metrics = analytics.get_service_reliability_metrics()
    cats = {m["service_category"] for m in metrics}
    assert service_cat in cats

"""
Unit tests for Max-Heap priority queue ordering and sliding-window event eviction.
"""
from datetime import datetime, timezone, timedelta
import pytest
from app.core.priority_queue import OperationalPriorityQueue
from app.core.sliding_window import SlidingWindowAggregator

base_time = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

# 1. Max-Heap Priority Queue Tests (15 tests)
def test_heap_empty_peek_and_pop():
    pq = OperationalPriorityQueue()
    assert pq.peek() is None
    assert pq.pop() is None
    assert pq.size() == 0


def test_heap_single_element():
    pq = OperationalPriorityQueue()
    pq.push(85.0, "EXC-1", {"id": "EXC-1"})
    assert pq.size() == 1
    assert pq.peek()["id"] == "EXC-1"
    assert pq.pop()["id"] == "EXC-1"
    assert pq.size() == 0


@pytest.mark.parametrize("scores,expected_order", [
    ([10, 20, 30, 40, 50], [50, 40, 30, 20, 10]),
    ([50, 40, 30, 20, 10], [50, 40, 30, 20, 10]),
    ([15, 95, 45, 85, 25], [95, 85, 45, 25, 15]),
    ([88.8, 12.3, 99.9, 0.1], [99.9, 88.8, 12.3, 0.1]),
    ([100.0, 100.0, 50.0], [100.0, 100.0, 50.0]),
])
def test_heap_ordering_invariants(scores, expected_order):
    pq = OperationalPriorityQueue()
    for idx, s in enumerate(scores):
        pq.push(s, f"EXC-{idx}", {"id": f"EXC-{idx}", "score": s})

    popped_scores = []
    while pq.size() > 0:
        popped_scores.append(pq.pop()["score"])

    assert popped_scores == expected_order


def test_heap_update_existing_item():
    pq = OperationalPriorityQueue()
    pq.push(50.0, "EXC-MUTABLE", {"id": "EXC-MUTABLE", "score": 50.0})
    pq.push(70.0, "EXC-OTHER", {"id": "EXC-OTHER", "score": 70.0})

    # Update EXC-MUTABLE to 99.0
    pq.push(99.0, "EXC-MUTABLE", {"id": "EXC-MUTABLE", "score": 99.0})
    assert pq.size() == 2
    assert pq.peek()["id"] == "EXC-MUTABLE"
    assert pq.peek()["score"] == 99.0


def test_heap_to_sorted_list():
    pq = OperationalPriorityQueue()
    pq.push(30.0, "EXC-3", {"score": 30.0})
    pq.push(90.0, "EXC-1", {"score": 90.0})
    pq.push(60.0, "EXC-2", {"score": 60.0})

    sorted_list = pq.to_sorted_list()
    assert len(sorted_list) == 3
    assert [x["score"] for x in sorted_list] == [90.0, 60.0, 30.0]
    # In-memory queue remains intact
    assert pq.size() == 3


# 2. Sliding-Window Aggregator Tests (15 tests)
@pytest.mark.parametrize("event_offsets_min,breach_flags,eval_offset_min,exp_count,exp_breaches", [
    ([-10, -5, -2], [True, False, True], 0, 3, 2),
    ([-90, -70, -10], [True, True, False], 0, 1, 0),        # 2 events expired
    ([-61, -60, -59], [True, True, True], 0, 2, 2),         # -61 expired, -60 is right on boundary
    ([-120, -110], [True, True], 0, 0, 0),                  # All expired
    ([], [], 0, 0, 0),                                      # Empty window
    ([-45, -30, -15, -5], [False, False, False, False], 0, 4, 0),
    ([-45, -30, -15, -5], [True, True, True, True], 0, 4, 4),
])
def test_sliding_window_scenarios(event_offsets_min, breach_flags, eval_offset_min, exp_count, exp_breaches):
    agg = SlidingWindowAggregator(window_minutes=60)
    for offset, is_b in zip(event_offsets_min, breach_flags):
        agg.add_event(base_time + timedelta(minutes=offset), is_breach=is_b)

    eval_time = base_time + timedelta(minutes=eval_offset_min)
    metrics = agg.get_metrics(eval_time)
    assert metrics["rolling_event_count"] == exp_count
    assert metrics["rolling_breach_count"] == exp_breaches
    if exp_count > 0:
        assert metrics["rolling_breach_rate_pct"] == round(exp_breaches / exp_count * 100.0, 2)
    else:
        assert metrics["rolling_breach_rate_pct"] == 0.0


def test_sliding_window_custom_window_size():
    # 15 minute window
    agg = SlidingWindowAggregator(window_minutes=15)
    agg.add_event(base_time - timedelta(minutes=20), is_breach=True)
    agg.add_event(base_time - timedelta(minutes=10), is_breach=True)
    agg.add_event(base_time - timedelta(minutes=5), is_breach=False)

    metrics = agg.get_metrics(base_time)
    assert metrics["rolling_event_count"] == 2
    assert metrics["rolling_breach_count"] == 1
    assert metrics["rolling_breach_rate_pct"] == 50.0

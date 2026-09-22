"""
Sliding-Window operational metrics aggregator for SWITCHYARD.
Maintains a monotonic time-ordered deque to compute rolling metrics
(e.g., incidents in the last 60 minutes, breach rate) in amortized O(1) time.
"""
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional


class SlidingWindowAggregator:
    def __init__(self, window_minutes: int = 60):
        self.window_seconds = window_minutes * 60
        self._window: deque = deque()  # stores tuples of (timestamp_utc, is_breach, payload)

    def _evict_expired(self, current_time: datetime):
        cutoff = current_time - timedelta(seconds=self.window_seconds)
        while self._window and self._window[0][0] < cutoff:
            self._window.popleft()

    def add_event(self, timestamp: datetime, is_breach: bool = False, payload: Optional[Dict[str, Any]] = None):
        """Add event to sliding window and evict expired entries."""
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        self._evict_expired(timestamp)
        self._window.append((timestamp, is_breach, payload or {}))

    def get_metrics(self, current_time: datetime = None) -> Dict[str, Any]:
        """Compute rolling statistics over the configured window."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        elif current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        self._evict_expired(current_time)

        total_count = len(self._window)
        breach_count = sum(1 for _, is_breach, _ in self._window if is_breach)
        breach_rate = round((breach_count / total_count * 100.0), 2) if total_count > 0 else 0.0

        return {
            "window_duration_minutes": self.window_seconds // 60,
            "rolling_event_count": total_count,
            "rolling_breach_count": breach_count,
            "rolling_breach_rate_pct": breach_rate,
        }

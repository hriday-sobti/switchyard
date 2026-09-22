"""
Algorithmic Max-Heap Priority Queue for operational exception triage.
Maintains high-priority exceptions ordered by priority score descending.
Offers O(log n) insertion and O(1) top-risk inspection.
"""
import heapq
from typing import Optional, List, Dict, Any


class PriorityQueueItem:
    def __init__(self, priority_score: float, exception_id: str, payload: Dict[str, Any]):
        self.priority_score = priority_score
        self.exception_id = exception_id
        self.payload = payload

    def __lt__(self, other: "PriorityQueueItem") -> bool:
        # Inverted for max-heap behavior in Python's min-heap implementation
        if self.priority_score != other.priority_score:
            return self.priority_score > other.priority_score
        # Tie-breaker: older/canonical string ID
        return self.exception_id < other.exception_id


class OperationalPriorityQueue:
    def __init__(self):
        self._heap: List[PriorityQueueItem] = []
        self._entry_map: Dict[str, PriorityQueueItem] = {}

    def push(self, priority_score: float, exception_id: str, payload: Dict[str, Any]):
        """Insert or update an exception in the priority queue."""
        item = PriorityQueueItem(priority_score, exception_id, payload)
        self._entry_map[exception_id] = item
        heapq.heappush(self._heap, item)

    def peek(self) -> Optional[Dict[str, Any]]:
        """Return the highest-priority exception without removing it in O(1) time."""
        if not self._heap:
            return None
        return self._heap[0].payload

    def pop(self) -> Optional[Dict[str, Any]]:
        """Remove and return the highest-priority exception in O(log n) time."""
        while self._heap:
            item = heapq.heappop(self._heap)
            if item.exception_id in self._entry_map:
                del self._entry_map[item.exception_id]
                return item.payload
        return None

    def size(self) -> int:
        return len(self._entry_map)

    def to_sorted_list(self) -> List[Dict[str, Any]]:
        """Return all active queue items sorted by priority descending."""
        sorted_items = sorted(self._entry_map.values())
        return [item.payload for item in sorted_items]

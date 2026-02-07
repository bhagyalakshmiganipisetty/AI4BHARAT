from collections import Counter
from threading import Lock


class MetricsStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._total_requests = 0
        self._total_errors = 0
        self._by_status: Counter[str] = Counter()

    def record(self, status_code: int) -> None:
        with self._lock:
            self._total_requests += 1
            self._by_status[str(status_code)] += 1
            if status_code >= 500:
                self._total_errors += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "total_requests": self._total_requests,
                "total_errors": self._total_errors,
                "by_status": dict(self._by_status),
            }


metrics = MetricsStore()

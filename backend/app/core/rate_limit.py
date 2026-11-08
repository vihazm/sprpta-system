"""In-memory limiter for failed logins per client IP.

The system has no Redis or background worker, so this lives in the process.
It resets on restart and is per worker, which is acceptable for one server.
"""

import threading
import time
from collections import defaultdict, deque

from app.core.config import settings


class FailureLimiter:
    def __init__(self) -> None:
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        window = settings.ip_failure_window_minutes * 60
        q = self._failures[key]
        while q and now - q[0] > window:
            q.popleft()
        if not q:
            self._failures.pop(key, None)
            return deque()
        return q

    def retry_after(self, key: str) -> int:
        """Seconds the caller must wait, or 0 when allowed."""
        now = time.monotonic()
        with self._lock:
            q = self._prune(key, now)
            if len(q) < settings.ip_failure_limit:
                return 0
            window = settings.ip_failure_window_minutes * 60
            return max(1, int(window - (now - q[0])) + 1)

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            self._failures[key].append(now)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


login_failures = FailureLimiter()

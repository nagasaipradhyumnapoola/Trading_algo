"""Fixed-window rate limiter (in-process).

Deterministic and testable via an injected clock. A real deployment uses Redis for
a shared window across workers; the interface stays the same.
"""

from __future__ import annotations

import time


class RateLimiter:
    def __init__(self, limit: int, window_s: float = 1.0) -> None:
        self.limit = limit
        self.window_s = window_s
        self._windows: dict[str, tuple[float, int]] = {}   # key -> (window_start, count)

    def allow(self, key: str, *, now: float | None = None) -> bool:
        t = time.monotonic() if now is None else now
        start, count = self._windows.get(key, (t, 0))
        if t - start >= self.window_s:
            start, count = t, 0                            # new window
        if count >= self.limit:
            self._windows[key] = (start, count)
            return False
        self._windows[key] = (start, count + 1)
        return True

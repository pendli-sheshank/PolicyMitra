"""Per-IP sliding-window rate limiting for /api/v1/* (health exempt).

Pure-ASGI middleware — no external dependency, no Redis: an in-memory deque
of request timestamps per client IP, swept lazily. Suits a single-process
dev/demo deployment (state is per-process by design; a multi-worker
production deployment would move this to a shared store).

The client key trusts the first X-Forwarded-For entry when present (GitHub
Codespaces / any reverse proxy); a direct client can spoof that header, which
is an accepted trade-off for a service with no other network infrastructure.

Configure with RATE_LIMIT_PER_MINUTE (default 30; 0 disables — api/main.py
skips adding the middleware entirely).
"""

from __future__ import annotations

import json
import math
import threading
import time
from collections import defaultdict, deque

RATE_LIMITED_PATH_PREFIX = "/api/v1"
EXEMPT_PATHS = frozenset({"/api/v1/healthz"})


class RateLimitMiddleware:
    def __init__(self, app, limit: int = 30, window_seconds: float = 60.0) -> None:
        self._app = app
        self._limit = limit
        self._window = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._checks_since_purge = 0

    def _client_key(self, scope) -> str:
        for name, value in scope.get("headers", []):
            if name == b"x-forwarded-for":
                return value.decode("latin-1").split(",")[0].strip()
        client = scope.get("client")
        return client[0] if client else "unknown"

    def _check(self, key: str) -> float | None:
        """Returns None if allowed (and records the request), else the
        Retry-After delay in seconds."""
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] <= now - self._window:
                bucket.popleft()
            if len(bucket) >= self._limit:
                return bucket[0] + self._window - now
            bucket.append(now)

            # Bound memory: periodically drop buckets whose window has fully
            # elapsed (clients that went quiet).
            self._checks_since_purge += 1
            if self._checks_since_purge >= 1024:
                self._checks_since_purge = 0
                cutoff = now - self._window
                stale = [k for k, dq in self._buckets.items() if not dq or dq[-1] <= cutoff]
                for k in stale:
                    del self._buckets[k]
            return None

    async def __call__(self, scope, receive, send) -> None:
        path = scope.get("path", "")
        if scope["type"] != "http" or not path.startswith(RATE_LIMITED_PATH_PREFIX) or path in EXEMPT_PATHS:
            await self._app(scope, receive, send)
            return

        retry_after = self._check(self._client_key(scope))
        if retry_after is None:
            await self._app(scope, receive, send)
            return

        body = json.dumps(
            {"error": "rate_limited", "detail": f"Rate limit exceeded ({self._limit} requests/minute). Try again shortly."}
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"retry-after", str(max(1, math.ceil(retry_after))).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})

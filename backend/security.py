"""Per-process capability and bounded request controls for the local API."""
from __future__ import annotations

import math
import secrets
import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException, Request

CAPABILITY_TOKEN = secrets.token_urlsafe(32)
INSTANCE_ID = secrets.token_hex(16)
API_VERSION = 2
SCHEMA_VERSION = 1


def require_capability(request: Request) -> None:
    value = request.headers.get("authorization", "")
    scheme, _, token = value.partition(" ")
    if (len(request.headers.getlist("authorization")) != 1
            or len(request.headers.getlist("x-allie-instance")) != 1
            or scheme.lower() != "bearer" or not token.isascii()
            or len(token) != len(CAPABILITY_TOKEN)
            or not secrets.compare_digest(token, CAPABILITY_TOKEN)):
        raise HTTPException(status_code=401, detail="Capability-Token erforderlich")
    if request.headers.get('x-allie-instance') != INSTANCE_ID:
        raise HTTPException(status_code=401, detail='Lokale Serverinstanz unbekannt')


class RequestRateLimiter:
    """Bounded sliding windows; each policy retains its own expiry.

    When all slots are live, a new key is denied instead of evicting an
    exhausted budget. Expired windows make room on the next request. The
    limit and duration are part of the identity, allowing several independent
    policies for one client without corrupting their accounting.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic, max_keys: int = 256):
        if isinstance(max_keys, bool) or not isinstance(max_keys, int) or max_keys < 1:
            raise ValueError("max_keys must be a positive integer")
        self._clock = clock
        self.max_keys = max_keys
        self._lock = threading.Lock()
        self._events: dict[tuple[str, int, float], deque[float]] = {}

    @property
    def key_count(self) -> int:
        with self._lock:
            return len(self._events)

    def allow(self, key: str, limit: int, window_seconds: float) -> bool:
        if (not isinstance(key, str) or not key
                or isinstance(limit, bool) or not isinstance(limit, int) or limit < 1
                or not math.isfinite(window_seconds) or window_seconds <= 0):
            raise ValueError("rate-limit key, limit and window must be valid and positive")
        policy = (key, limit, float(window_seconds))
        now = self._clock()
        with self._lock:
            for old_policy, events in list(self._events.items()):
                cutoff = now - old_policy[2]
                while events and events[0] <= cutoff:
                    events.popleft()
                if not events:
                    del self._events[old_policy]
            events = self._events.get(policy)
            if events is None:
                if len(self._events) >= self.max_keys:
                    return False
                events = deque()
                self._events[policy] = events
            if len(events) >= limit:
                return False
            events.append(now)
            return True


def capability_payload() -> dict[str, object]:
    return {
        "token": CAPABILITY_TOKEN,
        "instance_id": INSTANCE_ID,
        "api_version": API_VERSION,
        "schema_version": SCHEMA_VERSION,
    }

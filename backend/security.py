"""Per-process capability and bounded request controls for the local API."""
from __future__ import annotations

import secrets
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request

CAPABILITY_TOKEN = secrets.token_urlsafe(32)
INSTANCE_ID = secrets.token_hex(16)
API_VERSION = 2
SCHEMA_VERSION = 1


def require_capability(request: Request) -> None:
    value = request.headers.get("authorization", "")
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token or not secrets.compare_digest(token, CAPABILITY_TOKEN):
        raise HTTPException(status_code=401, detail="Capability-Token erforderlich")
    if request.headers.get('x-allie-instance') != INSTANCE_ID:
        raise HTTPException(status_code=401, detail='Lokale Serverinstanz unbekannt')


class RequestRateLimiter:
    """Small in-memory fixed-window limiter; bounded to one deque per key."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: float) -> bool:
        now = self._clock()
        cutoff = now - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            if len(self._events) > 256:
                for old_key in list(self._events)[:64]:
                    if not self._events[old_key]:
                        self._events.pop(old_key, None)
            return True


def capability_payload() -> dict[str, object]:
    return {
        "token": CAPABILITY_TOKEN,
        "instance_id": INSTANCE_ID,
        "api_version": API_VERSION,
        "schema_version": SCHEMA_VERSION,
    }

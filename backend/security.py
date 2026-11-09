"""Per-process capability and bounded request controls for the local API."""
from __future__ import annotations

import secrets
import threading
import time
from collections import OrderedDict, deque
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
    """Small in-memory fixed-window limiter with a hard key bound.

    Keys are supplied by browser clients, so a caller must not be able to grow
    this map without limit by sending a fresh session id on every request.
    Expired buckets are purged on every call and the oldest live bucket is
    evicted when ``max_keys`` is reached.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic, max_keys: int = 256):
        if int(max_keys) < 1:
            raise ValueError("max_keys must be positive")
        self._clock = clock
        self.max_keys = int(max_keys)
        self._lock = threading.Lock()
        self._events: OrderedDict[str, deque[float]] = OrderedDict()

    @property
    def key_count(self) -> int:
        with self._lock:
            return len(self._events)

    def allow(self, key: str, limit: int, window_seconds: float) -> bool:
        now = self._clock()
        cutoff = now - window_seconds
        with self._lock:
            # Purge every bucket, not just the bucket being accessed.  A
            # random-key flood otherwise leaves stale deques resident forever.
            for old_key, old_events in list(self._events.items()):
                while old_events and old_events[0] <= cutoff:
                    old_events.popleft()
                if not old_events:
                    self._events.pop(old_key, None)

            events = self._events.get(key)
            if events is None:
                while len(self._events) >= self.max_keys:
                    self._events.popitem(last=False)
                events = deque()
                self._events[key] = events
            else:
                self._events.move_to_end(key)
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

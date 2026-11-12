"""Per-process capability and bounded request controls for the local API."""
from __future__ import annotations

import json
import math
import os
import secrets
import threading
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path

from fastapi import HTTPException, Request

CAPABILITY_TOKEN = secrets.token_urlsafe(32)
INSTANCE_ID = secrets.token_hex(16)
API_VERSION = 2
SCHEMA_VERSION = 1
_PAIRING_LOCK = threading.RLock()
_PAIRING_CODE: str | None = None
_PAIRING_FAILURES: dict[str, deque[float]] = {}


def pairing_store_path() -> Path:
    """Return the per-user pairing store, never a repository path."""
    local_app_data = os.environ.get('LOCALAPPDATA')
    base = Path(local_app_data) / 'Allie21' if local_app_data else Path.home() / '.allie21'
    return base / 'pairing.json'


def _write_pairing(code: str) -> None:
    path = pairing_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps({'pairing_code': code}), encoding='utf-8')
    temporary.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def get_pairing_code() -> str:
    global _PAIRING_CODE
    with _PAIRING_LOCK:
        if _PAIRING_CODE is not None:
            return _PAIRING_CODE
        path = pairing_store_path()
        try:
            raw = json.loads(path.read_text(encoding='utf-8'))
            code = str(raw.get('pairing_code', ''))
        except (OSError, ValueError, TypeError):
            code = ''
        if len(code) != 8 or not code.isdecimal():
            code = f'{secrets.randbelow(100_000_000):08d}'
            _write_pairing(code)
        _PAIRING_CODE = code
        return code


def regenerate_pairing_code() -> str:
    global _PAIRING_CODE
    with _PAIRING_LOCK:
        _PAIRING_CODE = f'{secrets.randbelow(100_000_000):08d}'
        _write_pairing(_PAIRING_CODE)
        _PAIRING_FAILURES.clear()
        return _PAIRING_CODE


def pairing_attempt_allowed(origin: str, now: float | None = None) -> bool:
    current = time.monotonic() if now is None else now
    with _PAIRING_LOCK:
        events = _PAIRING_FAILURES.setdefault(origin or 'unknown', deque())
        while events and events[0] <= current - 60:
            events.popleft()
        if len(events) >= 5:
            return False
        events.append(current)
        return True


def verify_pairing_code(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 8 or not value.isdecimal():
        return False
    return secrets.compare_digest(value, get_pairing_code())


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
            current_events = self._events.get(policy)
            if current_events is None:
                if len(self._events) >= self.max_keys:
                    return False
                current_events = deque()
                self._events[policy] = current_events
            events = current_events
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

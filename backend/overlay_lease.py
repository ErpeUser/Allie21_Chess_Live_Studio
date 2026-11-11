"""Short-lived ownership leases for the single native private overlay."""
from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from typing import Callable


LEASE_SECONDS = 30.0


@dataclass(frozen=True)
class OverlayLease:
    session_id: str
    owner_token: str
    expires_at: float


class OverlayLeaseConflict(RuntimeError):
    """Raised when another live session owns the private overlay."""


class OverlayLeaseManager:
    def __init__(self, clock: Callable[[], float] = time.monotonic,
                 lease_seconds: float = LEASE_SECONDS,
                 on_expire: Callable[[OverlayLease], None] | None = None) -> None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        self._clock = clock
        self._lease_seconds = float(lease_seconds)
        self._on_expire = on_expire
        self._lock = threading.RLock()
        self._lease: OverlayLease | None = None

    def _live_locked(self, now: float) -> OverlayLease | None:
        lease = self._lease
        if lease is not None and lease.expires_at <= now:
            self._lease = None
            callback = self._on_expire
            if callback is not None:
                try:
                    callback(lease)
                except Exception:  # noqa: BLE001 - cleanup must not break auth
                    pass
            lease = None
        return lease

    def claim(self, session_id: str) -> OverlayLease:
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("session_id must be non-empty")
        with self._lock:
            now = self._clock()
            lease = self._live_locked(now)
            if lease is not None:
                if lease.session_id != session_id:
                    raise OverlayLeaseConflict
                renewed = OverlayLease(session_id, lease.owner_token, now + self._lease_seconds)
                self._lease = renewed
                return renewed
            lease = OverlayLease(session_id, secrets.token_urlsafe(32), now + self._lease_seconds)
            self._lease = lease
            return lease

    def authorize(self, session_id: str, owner_token: str) -> bool:
        with self._lock:
            lease = self._live_locked(self._clock())
            return bool(lease and lease.session_id == session_id and
                        secrets.compare_digest(lease.owner_token, owner_token))

    def touch(self, session_id: str, owner_token: str) -> OverlayLease:
        with self._lock:
            if not self.authorize(session_id, owner_token):
                raise OverlayLeaseConflict
            lease = OverlayLease(session_id, owner_token, self._clock() + self._lease_seconds)
            self._lease = lease
            return lease

    def release(self, session_id: str, owner_token: str) -> bool:
        with self._lock:
            if not self.authorize(session_id, owner_token):
                return False
            self._lease = None
            return True

    def force_release(self) -> None:
        with self._lock:
            self._lease = None


__all__ = ["LEASE_SECONDS", "OverlayLease", "OverlayLeaseConflict", "OverlayLeaseManager"]

"""Website-independent board history tracking powered by python-chess.

The browser overlay sends only the visible piece placement.  No site move-list
fields, private APIs, game-type labels, or website-specific notation are needed.
"""
from __future__ import annotations

import re
import time
from collections import OrderedDict
from threading import RLock

import chess
from position_tracker import PositionTracker

SESSION_RE = re.compile(r"^[A-Za-z0-9._:-]{1,180}$")


class BrowserTrackerPool:
    def __init__(self, maximum: int = 16, ttl_seconds: float = 1800.0):
        self.maximum = maximum
        self.ttl_seconds = ttl_seconds
        self.lock = RLock()
        self.trackers: OrderedDict[str, PositionTracker] = OrderedDict()
        self.last_seen: dict[str, float] = {}

    def _tracker(self, session_id: str) -> PositionTracker:
        if not SESSION_RE.fullmatch(session_id):
            raise ValueError("Ungültige lokale Brett-Sitzung")
        now = time.monotonic()
        for stale in tuple(self.last_seen):
            if now - self.last_seen[stale] > self.ttl_seconds:
                self.last_seen.pop(stale, None)
                self.trackers.pop(stale, None)
        tracker = self.trackers.pop(session_id, None) or PositionTracker()
        self.trackers[session_id] = tracker
        self.last_seen[session_id] = now
        while len(self.trackers) > self.maximum:
            old, _ = self.trackers.popitem(last=False)
            self.last_seen.pop(old, None)
        return tracker

    @staticmethod
    def _visible_fen(placement: str) -> str:
        if not isinstance(placement, str) or len(placement) > 100:
            raise ValueError("Ungültige sichtbare Brettstellung")
        try:
            board = chess.Board(f"{placement.strip()} w - - 0 1")
        except ValueError as exc:
            raise ValueError("Sichtbare Brettstellung ist keine gültige FEN") from exc
        if len(board.pieces(chess.KING, chess.WHITE)) != 1 or len(board.pieces(chess.KING, chess.BLACK)) != 1:
            raise ValueError("Beide Könige müssen sichtbar sein")
        return board.fen()

    def observe(self, session_id: str, placement: str, notation: str = "",
                notations: list[str] | None = None) -> dict:
        visible_fen = self._visible_fen(placement)
        with self.lock:
            tracker = self._tracker(session_id)
            change = None
            candidates = dict.fromkeys([notation, *(notations or [])])
            for candidate in candidates:
                if not candidate or candidate == "*":
                    continue
                attempt = tracker.set_notation(candidate, visible_fen, origin="sichtbares Brett")
                change = attempt
                if attempt.changed:
                    break
            if change is None or not change.changed:
                change = tracker.observe(visible_fen)
            synced = bool(
                tracker.board
                and tracker.board.board_fen() == chess.Board(visible_fen).board_fen()
            )
            ready = bool(tracker.complete_history and tracker.turn_verified and synced)
            fallback_ready = bool(tracker.turn_verified and synced)
            message = change.message
            if tracker.complete_history and not synced:
                message = "Brettwechsel noch nicht eindeutig erkannt; Pfeile ausgeblendet."
            if not ready and message == "Position unchanged":
                message = ("Brett erkannt – nach dem nächsten eindeutigen Zug startet Stockfish; "
                           "Allie folgt mit vollständiger Historie.")
            return {
                "ready": ready,
                "fallback_ready": fallback_ready,
                "changed": bool(change.changed),
                "message": message,
                "pgn": (tracker.pgn_uci or "*") if ready else "",
                "fen": tracker.current_fen(),
                "moves_seen": len(tracker.moves),
                "history_source": tracker.history_origin,
            }

    def reset(self, session_id: str) -> None:
        with self.lock:
            self.trackers.pop(session_id, None)
            self.last_seen.pop(session_id, None)

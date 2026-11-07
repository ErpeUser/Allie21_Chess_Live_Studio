"""Website-independent board history tracking powered by python-chess.

The browser overlay sends only the visible piece placement.  No site move-list
fields, private APIs, game-type labels, or website-specific notation are needed.
"""
from __future__ import annotations

from collections import OrderedDict
from threading import RLock
import re

import chess

from position_tracker import PositionTracker


SESSION_RE = re.compile(r"^[A-Za-z0-9._:-]{1,180}$")


class BrowserTrackerPool:
    def __init__(self, maximum: int = 16):
        self.maximum = maximum
        self.lock = RLock()
        self.trackers: OrderedDict[str, PositionTracker] = OrderedDict()

    def _tracker(self, session_id: str) -> PositionTracker:
        if not SESSION_RE.fullmatch(session_id):
            raise ValueError("Ungültige lokale Brett-Sitzung")
        tracker = self.trackers.pop(session_id, None) or PositionTracker()
        self.trackers[session_id] = tracker
        while len(self.trackers) > self.maximum:
            self.trackers.popitem(last=False)
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

    def observe(self, session_id: str, placement: str, notation: str = "") -> dict:
        visible_fen = self._visible_fen(placement)
        with self.lock:
            tracker = self._tracker(session_id)
            change = None
            if notation and notation != "*":
                change = tracker.set_notation(notation, visible_fen, origin="sichtbares Brett")
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
                message = "Brett erkannt – warte auf Startstellung oder eine lesbare Zugfolge."
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

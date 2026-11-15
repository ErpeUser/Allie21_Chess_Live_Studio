"""Bounded PGN mainline replay using python-chess, without engine or model IO."""
from __future__ import annotations

import io
from typing import Any

import chess
import chess.pgn

MAX_PGN_CHARS = 40_000
# The existing analysis history contract requires len(moves) < 1014. Keep a
# replay within that same limit without importing the model analysis service.
MAX_REPLAY_PLIES = 1013


class _ReplayBuilder(chess.pgn.GameBuilder):
    """Fail closed on parser errors without logging PGNs, names, or positions."""

    def begin_game(self) -> None:
        super().begin_game()
        self.plies = 0
        self.variation_depth = 0

    def end_headers(self) -> None:
        headers = self.game.headers
        if headers.get("Variant", "Standard") not in {"Standard", "Chess", ""}:
            raise ValueError("Der Rückblick unterstützt nur Standardschach, keine Varianten.")
        if "SetUp" in headers or "FEN" in headers:
            raise ValueError("Bitte eine PGN ab der Startstellung ohne SetUp/FEN importieren.")

    def begin_variation(self) -> None:
        super().begin_variation()
        self.variation_depth += 1

    def end_variation(self) -> None:
        super().end_variation()
        self.variation_depth -= 1

    def visit_move(self, board: chess.Board, move: chess.Move) -> None:
        if not move or move not in board.legal_moves:
            raise ValueError("Die PGN enthält einen illegalen Zug oder einen Nullzug.")
        if not self.variation_depth:
            self.plies += 1
            if self.plies > MAX_REPLAY_PLIES:
                raise ValueError("Die PGN darf höchstens 1013 Halbzüge enthalten.")
        super().visit_move(board, move)

    def handle_error(self, error: Exception) -> None:
        # GameBuilder's default handler logs the exception, often including a
        # user's board. Never forward or log its original diagnostic here.
        raise ValueError("Die PGN enthält einen ungültigen oder mehrdeutigen Zug.") from None


def _position(board: chess.Board, ply: int, san: str = "", uci: str = "",
              last_move_label: str = "Startstellung") -> dict[str, Any]:
    return {
        "ply": ply,
        "fen": board.fen(),
        "san": san,
        "uci": uci,
        "last_move_label": last_move_label,
        "turn": "white" if board.turn == chess.WHITE else "black",
        "in_check": board.is_check(),
        "game_over": board.is_game_over(),
    }


def build_replay(pgn: str) -> dict[str, Any]:
    """Return one game's canonical positions; never return headers or comments.

    Input remains in memory. No capture, live session, engine, model, file, or
    network service is consulted. python-chess owns PGN/SAN parsing and legality.
    """
    if not isinstance(pgn, str):
        raise TypeError("PGN muss als Text übergeben werden.")
    if len(pgn) > MAX_PGN_CHARS:
        raise ValueError("Die PGN darf höchstens 40.000 Zeichen enthalten.")
    if not pgn.strip():
        raise ValueError("Bitte zuerst eine PGN-Partie einfügen.")
    stream = io.StringIO(pgn)
    game = chess.pgn.read_game(stream, Visitor=_ReplayBuilder)
    if game is None or not game.variations:
        raise ValueError("Keine Zugfolge gefunden. Bitte eine PGN mit mindestens einem Zug importieren.")
    if chess.pgn.read_game(stream, Visitor=_ReplayBuilder) is not None:
        raise ValueError("Bitte genau eine Partie importieren; die Datei enthält mehrere Partien.")
    board = game.board()
    positions = [_position(board, 0)]
    for ply, move in enumerate(game.mainline_moves(), 1):
        san = board.san(move)
        label = f"{board.fullmove_number}{'.' if board.turn else '...'} {san}"
        board.push(move)
        positions.append(_position(board, ply, san, move.uci(), label))
    return {"ply_count": len(positions) - 1, "positions": positions}

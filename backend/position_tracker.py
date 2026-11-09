"""Reconstruct only moves consistent with successive observed chess boards.

A visual position does not determine complete history, en passant, castling,
or side to move. Never declare a reconstructed history to be complete unless
we observed the initial position or verified a full PGN from the initial ply.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import chess
import chess.pgn


@dataclass
class Change:
    changed: bool
    message: str
    move_uci: tuple[str, ...] = ()


class PositionTracker:
    def __init__(self):
        self.board: chess.Board | None = None
        self.moves: list[str] = []
        self.complete_history = False
        self.turn_verified = False
        self.history_origin = "unknown"
        self.last_error = ""

    @property
    def pgn_uci(self) -> str:
        return " ".join(self.moves) if self.complete_history else ""

    def reset(self):
        self.board = None
        self.moves = []
        self.complete_history = False
        self.turn_verified = False
        self.history_origin = "unknown"

    def set_notation(self, pgn: str, observed_fen: str | None = None, origin="notation") -> Change:
        """Accept only complete legal PGN which agrees with observed placement."""
        try:
            game = chess.pgn.read_game(io.StringIO(pgn))
            if game is None or game.errors:
                return Change(False, "Invalid notation")
            if game.board().fen() != chess.STARTING_FEN:
                return Change(False, "Notation starts from a custom position")
            board = chess.Board()
            moves = []
            for move in game.mainline_moves():
                if move not in board.legal_moves:
                    return Change(False, "Illegal move in notation")
                board.push(move)
                moves.append(move.uci())
            if not moves:
                return Change(False, "No readable moves")
            if observed_fen and board.board_fen() != chess.Board(observed_fen).board_fen():
                return Change(False, "Notation does not match visible board")
            if (
                self.complete_history
                and self.board
                and self.board.board_fen() == board.board_fen()
                and len(moves) < len(self.moves)
            ):
                return Change(False, "Partial notation; retaining longer recorded history")
            if self.complete_history and moves == self.moves:
                return Change(False, "Notation unchanged")
            self.board = board
            self.moves = moves
            self.complete_history = True
            self.turn_verified = True
            self.history_origin = origin
            return Change(True, f"Loaded {len(moves)} halfmoves from {origin}", tuple(moves))
        except (ValueError, AssertionError, TypeError) as exc:
            return Change(False, "Notation could not be validated: " + str(exc)[:100])

    @staticmethod
    def _candidates(board: chess.Board, target_placement: str, depth: int) -> list[tuple[chess.Move, ...]]:
        found: list[tuple[chess.Move, ...]] = []
        if depth < 1:
            return found
        for move in board.legal_moves:
            board.push(move)
            if board.board_fen() == target_placement:
                found.append((move,))
            if depth >= 2 and board.board_fen() != target_placement:
                for reply in board.legal_moves:
                    board.push(reply)
                    if board.board_fen() == target_placement:
                        found.append((move, reply))
                    board.pop()
            board.pop()
        return found

    def observe(self, fen: str) -> Change:
        try:
            observed = chess.Board(fen)
        except ValueError:
            return Change(False, "Recognition returned invalid FEN")
        placement = observed.board_fen()
        # Prevent corrupted detections from creating a false history.
        if len(observed.pieces(chess.KING, True)) != 1 or len(observed.pieces(chess.KING, False)) != 1:
            return Change(False, "Could not identify both kings")
        for color in (chess.WHITE, chess.BLACK):
            if len(observed.pieces(chess.PAWN, color)) > 8 or sum(piece.color == color for piece in observed.piece_map().values()) > 16:
                return Change(False, "Unplausible piece counts; waiting for clearer video")

        # Recognize a game already one move past the start, including after a
        # server restart. A unique legal first ply is complete observed history.
        fresh = chess.Board()
        fresh_moves = self._candidates(fresh, placement, depth=1)
        fresh_uci = {sequence[0].uci() for sequence in fresh_moves}
        if len(fresh_uci) == 1 and (self.board is None or self.board.board_fen() != placement):
            move = fresh_moves[0][0]
            self.board = fresh
            self.moves = []
            self.complete_history = True
            self.turn_verified = True
            self.history_origin = "initial-position"
            self.board.push(move)
            self.moves.append(move.uci())
            return Change(True, "Neue Partie erkannt: " + move.uci(), (move.uci(),))

        if self.board is None or (
            placement == chess.STARTING_BOARD_FEN
            and self.board.board_fen() != chess.STARTING_BOARD_FEN
        ):
            self.board = chess.Board() if placement == chess.STARTING_BOARD_FEN else observed
            if placement != chess.STARTING_BOARD_FEN:
                # A screenshot cannot establish historic castling/en-passant rights;
                # using inferred rights could generate illegal Stockfish advice.
                self.board.castling_rights = 0
                self.board.ep_square = None
            self.moves = []
            self.complete_history = placement == chess.STARTING_BOARD_FEN
            self.turn_verified = self.complete_history
            self.history_origin = "initial-position" if self.complete_history else "partial-video"
            return Change(True, "Initial board acquired" if self.complete_history else "Started in midgame: unknown prior history")
        if self.board.board_fen() == placement:
            return Change(False, "Position unchanged")

        # A bot-selection preview can be replaced by a real game between two
        # samples. If the new board is uniquely one legal ply from the standard
        # start, that single move is a complete observed history, not a guess.
        # When initial side to move was inferred from video, try both sides for first transition.
        variants = [self.board.copy(stack=True)]
        if not self.complete_history and not self.moves:
            alt = self.board.copy(stack=True)
            alt.turn = not alt.turn
            variants.append(alt)

        matches = []
        for base in variants:
            try:
                for sequence in self._candidates(base, placement, depth=2):
                    matches.append((base, sequence))
            except (ValueError, AssertionError):
                pass
        # If 1-ply unique, prefer it to 2-ply, which can be ambiguous.
        min_len = min((len(seq) for _, seq in matches), default=0)
        shortest = [(base, seq) for base, seq in matches if len(seq) == min_len]
        # Symmetrical positions can have multiple equally plausible sequences; do not fabricate.
        unique = {tuple(m.uci() for m in seq) for _, seq in shortest}
        if len(unique) != 1:
            self.last_error = ("Mehrdeutiger Stellungswechsel" if matches else "Kein legaler Stellungswechsel")
            return Change(False, self.last_error + "; warte auf das nächste stabile Brettbild")
        base, seq = shortest[0]
        self.board = base.copy(stack=True)
        self.turn_verified = True
        seq_uci = tuple(move.uci() for move in seq)
        for move in seq:
            self.board.push(move)
            self.moves.append(move.uci())
        return Change(True, "Tracked: " + " ".join(seq_uci), seq_uci)

    def current_fen(self) -> str:
        return self.board.fen() if self.board else ""

"""Opening recognition keeps the complete legal position authoritative."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

import chess
from chess_extras import opening_for_position


def board_after(*moves: str) -> chess.Board:
    board = chess.Board()
    for move in moves:
        board.push_uci(move)
    return board


class OpeningLookupTests(unittest.TestCase):
    def test_fen_only_lookup_keeps_side_to_move_authoritative(self):
        board = board_after('e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1b5')
        self.assertEqual(opening_for_position(board, [])['name'], 'Ruy Lopez')
        board.turn = not board.turn
        before = board.fen()
        self.assertIsNone(opening_for_position(board, []))
        self.assertEqual(board.fen(), before)

    def test_fen_only_lookup_keeps_legal_en_passant_authoritative(self):
        board = board_after('d2d4', 'c7c5', 'd4d5', 'e7e5')
        self.assertTrue(board.has_legal_en_passant())
        self.assertEqual(opening_for_position(board, [])['name'], 'Benoni Defense: Old Benoni')
        board.ep_square = None
        before = board.fen()
        self.assertIsNone(opening_for_position(board, []))
        self.assertEqual(board.fen(), before)

    def test_clocks_do_not_change_the_named_position(self):
        board = board_after('e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1b5')
        board.halfmove_clock = 41
        board.fullmove_number = 93
        before = board.fen(), tuple(board.move_stack)
        self.assertEqual(opening_for_position(board, []), {
            'eco': 'C60', 'name': 'Ruy Lopez', 'ply': 5, 'source': 'position',
        })
        self.assertEqual((board.fen(), tuple(board.move_stack)), before)

    def test_history_retains_the_last_named_position(self):
        moves = ['e2e4', 'b8c6', 'a2a3', 'a7a5']
        board = board_after(*moves)
        before = board.fen(), tuple(board.move_stack)
        self.assertIsNone(opening_for_position(board, []))
        self.assertEqual(opening_for_position(board, moves), {
            'eco': 'B00', 'name': 'Nimzowitsch Defense', 'ply': 2, 'source': 'history',
        })
        self.assertEqual((board.fen(), tuple(board.move_stack)), before)


if __name__ == '__main__':
    unittest.main()

"""Output and work-budget regressions for the bounded tactical scan."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))

import chess
from chess_extras import tactical_hints


class TacticalPerformanceTests(unittest.TestCase):
    def test_exact_hints_for_synthetic_positions(self):
        # Expected strings were captured from the unchanged implementation.
        # Keep its existing punctuation and first-found continuation ordering.
        cases = (
            (chess.STARTING_FEN, []),
            ('r3k2r/p1ppqpb1/bn2pnp1/2P5/1p2P3/2N2N2/PPQBBPPP/R3K2R w KQkq - 0 1', []),
            ('7k/8/8/3pP3/8/8/8/K7 w - d6 0 1', []),
            ('7k/5K2/6Q1/8/8/8/8/8 b - - 0 1', []),
            ('7k/6Q1/6K1/8/8/8/8/8 b - - 0 1', []),
            ('7k/5K2/6Q1/8/8/8/8/8 w - - 0 1',
             ['Nächster Schachmatt: Qg8##']),
            ('7k/5P2/6K1/8/8/8/8/8 w - - 0 1',
             ['Nächster Schachmatt: f8=Q##']),
            ('kr6/1r1N4/2Q5/8/8/8/8/K7 w - - 0 1',
             ['Mögliche Mattfolge in 2 Zügen: Nc5 … Rh8 Qxb7##']),
        )
        for fen, expected in cases:
            with self.subTest(fen=fen):
                board = chess.Board(fen)
                self.assertTrue(board.is_valid())
                self.assertEqual(tactical_hints(board), expected)
                self.assertEqual(board.fen(en_passant='fen'), fen)

    def test_input_board_and_history_are_unchanged(self):
        for moves in (('f2f3', 'e7e5', 'g2g4'),
                      ('e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1b5')):
            with self.subTest(moves=moves):
                board = chess.Board()
                for move in moves:
                    board.push_uci(move)
                before = board.copy(stack=True)
                tactical_hints(board)
                self.assertEqual(board, before)
                self.assertEqual(board.fen(en_passant='fen'), before.fen(en_passant='fen'))
                self.assertEqual(board.move_stack, before.move_stack)
                self.assertEqual(board.root(), before.root())

    def test_san_work_is_bounded_by_returned_text(self):
        # Count expensive formatting work, avoiding a machine-dependent
        # wall-clock threshold in the ordinary regression suite.
        cases = (
            (chess.STARTING_FEN, 0),
            ('7k/5K2/6Q1/8/8/8/8/8 w - - 0 1', 1),
            ('7k/5P2/6K1/8/8/8/8/8 w - - 0 1', 1),
            ('kr6/1r1N4/2Q5/8/8/8/8/K7 w - - 0 1', 3),
        )
        for fen, maximum_calls in cases:
            with self.subTest(fen=fen):
                with patch.object(chess.Board, 'san', autospec=True,
                                  side_effect=chess.Board.san) as san:
                    tactical_hints(chess.Board(fen))
                self.assertLessEqual(san.call_count, maximum_calls)


if __name__ == '__main__':
    unittest.main()

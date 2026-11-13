import unittest

import chess
from position_tracker import PositionTracker


class PositionTrackerTurnTests(unittest.TestCase):
    def test_later_full_fen_verifies_turn_for_same_placement(self):
        board = chess.Board()
        for uci in ("e2e4", "e7e5", "g1f3"):
            board.push_uci(uci)

        tracker = PositionTracker()
        placement_only = f"{board.board_fen()} w - - 0 1"
        first = tracker.observe(placement_only, turn_known=False)
        self.assertTrue(first.changed)
        self.assertFalse(tracker.turn_verified)

        second = tracker.observe(board.fen(), turn_known=True)

        self.assertTrue(second.changed)
        self.assertTrue(tracker.turn_verified)
        self.assertEqual(tracker.board.turn, board.turn)
        self.assertEqual(tracker.board.castling_rights, board.castling_rights)
        self.assertEqual(tracker.board.ep_square, board.ep_square)


if __name__ == "__main__":
    unittest.main()

"""Regression coverage for turn verification across partial-history states."""

import sys
import unittest
from pathlib import Path

import chess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from position_tracker import PositionTracker

AFTER_NF3 = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2'
AFTER_BLACK_NC6 = 'r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3'
AFTER_OUT_OF_TURN_BB5 = 'rnbqkbnr/pppp1ppp/8/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 2 2'
PLACEMENT_ONLY = AFTER_NF3.split()[0] + ' w - - 0 1'


class PositionTrackerArchitectureTests(unittest.TestCase):
    def test_verified_partial_history_rejects_a_move_by_the_wrong_side(self):
        for turn_known in (True, False):
            with self.subTest(turn_known=turn_known):
                tracker = PositionTracker()
                tracker.observe(PLACEMENT_ONLY, turn_known=False)
                verified = tracker.observe(AFTER_NF3)
                self.assertTrue(verified.changed)
                self.assertTrue(tracker.turn_verified)
                self.assertEqual(tracker.board.turn, chess.BLACK)
                previous_fen = tracker.current_fen()

                change = tracker.observe(AFTER_OUT_OF_TURN_BB5, turn_known=turn_known)

                self.assertFalse(change.changed)
                self.assertEqual(tracker.current_fen(), previous_fen)
                self.assertEqual(tracker.moves, [])
                self.assertTrue(tracker.turn_verified)
                self.assertFalse(tracker.complete_history)

    def test_verified_partial_history_tracks_the_confirmed_side(self):
        tracker = PositionTracker()
        tracker.observe(PLACEMENT_ONLY, turn_known=False)
        tracker.observe(AFTER_NF3)

        change = tracker.observe(AFTER_BLACK_NC6)

        self.assertTrue(change.changed)
        self.assertEqual(change.move_uci, ('b8c6',))
        self.assertEqual(tracker.moves, ['b8c6'])
        self.assertEqual(tracker.board.turn, chess.WHITE)
        self.assertTrue(tracker.turn_verified)
        self.assertFalse(tracker.complete_history)

    def test_unverified_partial_history_can_infer_either_first_mover(self):
        for fen, move in ((AFTER_BLACK_NC6, 'b8c6'), (AFTER_OUT_OF_TURN_BB5, 'f1b5')):
            with self.subTest(move=move):
                tracker = PositionTracker()
                tracker.observe(PLACEMENT_ONLY, turn_known=False)
                self.assertFalse(tracker.turn_verified)

                change = tracker.observe(fen)

                self.assertTrue(change.changed)
                self.assertEqual(change.move_uci, (move,))
                self.assertEqual(tracker.moves, [move])
                self.assertTrue(tracker.turn_verified)
                self.assertFalse(tracker.complete_history)


if __name__ == '__main__':
    unittest.main()

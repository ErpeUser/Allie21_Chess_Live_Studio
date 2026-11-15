"""Drawn positions retain current-board recommendations while legal moves exist."""
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import chess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from allie_local_server import analyse_position
from live_session import LiveSession

KNIGHT_CYCLE = ('g1f3', 'g8f6', 'f3g1', 'f6g8')
REPETITION_PGN = '1. Nf3 Nf6 2. Ng1 Ng8 3. Nf3 Nf6 4. Ng1 Ng8 '
REPETITION_PGN += '5. Nf3 Nf6 6. Ng1 Ng8 7. Nf3 Nf6 8. Ng1 Ng8'
REPETITION_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 16 9'
TERMINAL_FENS = (
    '7k/6Q1/5K2/8/8/8/8/8 b - - 0 1',  # Checkmate.
    '7k/5K2/6Q1/8/8/8/8/8 b - - 0 1',  # Stalemate.
)


class KnightCycleModel:
    """Replace only model inference with a deterministic legal knight cycle."""

    def predict(self, moves, **_kwargs):
        return {KNIGHT_CYCLE[len(moves) % 4]: 1.0}

    def analyze(self, moves, **kwargs):
        return {'moves': self.predict(moves, **kwargs), 'wdl': [0.0, 1.0, 0.0],
                'think_time': 1.0}


class DrawAnalysisTests(unittest.TestCase):
    def test_fivefold_repetition_keeps_current_position_arrows(self):
        result = analyse_position({
            'pgn': REPETITION_PGN, 'analysis_source': 'allie', 'player_side': 'white',
        }, KnightCycleModel())

        self.assertEqual(result['fen'], REPETITION_FEN)
        self.assertEqual(result['move_count'], 16)
        self.assertFalse(result['reviewed_finished_game'])
        self.assertIsNone(result['final_played_move'])
        self.assertEqual(result['wdl'], [0.0, 1.0, 0.0])
        self.assertEqual(result['my_moves'][0]['uci'], 'g1f3')
        self.assertEqual(result['opponent_moves'][0]['uci'], 'g8f6')
        self.assertEqual(result['premove']['uci'], 'f3g1')

    def test_drawn_endgame_fen_keeps_zero_score_engine_arrows(self):
        for fen in (
            '7k/8/8/8/8/8/8/K7 w - - 0 1',  # Insufficient material.
            '7k/8/8/8/8/8/R7/K7 w - - 100 51',  # Claimable fifty-move draw.
            '7k/8/8/8/8/8/R7/K7 w - - 150 76',  # Automatic seventy-five-move draw.
        ):
            with self.subTest(fen=fen), patch('allie_local_server.stockfish_lines', return_value={
                'available': True, 'engine': 'Stockfish', 'scope': 'position',
                'lines': [{'uci': 'a1b1', 'san': 'Kb1', 'score': '+0.00',
                           'score_cp': 0, 'depth': 12, 'variation': 'Kb1'}],
            }):
                result = analyse_position({
                    'fen': fen, 'analysis_source': 'stockfish', 'player_side': 'white',
                }, KnightCycleModel())

                self.assertEqual(result['fen'], fen)
                self.assertEqual(result['my_moves'][0]['uci'], 'a1b1')
                self.assertEqual(result['my_moves'][0]['score_cp'], 0)
                self.assertEqual(result['my_moves'][0]['source'], 'stockfish')

    def test_reply_preview_continues_after_seventy_five_move_draw(self):
        result = analyse_position({
            'pgn': ' '.join((KNIGHT_CYCLE * 38)[:149]),
            'analysis_source': 'allie', 'player_side': 'black',
        }, KnightCycleModel())

        self.assertEqual(result['fen'].split()[-2:], ['149', '75'])
        self.assertEqual(result['my_moves'][0]['uci'], 'g8f6')
        self.assertEqual(result['opponent_moves'][0]['uci'], 'f3g1')
        self.assertEqual(result['premove']['uci'], 'f6g8')

    def test_premove_preview_continues_after_seventy_five_move_draw(self):
        result = analyse_position({
            'pgn': ' '.join(KNIGHT_CYCLE * 37),
            'analysis_source': 'allie', 'player_side': 'white',
        }, KnightCycleModel())

        self.assertEqual(result['fen'].split()[-2:], ['148', '75'])
        self.assertEqual(result['my_moves'][0]['uci'], 'g1f3')
        self.assertEqual(result['opponent_moves'][0]['uci'], 'g8f6')
        self.assertEqual(result['premove']['uci'], 'f3g1')

    def test_explicit_finished_draw_review_still_rewinds_one_ply(self):
        result = analyse_position({
            'pgn': REPETITION_PGN, 'analysis_source': 'allie', 'review_finished': True,
        }, KnightCycleModel())

        self.assertTrue(result['reviewed_finished_game'])
        self.assertEqual(result['final_played_move'], 'f6g8')
        self.assertEqual(result['move_count'], 15)
        self.assertEqual(result['fen'],
                         'rnbqkb1r/pppppppp/5n2/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 15 8')

    def test_ragebait_keeps_current_arrows_and_drawn_preview_continuations(self):
        result = analyse_position({
            'pgn': ' '.join((KNIGHT_CYCLE * 38)[:149]),
            'analysis_source': 'allie', 'player_side': 'black',
            'play_style': 'ragebait',
        }, KnightCycleModel())

        self.assertEqual(result['fen'].split()[-2:], ['149', '75'])
        self.assertEqual(result['my_moves'][0]['uci'], 'g8f6')
        self.assertEqual(result['opponent_moves'][0]['uci'], 'f3g1')
        self.assertEqual(result['premove']['uci'], 'f6g8')

    def test_positions_without_legal_moves_still_reject_analysis(self):
        for fen in TERMINAL_FENS:
            with self.subTest(fen=fen), self.assertRaisesRegex(ValueError, 'Partie beendet'):
                analyse_position({'fen': fen, 'analysis_source': 'allie'}, KnightCycleModel())

    def test_live_worker_publishes_arrows_for_current_drawn_position(self):
        # Exercise the real tracker, queue, analysis and publication; only the
        # heavyweight model is replaced, so a dropped draw job cannot pass.
        with patch('live_session.analyse_position', side_effect=lambda payload:
                   analyse_position(payload, KnightCycleModel())):
            live = LiveSession()
            try:
                live.start({'player_side': 'white'})
                with live.lock:
                    self.assertTrue(live.tracker.set_notation(REPETITION_PGN).changed)
                    live._update_history_locked()
                    live._queue_locked()
                deadline = time.monotonic() + 3
                state = live.get_state()
                while state['analysing'] and time.monotonic() < deadline:
                    time.sleep(.01)
                    state = live.get_state()

                self.assertIsNotNone(state['result'], state['message'])
                self.assertFalse(state['analysing'])
                self.assertEqual(state['result']['fen'], REPETITION_FEN)
                self.assertTrue(state['result']['history_complete'])
                self.assertTrue(state['result']['turn_verified'])
                self.assertEqual(state['result']['my_moves'][0]['uci'], 'g1f3')
            finally:
                live.stop()

    def test_live_does_not_queue_positions_without_legal_moves(self):
        live = LiveSession()
        try:
            live.start({})
            for fen in TERMINAL_FENS:
                with self.subTest(fen=fen), live.lock:
                    live.tracker.board = chess.Board(fen)
                    live.tracker.turn_verified = True
                    live._queue_locked()
                    self.assertFalse(live.get_state()['analysing'])
                    self.assertIsNone(live.get_state()['result'])
                    self.assertIsNone(live.analysis_job)
        finally:
            live.stop()


if __name__ == '__main__':
    unittest.main()

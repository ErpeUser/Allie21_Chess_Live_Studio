"""Integration tests run automatically after START_HIER has installed python-chess."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from io import BytesIO
from threading import Event
from types import SimpleNamespace
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
try:
    import chess
    from PIL import Image
except ImportError as exc:
    raise unittest.SkipTest('Chess libraries have not been installed yet') from exc

from allie_local_server import (
    analyse_position, make_plan_messages, parse_history,
    risk_weighted_premove,
)
import allie_local_server as allie_server
from position_tracker import PositionTracker
from chess_extras import opening_for_position
from live_session import LiveSession
from browser_session import BrowserTrackerPool


class FakeAllie:
    def __init__(self): self.called = 0
    def predict(self, moves, **kwargs):
        self.called += 1
        board = chess.Board()
        for uci in moves: board.push_uci(uci)
        return {move.uci(): .6/(i+1) for i, move in enumerate(list(board.legal_moves)[:4])}

    def analyze(self, moves, **kwargs):
        return {'moves': self.predict(moves, **kwargs), 'wdl': [.4,.3,.3],
                'think_time': 2.5}


class ChessTests(unittest.TestCase):
    def test_windows_model_load_uses_supported_blitz_settings(self):
        calls = []

        class FakeAutoModel:
            @staticmethod
            def from_pretrained(*args, **kwargs):
                calls.append((args, kwargs))
                return object()

        previous = allie_server._model
        allie_server._model = None
        try:
            with patch.dict(sys.modules, {'transformers': SimpleNamespace(AutoModel=FakeAutoModel)}), \
                 patch.object(allie_server.sys, 'platform', 'win32'):
                allie_server.get_model()
        finally:
            allie_server._model = previous
        self.assertEqual(calls[0][1]['active_experts'], 8)
        self.assertEqual(calls[0][1]['backend'], 'torch')

    def test_browser_tracker_reconstructs_visible_board_transitions(self):
        pool = BrowserTrackerPool()
        board = chess.Board()
        first = pool.observe('web-test', board.board_fen())
        self.assertTrue(first['ready'])
        self.assertEqual(first['pgn'], '*')
        board.push_uci('e2e4')
        second = pool.observe('web-test', board.board_fen())
        self.assertEqual(second['pgn'], 'e2e4')
        board.push_uci('b8c6')
        third = pool.observe('web-test', board.board_fen())
        self.assertEqual(third['pgn'], 'e2e4 b8c6')
        self.assertEqual(third['moves_seen'], 2)

    def test_browser_tracker_can_bridge_two_unseen_halfmoves(self):
        pool = BrowserTrackerPool()
        board = chess.Board()
        pool.observe('web-two-ply', board.board_fen())
        board.push_uci('e2e4'); board.push_uci('b8c6')
        result = pool.observe('web-two-ply', board.board_fen())
        self.assertTrue(result['ready'])
        self.assertEqual(result['pgn'], 'e2e4 b8c6')

    def test_bot_preview_is_replaced_by_new_game_first_move(self):
        pool = BrowserTrackerPool()
        preview = chess.Board()
        for uci in ('d2d4', 'd7d5', 'c1f4'):
            preview.push_uci(uci)
        self.assertFalse(pool.observe('web-bot', preview.board_fen())['ready'])
        game = chess.Board(); game.push_uci('e2e4')
        started = pool.observe('web-bot', game.board_fen())
        self.assertTrue(started['ready'])
        self.assertEqual(started['pgn'], 'e2e4')

    def test_browser_tracker_never_returns_old_history_for_unmatched_board(self):
        pool = BrowserTrackerPool()
        board = chess.Board()
        pool.observe('web-stale', board.board_fen())
        board.push_uci('e2e4')
        current = pool.observe('web-stale', board.board_fen())
        self.assertTrue(current['ready'])
        self.assertEqual(current['pgn'], 'e2e4')

        unrelated = chess.Board()
        unrelated.push_uci('d2d4')
        unrelated.push_uci('d7d5')
        unrelated.push_uci('c1f4')
        stale = pool.observe('web-stale', unrelated.board_fen())
        self.assertFalse(stale['ready'])
        self.assertEqual(stale['pgn'], '')
        self.assertIn('Pfeile ausgeblendet', stale['message'])

    def test_browser_tracker_does_not_invent_a_late_start_history(self):
        pool = BrowserTrackerPool()
        board = chess.Board(); board.push_uci('f2f3'); board.push_uci('e7e5')
        result = pool.observe('web-late-start', board.board_fen())
        self.assertFalse(result['ready'])
        self.assertFalse(result['fallback_ready'])
        self.assertEqual(result['pgn'], '')
        self.assertFalse(result['history_source'] == 'reconstructed-opening')
        board.push_uci('e2e4')
        tracked = pool.observe('web-late-start', board.board_fen())
        self.assertFalse(tracked['ready'])
        self.assertTrue(tracked['fallback_ready'])
        self.assertEqual(chess.Board(tracked['fen']).turn, chess.BLACK)

    def test_browser_tracker_accepts_confirmed_complete_history(self):
        pool = BrowserTrackerPool()
        board = chess.Board(); board.push_uci('f2f3'); board.push_uci('e7e5')
        result = pool.observe('web-with-pgn', board.board_fen(), '1. f3 e5')
        self.assertTrue(result['ready'])
        self.assertEqual(result['pgn'], 'f2f3 e7e5')

    def test_pgn_is_legal(self):
        moves, board, clocks = parse_history('1. e4 e5 2. Nf3 Nc6')
        self.assertEqual(len(moves), 4)
        self.assertEqual(len(clocks), 4)
        self.assertEqual(board.turn, chess.WHITE)

    def test_allie_model_API_is_injected_only_in_test(self):
        model = FakeAllie()
        result = analyse_position({'pgn':'1. e4 e5 2. Nf3 Nc6', 'analysis_source':'allie'}, model)
        self.assertEqual(result['model'], 'yimingzhang/allie-2.1')
        self.assertGreaterEqual(model.called, 3)
        self.assertTrue(result['opponent_moves'])
        self.assertTrue(result['my_moves'])
        self.assertTrue(result['plan_messages'])
        self.assertTrue(result['moves'][0]['explanation'])

    def test_player_turn_preview_needs_only_three_allie_calls(self):
        model = FakeAllie()
        result = analyse_position({
            'pgn': '1. e4 e5 2. Nf3 Nc6',
            'analysis_source': 'allie',
            'preview': True,
            'player_side': 'white',
        }, model)

        self.assertEqual(model.called, 3)
        self.assertEqual(len(result['my_moves']), 2)
        self.assertEqual(len(result['opponent_moves']), 2)
        self.assertIsNotNone(result['premove'])

    def test_both_mode_scores_only_allie_candidates_without_reordering_them(self):
        captured = []

        def score_candidates(_board, _budget, root_moves=None):
            captured.append(root_moves)
            return {
                'available': True,
                'engine': 'Stockfish',
                'scope': 'allie-candidates',
                'lines': [
                    {'uci': uci, 'san': uci, 'score': f'+{index}.00',
                     'depth': 12, 'variation': uci}
                    for index, uci in enumerate(reversed(root_moves or []), 1)
                ],
            }

        with patch('allie_local_server.stockfish_lines', side_effect=score_candidates):
            result = analyse_position({
                'pgn': '1. e4 e5 2. Nf3 Nc6',
                'analysis_source': 'both',
                'preview': False,
            }, FakeAllie())

        allie_order = [move['uci'] for move in result['moves']]
        self.assertEqual(captured, [allie_order])
        self.assertEqual(result['stockfish']['scope'], 'allie-candidates')
        self.assertTrue(all('stockfish_score' in move for move in result['moves']))

    def test_allie_can_choose_from_the_normal_start_position(self):
        result = analyse_position({'pgn': '*', 'analysis_source': 'allie', 'preview': False}, FakeAllie())
        self.assertEqual(result['move_count'], 0)
        self.assertEqual(result['side_to_move'], 'white')
        self.assertTrue(result['moves'])

    def test_premove_balances_probability_and_branch_risk(self):
        common = {'uci':'g1f3', 'san':'Nf3', 'probability':.5, 'flags':[]}
        risky = {'uci':'f1b5', 'san':'Bb5', 'probability':.9, 'flags':[]}
        plan = risk_weighted_premove([
            (.7, [common, risky]),
            (.3, [{**common, 'probability':.4}]),
        ])
        self.assertEqual(plan['uci'], 'g1f3')
        self.assertEqual(plan['coverage'], 1.0)
        self.assertEqual(plan['source'], 'allie')

    def test_legal_game_populates_colored_allie_plan(self):
        """Exercise the recommendation shape on a short legal move sequence."""
        board = chess.Board()
        history = []
        centers = {chess.D4, chess.E4, chess.D5, chess.E5}
        for ply in range(12):
            legal = list(board.legal_moves)
            self.assertTrue(legal)
            # Build a deterministic legal sequence without a subprocess/download.
            move = max(legal, key=lambda candidate: (
                board.is_capture(candidate) if ply % 2 else candidate.to_square in centers,
                board.gives_check(candidate), candidate.uci(),
            ))
            history.append(move.uci())
            board.push(move)
            if board.is_game_over():
                break
        self.assertGreaterEqual(len(history), 6)
        result = analyse_position({
            'pgn': ' '.join(history), 'analysis_source': 'allie',
            'preview': True, 'time_control': '600+0',
        }, FakeAllie())
        self.assertGreaterEqual(len(result['moves']), 2)
        self.assertTrue(result['my_moves'])
        self.assertTrue(result['opponent_moves'])
        self.assertTrue(result['moves'][0]['explanation'])
        self.assertNotEqual(result['moves'][0]['uci'], result['moves'][1]['uci'])

    def test_fen_never_calls_allie(self):
        model = FakeAllie()
        result = analyse_position({'fen':chess.STARTING_FEN, 'analysis_source':'allie'}, model)
        self.assertEqual(model.called, 0)
        self.assertTrue(result['allie_skip_reason'])

    def test_fen_stockfish_fallback_populates_current_side_arrows(self):
        lines = [
            {'san': 'e4', 'uci': 'e2e4', 'score': '+0.20', 'variation': '1. e4'},
            {'san': 'd4', 'uci': 'd2d4', 'score': '+0.10', 'variation': '1. d4'},
        ]
        with patch('allie_local_server.stockfish_lines', return_value={
            'available': True, 'engine': 'Stockfish', 'scope': 'position', 'lines': lines,
        }):
            result = analyse_position({
                'fen': chess.STARTING_FEN, 'analysis_source': 'stockfish',
                'player_side': 'white',
            })
        self.assertEqual([move['uci'] for move in result['my_moves']], ['e2e4', 'd2d4'])
        self.assertFalse(result['opponent_moves'])
        self.assertTrue(result['allie_skip_reason'])

    def test_model_failure_is_visible(self):
        class Broken:
            def analyze(self, *args, **kwargs): raise RuntimeError('Unreachable')
        result = analyse_position({'pgn':'1. e4 e5', 'analysis_source':'allie'}, Broken())
        self.assertIn('Unreachable', result['allie_skip_reason'])

    def test_midgame_unknown_turn_does_not_show_engine(self):
        tracker = PositionTracker()
        b = chess.Board()
        for uci in ('e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1b5'):
            b.push_uci(uci)
        tracker.observe(b.fen())
        self.assertFalse(tracker.turn_verified)
        self.assertFalse(tracker.complete_history)
        self.assertEqual(tracker.board.castling_rights, 0)

    def test_start_to_legal_transition(self):
        tracker = PositionTracker()
        tracker.observe(chess.STARTING_FEN)
        self.assertTrue(tracker.turn_verified)
        b = chess.Board(); b.push_uci('e2e4')
        tracker.observe(b.fen())
        self.assertTrue(tracker.complete_history)
        self.assertEqual(tracker.pgn_uci, 'e2e4')

    def test_lichess_opening_fallback(self):
        board = chess.Board(); moves=[]
        for uci in ('e2e4','e7e5','g1f3','b8c6','f1b5'):
            board.push_uci(uci); moves.append(uci)
        self.assertIn('Ruy Lopez', opening_for_position(board, moves)['name'])

    def test_nimzowitsch_opening_is_named_without_download(self):
        board = chess.Board(); moves=[]
        for uci in ('e2e4', 'b8c6'):
            board.push_uci(uci); moves.append(uci)
        self.assertEqual(opening_for_position(board, moves)['name'], 'Nimzowitsch Defense')

    def test_plan_messages_add_context_instead_of_repeating_arrows(self):
        messages = make_plan_messages({
            'move_count': 2,
            'opening': {'eco': 'B00', 'name': 'Nimzowitsch Defense',
                        'idea': 'Schwarz bleibt flexibel.'},
            'position_facts': ['Materiell ausgeglichen (vereinfachte Zählung).',
                               'Entwicklung: Mehrere Leichtfiguren stehen noch auf ihren Ausgangsfeldern.'],
            'opponent_moves': [
                {'san': 'e5', 'probability': .37, 'flags': [],
                 'explanation': 'Besetzt ein zentrales Feld.'},
                {'san': 'c5', 'probability': .24, 'flags': [],
                 'explanation': 'Verändert die Bauernstruktur.'},
            ],
            'premove': {'san': 'Nf3', 'coverage': 1.0, 'risk': 0.0},
            'tactical_warnings': [],
        })
        joined = ' '.join(messages)
        self.assertIn('Nimzowitsch Defense', joined)
        self.assertIn('gegnerische Absicht', joined)
        self.assertNotIn('37 %', joined)
        self.assertNotIn('Für dich empfiehlt', joined)
        self.assertNotIn('Als Pre-Move passt', joined)

    def test_live_invalid_time_control(self):
        live=LiveSession()
        with self.assertRaises(ValueError):
            live.start({'time_control':'bad'})
        live.stop()

    def test_new_video_position_needs_stability(self):
        live=LiveSession();live.start({})
        class Detector:
            def recognize(self, _):
                return {'fen': chess.STARTING_FEN, 'box': [4,4,240,240],
                        'confidence': .99, 'orientation':'white'}
            def read_notation(self, *_): return ''
        live.vision=Detector()
        b=BytesIO();Image.new('RGB',(340,340), 'white').save(b,format='JPEG')
        with patch('live_session.analyse_position',return_value={'fen': chess.STARTING_FEN,'moves':[],'stockfish':None}):
            first=live.submit_frame(b.getvalue())
            self.assertIsNone(first['detection'])
            second=live.submit_frame(b.getvalue())
            self.assertIsNotNone(second['detection'])
            self.assertTrue(second['history_complete'])
        live.stop()

    def test_live_recommendations_can_be_disabled_and_enabled(self):
        live = LiveSession()
        try:
            state = live.start({'recommendations_enabled': False})
            self.assertFalse(state['recommendations_enabled'])
            with live.lock:
                live.tracker.observe(chess.STARTING_FEN)
                live._update_history_locked()
                live._queue_locked()
            state = live.get_state()
            self.assertFalse(state['analysing'])
            self.assertIsNone(state['result'])

            state = live.set_recommendations(True)
            self.assertTrue(state['recommendations_enabled'])
            self.assertTrue(state['analysing'])

            state = live.set_recommendations(False)
            self.assertFalse(state['recommendations_enabled'])
            self.assertFalse(state['analysing'])
            self.assertIsNone(state['result'])
        finally:
            live.stop()

    def test_complete_live_history_runs_one_combined_latest_job(self):
        live = LiveSession()
        live.start({})
        calls = []

        def fake_analysis(payload):
            calls.append(payload['analysis_source'])
            base = {'fen': chess.STARTING_FEN, 'opening': None, 'position_facts': [],
                    'tactical_warnings': [], 'allie_skip_reason': None, 'brief': [],
                    'model': 'yimingzhang/allie-2.1',
                    'stockfish': {'available': True, 'lines': []},
                    'moves': [{'san': 'e4', 'uci': 'e2e4', 'probability': .5}],
                    'wdl': None, 'expected_think_time_s': None,
                    'my_moves': [], 'opponent_moves': [], 'premove': None,
                    'plan_messages': []}
            return base

        try:
            with patch('live_session.analyse_position', side_effect=fake_analysis):
                with live.lock:
                    live.tracker.observe(chess.STARTING_FEN)
                    live._update_history_locked()
                    live._queue_locked()
                deadline = time.monotonic() + 3
                state = live.get_state()
                while state.get('analysing') and time.monotonic() < deadline:
                    time.sleep(.02)
                    state = live.get_state()
                self.assertEqual(calls, ['both'])
                self.assertEqual(state['result']['moves'][0]['uci'], 'e2e4')
                self.assertFalse(state['analysing'])
        finally:
            live.stop()

    def test_stopped_analysis_cannot_publish_and_restart_is_clean(self):
        live = LiveSession()
        release = Event()

        def delayed(payload):
            release.wait(3)
            return {'fen': chess.STARTING_FEN, 'moves': [{'uci': 'e2e4'}],
                    'stockfish': None, 'opening': None, 'position_facts': [],
                    'tactical_warnings': [], 'allie_skip_reason': None, 'brief': []}

        try:
            live.start({})
            with patch('live_session.analyse_position', side_effect=delayed):
                with live.lock:
                    live.tracker.observe(chess.STARTING_FEN)
                    live._update_history_locked()
                    live._queue_locked()
                live.stop()
                live.start({})
                release.set()
                time.sleep(.1)
                state = live.get_state()
                self.assertTrue(state['running'])
                self.assertIsNone(state['result'])
                self.assertFalse(state['analysing'])
        finally:
            release.set()
            live.stop()


if __name__ == '__main__':
    unittest.main()

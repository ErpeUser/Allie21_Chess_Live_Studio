"""Integration tests run automatically after START_HIER has installed python-chess."""
import sys
import time
import unittest
from io import BytesIO
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
try:
    import chess
    from PIL import Image
except ImportError as exc:
    raise unittest.SkipTest('Chess libraries have not been installed yet') from exc

import allie_local_server as allie_server
from allie_local_server import (
    analyse_position,
    make_plan_messages,
    parse_history,
    rank_allie_candidates,
    risk_weighted_premove,
    safe_aggressive_order,
)
from browser_session import BrowserTrackerPool
from chess_extras import opening_for_position, repertoire_move_for, standard_repertoire
from live_session import LiveSession
from position_tracker import PositionTracker


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


class BrokenAllie:
    def analyze(self, *args, **kwargs):
        raise RuntimeError('Unreachable')


class FoolMateAllie:
    def analyze(self, _moves, **_kwargs):
        return {'moves': {'a7a6': .72, 'd8h4': .08}, 'wdl': [.3, .3, .4]}

    def predict(self, _moves, **_kwargs):
        return {}


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

    def test_first_observation_after_server_restart_can_be_e4(self):
        pool = BrowserTrackerPool()
        game = chess.Board(); game.push_uci('e2e4')
        started = pool.observe('web-restart', game.board_fen())
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

    def test_browser_tracker_chooses_visible_history_that_matches_board(self):
        pool = BrowserTrackerPool()
        board = chess.Board()
        for uci in ('e2e4', 'd7d5', 'e4d5', 'g8f6', 'd2d4', 'e7e5',
                    'f2f3', 'e5e4', 'g2g3', 'b8c6'):
            board.push_uci(uci)
        result = pool.observe(
            'web-candidates', board.board_fen(), '',
            ['1. e4 e5', '1. e4 d5 2. exd5 Nf6 3. d4 e5 4. f3 e4 5. g3 Nc6'],
        )
        self.assertTrue(result['ready'])
        self.assertEqual(result['moves_seen'], 10)

    def test_new_shorter_game_replaces_previous_history_on_same_page(self):
        pool = BrowserTrackerPool()
        previous = chess.Board()
        pool.observe('web-same-page', previous.board_fen())
        for uci in ('e2e4', 'e7e5', 'g1f3'):
            previous.push_uci(uci)
            pool.observe('web-same-page', previous.board_fen())

        current = chess.Board()
        current.push_uci('f2f3'); current.push_uci('d7d5')
        result = pool.observe('web-same-page', current.board_fen(), '1. f3 d5')

        self.assertTrue(result['ready'])
        self.assertEqual(result['pgn'], 'f2f3 d7d5')

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

    def test_normal_style_preserves_allie_order(self):
        board = chess.Board()
        choices = [
            {'uci': 'e2e4', 'probability': .51, 'flags': []},
            {'uci': 'd2d4', 'probability': .29, 'flags': []},
        ]

        self.assertEqual(rank_allie_candidates(board, choices, 'normal'), choices)

    def test_standard_repertoire_has_requested_white_and_black_lines(self):
        self.assertEqual(standard_repertoire('white')['primary'], 'Grob Gambit')
        self.assertEqual(standard_repertoire('white')['alternative'], 'Wiener Gambit')
        self.assertEqual(standard_repertoire('white')['additional'], 'Dänisches Gambit')
        self.assertEqual(standard_repertoire('black')['primary'], 'Englund Gambit')
        self.assertEqual(standard_repertoire('black')['alternative'], 'Budapester Gambit')
        self.assertEqual(standard_repertoire('black')['additional'], 'Aljechin-Verteidigung')

    def test_standard_repertoire_selection_changes_primary_line(self):
        self.assertEqual(standard_repertoire('white', 'vienna')['primary'], 'Wiener Gambit')
        self.assertEqual(repertoire_move_for([], 'white', 'vienna'), 'e2e4')
        self.assertEqual(standard_repertoire('black', 'alekhine')['primary'], 'Aljechin-Verteidigung')
        self.assertEqual(repertoire_move_for(['e2e4'], 'black', 'alekhine'), 'g8f6')

    def test_troll_repertoire_uses_existing_legal_opening_lines(self):
        self.assertEqual(standard_repertoire('white', 'halloween')['primary'], 'Halloween-Gambit')
        self.assertEqual(repertoire_move_for([], 'white', 'bongcloud'), 'e2e4')
        self.assertEqual(repertoire_move_for(['e2e4', 'e7e5'], 'white', 'bongcloud'), 'e1e2')
        self.assertEqual(repertoire_move_for(['e2e4', 'e7e5', 'g1f3', 'g8f6', 'f3e5'], 'black', 'stafford'), 'b8c6')
        self.assertEqual(repertoire_move_for(['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1c4', 'g8f6', 'f3g5'], 'black', 'traxler'), 'f8c5')

    def test_repertoire_move_is_only_returned_for_matching_legal_history(self):
        self.assertEqual(repertoire_move_for([], 'white'), 'g2g4')
        self.assertIsNone(repertoire_move_for(['e2e4'], 'black'))
        self.assertEqual(repertoire_move_for(['d2d4'], 'black'), 'e7e5')
        self.assertIsNone(repertoire_move_for(['e2e4', 'e7e5', 'b1c3'], 'black'))

    def test_repertoire_does_not_switch_to_another_line_after_deviation(self):
        # The selected Vienna line diverges on 2.d4; Danish must not be used
        # as an implicit fallback just because its prefix happens to match.
        self.assertIsNone(repertoire_move_for(
            ['e2e4', 'e7e5', 'd2d4'], 'white', 'vienna'))
        # Likewise, Englund must not silently become Budapest after 1.d4 Nf6.
        self.assertIsNone(repertoire_move_for(
            ['d2d4', 'g8f6'], 'black', 'englund'))

    def test_aggressive_style_promotes_immediate_mate_for_player(self):
        result = analyse_position({
            'pgn': '1. f3 e5 2. g4',
            'analysis_source': 'allie',
            'preview': False,
            'player_side': 'black',
            'play_style': 'aggressive',
        }, FoolMateAllie())

        self.assertEqual(result['my_moves'][0]['uci'], 'd8h4')
        self.assertIn('Schachmatt', result['my_moves'][0]['flags'])
        self.assertEqual(result['play_style'], 'aggressive')

    def test_aggressive_style_does_not_reorder_opponent_prediction(self):
        result = analyse_position({
            'pgn': '1. f3 e5 2. g4',
            'analysis_source': 'allie',
            'preview': False,
            'player_side': 'white',
            'play_style': 'aggressive',
        }, FoolMateAllie())

        self.assertEqual([move['uci'] for move in result['opponent_moves']], ['a7a6', 'd8h4'])

    def test_aggressive_style_keeps_pressure_inside_engine_safety_margin(self):
        candidates = [
            {'uci': 'e2e4', 'probability': .8, 'flags': ['Schach']},
            {'uci': 'd2d4', 'probability': .2, 'flags': []},
        ]
        stockfish = {'available': True, 'lines': [
            {'uci': 'e2e4', 'score_cp': -240},
            {'uci': 'd2d4', 'score_cp': 20},
        ]}
        safe = safe_aggressive_order(candidates, stockfish)
        self.assertEqual([move['uci'] for move in safe], ['d2d4', 'e2e4'])

    def test_allie_can_choose_from_the_normal_start_position(self):
        result = analyse_position({'pgn': '*', 'analysis_source': 'allie', 'preview': False}, FakeAllie())
        self.assertEqual(result['move_count'], 0)
        self.assertEqual(result['side_to_move'], 'white')
        self.assertTrue(result['moves'])
        self.assertEqual(result['repertoire']['primary'], 'Grob Gambit')
        self.assertEqual(result['repertoire']['expected_move'], 'g2g4')
        self.assertEqual(result['repertoire']['expected_san'], 'g4')
        self.assertTrue(any('Standardrepertoire' in message for message in result['plan_messages']))

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

    def test_incomplete_history_can_analyse_but_cannot_publish_concrete_moves(self):
        with patch('allie_local_server.stockfish_lines', return_value={
            'available': True, 'engine': 'Stockfish', 'scope': 'position',
            'lines': [{'san': 'e4', 'uci': 'e2e4', 'score': '+0.20', 'variation': '1. e4'}],
        }):
            result = analyse_position({
                'fen': chess.STARTING_FEN, 'analysis_source': 'stockfish',
                'player_side': 'white', 'show_moves': False,
            })
        self.assertFalse(result['my_moves'])
        self.assertFalse(result['opponent_moves'])
        self.assertIsNone(result['premove'])
        self.assertEqual(result['uncertainty']['level'], 'warning')

    def test_model_failure_is_visible(self):
        class Broken:
            def analyze(self, *args, **kwargs): raise RuntimeError('Unreachable')
        result = analyse_position({'pgn':'1. e4 e5', 'analysis_source':'allie'}, Broken())
        self.assertIn('Fehler-ID', result['allie_skip_reason'])
        self.assertNotIn('Unreachable', result['allie_skip_reason'])

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

    def test_opening_lookup_resolves_a_real_epd_transposition(self):
        first = chess.Board()
        first_moves = ('e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1b5')
        for uci in first_moves:
            first.push_uci(uci)
        transposed = chess.Board()
        transposed_moves = ('e2e4', 'e7e5', 'f1b5', 'b8c6', 'g1f3')
        for uci in transposed_moves:
            transposed.push_uci(uci)
        self.assertEqual(first.epd(en_passant='legal'), transposed.epd(en_passant='legal'))
        self.assertEqual(opening_for_position(transposed, list(transposed_moves))['name'], 'Ruy Lopez')

    def test_opening_lookup_does_not_ignore_castling_rights_in_fen_only_mode(self):
        board = chess.Board()
        for uci in ('e2e4', 'e7e5'):
            board.push_uci(uci)
        board.castling_rights = 0
        self.assertIsNone(opening_for_position(board, []))

    def test_analysis_uses_the_selected_black_repertoire_and_keeps_allie_fallback(self):
        result = analyse_position({
            'pgn': '1. e4', 'analysis_source': 'allie',
            'player_side': 'black', 'opening_black': 'alekhine',
        }, BrokenAllie())
        self.assertEqual(result['repertoire']['selection'], 'alekhine')
        self.assertEqual(result['repertoire']['expected_move'], 'g8f6')
        self.assertIn('Fehler-ID', result['allie_skip_reason'])
        self.assertNotIn('Unreachable', result['allie_skip_reason'])

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

    def test_complete_live_history_runs_one_allie_latest_job(self):
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
                self.assertEqual(calls, ['allie'])
                self.assertEqual(state['result']['moves'][0]['uci'], 'e2e4')
                self.assertFalse(state['analysing'])
        finally:
            live.stop()

    def test_live_history_passes_selected_openings_to_allie(self):
        live = LiveSession()
        live.start({'opening_white': 'vienna', 'opening_black': 'alekhine',
                    'play_style': 'aggressive'})
        captured = []

        def fake_analysis(payload):
            captured.append(payload.copy())
            return {'fen': chess.STARTING_FEN, 'opening': None, 'position_facts': [],
                    'tactical_warnings': [], 'allie_skip_reason': None, 'brief': [],
                    'model': 'yimingzhang/allie-2.1', 'stockfish': None,
                    'moves': [{'san': 'e4', 'uci': 'e2e4', 'probability': .5}],
                    'wdl': None, 'expected_think_time_s': None,
                    'my_moves': [], 'opponent_moves': [], 'premove': None,
                    'plan_messages': []}

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
            self.assertEqual(len(captured), 1)
            self.assertEqual(captured[0]['analysis_source'], 'allie')
            self.assertEqual(captured[0]['opening_white'], 'vienna')
            self.assertEqual(captured[0]['opening_black'], 'alekhine')
            self.assertEqual(captured[0]['play_style'], 'aggressive')
        finally:
            live.stop()

    def test_live_history_falls_back_to_stockfish_when_allie_has_no_moves(self):
        live = LiveSession()
        live.start({})
        calls = []

        def fake_analysis(payload):
            calls.append(payload['analysis_source'])
            if payload['analysis_source'] == 'allie':
                return {'fen': chess.STARTING_FEN, 'moves': [],
                        'allie_skip_reason': 'Allie nicht verfügbar'}
            return {'fen': chess.STARTING_FEN, 'moves': [],
                    'allie_skip_reason': 'Allie nicht verfügbar', 'stockfish': {
                        'available': True, 'lines': []}}

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
            self.assertEqual(calls, ['allie', 'stockfish'])
            self.assertEqual(state['message'], 'Stockfish-Fallback aktiv · Allie nicht verfügbar')
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

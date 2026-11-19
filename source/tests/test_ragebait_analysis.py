"""Adaptive own-move choices retain model probabilities and matching previews."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import chess

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from allie_local_server import (
    analyse_position,
    describe_move,
    rank_allie_candidates,
    safe_aggressive_order,
)


class DistributionModel:
    """Substitute heavyweight inference, preserving real parser/analysis behavior."""

    def __init__(self, distributions):
        self.distributions = distributions

    def predict(self, moves, **_kwargs):
        key = tuple(moves)
        if key in self.distributions:
            return self.distributions[key]
        board = chess.Board()
        for uci in moves:
            board.push_uci(uci)
        legal = list(board.legal_moves)[:4]
        return {move.uci(): 1 / len(legal) for move in legal}

    def analyze(self, moves, **kwargs):
        return {'moves': self.predict(moves, **kwargs),
                'wdl': [.2, .6, .2], 'think_time': 1.0}


def engine_result(*lines):
    return {'available': True, 'engine': 'Stockfish', 'scope': 'allie-candidates',
            'lines': [{'san': uci, 'uci': uci, 'score': str(cp), 'score_cp': cp,
                       'score_mate': mate, 'depth': 12, 'variation': uci}
                      for uci, cp, mate in lines]}


class AdaptiveAnalysisTests(unittest.TestCase):
    def analyse(self, distributions, **payload):
        settings = {'pgn': '*', 'analysis_source': 'allie', 'preview': False,
                    'player_side': 'white', **payload}
        try:
            return analyse_position(settings, DistributionModel(distributions))
        except ValueError as exc:
            self.fail(f'Legal requested analysis was rejected: {exc}')

    def test_normal_soft_book_preference_reaches_supported_sixth_move(self):
        result = self.analyse({(): {
            'e2e4': .24, 'd2d4': .20, 'g1f3': .18,
            'c2c4': .16, 'b1c3': .13, 'g2g4': .09,
        }}, opening_white='grob')
        self.assertEqual(result['my_moves'][0]['uci'], 'g2g4')
        self.assertEqual(result['my_moves'][0]['probability'], .09)
        self.assertTrue(result['repertoire']['applied'])

    def test_normal_keeps_large_probability_gap_despite_book_preference(self):
        result = self.analyse({(): {
            'e2e4': .60, 'd2d4': .20, 'g1f3': .10,
            'c2c4': .06, 'b1c3': .039, 'g2g4': .001,
        }}, opening_white='grob')
        self.assertEqual(result['my_moves'][0]['uci'], 'e2e4')
        self.assertIn('g2g4', [move['uci'] for move in result['moves']])
        self.assertFalse(result['repertoire']['applied'])

    def test_ragebait_uses_supported_rare_preferred_book_without_new_probability(self):
        result = self.analyse({(): {
            'e2e4': .60, 'd2d4': .20, 'g1f3': .10,
            'c2c4': .06, 'b1c3': .039, 'g2g4': .001,
        }}, opening_white='grob', play_style='ragebait')
        self.assertEqual(result['my_moves'][0]['uci'], 'g2g4')
        self.assertEqual(result['my_moves'][0]['probability'], .001)
        self.assertEqual(result['repertoire']['selection'], 'grob')
        self.assertEqual(result['repertoire']['active_selection'], 'grob')
        self.assertTrue(result['repertoire']['applied'])

    def test_missing_allie_book_support_stays_free_analysis_and_honest(self):
        result = self.analyse({(): {'h2h3': .8, 'a2a3': .2}}, opening_white='grob')
        self.assertEqual(result['my_moves'][0]['uci'], 'h2h3')
        self.assertEqual(result['repertoire']['expected_move'], 'g2g4')
        self.assertIn('active_selection', result['repertoire'])
        self.assertIsNone(result['repertoire']['active_selection'])
        self.assertFalse(result['repertoire']['applied'])
        self.assertNotIn('Allie-Kandidat aus dem Repertoire:', ' '.join(result['plan_messages']))

    def test_unavailable_preferred_family_uses_supported_current_alternative(self):
        result = self.analyse({('e2e4',): {'g8f6': .7, 'e7e5': .3}},
                              pgn='1. e4', player_side='black',
                              opening_black='englund', play_style='ragebait')
        self.assertEqual(result['my_moves'][0]['uci'], 'g8f6')
        self.assertEqual(result['repertoire']['selection'], 'englund')
        self.assertEqual(result['repertoire']['primary'], 'Englund Gambit')
        self.assertEqual(result['repertoire']['active_selection'], 'alekhine')
        self.assertEqual(result['repertoire']['expected_move'], 'g8f6')
        self.assertEqual(result['repertoire']['compatible_openings'], ['Aljechin-Verteidigung'])
        self.assertTrue(result['repertoire']['adaptation_reason'])

    def test_same_move_families_are_combined_without_duplicate_candidates(self):
        result = self.analyse({(): {'e2e4': .8, 'g2g4': .2}},
                              opening_white='vienna', play_style='ragebait')
        self.assertEqual(result['repertoire']['active_selection'], 'vienna')
        self.assertIn('Wiener Gambit', result['repertoire']['compatible_openings'])
        self.assertIn('Dänisches Gambit', result['repertoire']['compatible_openings'])
        self.assertEqual([move['uci'] for move in result['moves']].count('e2e4'), 1)

    def test_deviation_without_current_book_match_keeps_legal_free_analysis(self):
        history = ('a2a3', 'a7a6', 'h2h3', 'h7h6')
        result = self.analyse({history: {'e2e4': .7, 'd2d4': .3}},
                              pgn=' '.join(history), opening_white='halloween',
                              play_style='ragebait')
        self.assertIsNone(result['repertoire']['active_selection'])
        self.assertIsNone(result['repertoire']['expected_move'])
        self.assertTrue(result['my_moves'])

    def test_ragebait_promotes_supported_mate_beyond_its_normal_pool(self):
        history = ('f2f3', 'e7e5', 'g2g4')
        board = chess.Board()
        for uci in history:
            board.push_uci(uci)
        others = [move.uci() for move in board.legal_moves if move.uci() != 'd8h4'][:13]
        distribution = {uci: .999 / len(others) for uci in others}
        distribution['d8h4'] = .001
        result = self.analyse({history: distribution}, pgn=' '.join(history),
                              player_side='black', play_style='ragebait')
        self.assertEqual(result['my_moves'][0]['uci'], 'd8h4')
        self.assertEqual(result['my_moves'][0]['probability'], .001)
        self.assertIn('Schachmatt', result['my_moves'][0]['flags'])

    def test_ragebait_book_priority_cannot_override_mate_in_one_avoidance(self):
        board = chess.Board()
        board.push_uci('f2f3')
        board.push_uci('e7e5')
        book = {**describe_move(board, 'g2g4', .8), 'repertoire': True}
        safe = describe_move(board, 'e2e4', .2)
        try:
            ranked = rank_allie_candidates(board, [book, safe], 'ragebait')
        except ValueError as exc:
            self.fail(f'Ragebait ranking was rejected: {exc}')
        self.assertEqual(ranked[0]['uci'], 'e2e4')
        self.assertEqual(ranked[0]['probability'], .2)

    def test_ragebait_finds_supported_mate_escape_outside_an_all_losing_pool(self):
        history = ('e2e4', 'e7e5', 'f1c4', 'b8c6', 'd1h5')
        # Every listed tempting move permits Qxf7#. The rare ...g6 prevents it.
        unsafe = ('g8e7', 'g8f6', 'f8e7', 'f8d6', 'f8c5', 'f8b4',
                  'f8a3', 'a8b8', 'c6b8', 'c6e7', 'c6a5', 'c6d4')
        distribution = {uci: .999 / len(unsafe) for uci in unsafe}
        distribution['g7g6'] = .001
        result = self.analyse({history: distribution}, pgn=' '.join(history),
                              player_side='black', play_style='ragebait')
        self.assertEqual(result['my_moves'][0]['uci'], 'g7g6')
        self.assertEqual(result['my_moves'][0]['probability'], .001)

    def test_ragebait_rewards_a_real_attack_on_the_opponent_queen(self):
        history = ('e2e4', 'd7d5', 'e4d5', 'd8d5')
        result = self.analyse({history: {'a2a3': .8, 'b1c3': .2}},
                              pgn=' '.join(history), play_style='ragebait')
        self.assertEqual(result['my_moves'][0]['uci'], 'b1c3')
        self.assertEqual(result['my_moves'][0]['probability'], .2)

    def test_engine_demoted_root_has_matching_reply_and_continuation(self):
        distributions = {
            (): {'e2e4': .6, 'd2d4': .4},
            ('e2e4',): {'e7e5': 1.0},
            ('d2d4',): {'d7d5': 1.0},
            ('e2e4', 'e7e5'): {'g1f3': 1.0},
            ('d2d4', 'd7d5'): {'c2c4': 1.0},
        }
        with patch('allie_local_server.stockfish_lines', return_value=engine_result(
                ('e2e4', -400, None), ('d2d4', 0, None))):
            result = self.analyse(distributions, play_style='aggressive',
                                  analysis_source='both', preview=True)
        self.assertEqual(result['my_moves'][0]['uci'], 'd2d4')
        self.assertEqual(result['opponent_moves'][0]['uci'], 'd7d5')
        self.assertEqual(result['premove']['uci'], 'c2c4')

    def test_engine_and_style_never_reorder_opponent_probability_predictions(self):
        for style in ('aggressive', 'ragebait'):
            with self.subTest(style=style), patch(
                    'allie_local_server.stockfish_lines', return_value=engine_result(
                        ('e7e5', -400, None), ('d7d5', 0, None))):
                result = self.analyse({('e2e4',): {'e7e5': .8, 'd7d5': .2}},
                                      pgn='1. e4', player_side='white', play_style=style,
                                      analysis_source='both')
                self.assertEqual([move['uci'] for move in result['opponent_moves']],
                                 ['e7e5', 'd7d5'])

    def test_ragebait_own_reply_and_blue_plan_apply_the_selected_book(self):
        result = self.analyse({
            ('e2e4',): {'e7e5': 1.0},
            ('e2e4', 'e7e5'): {'g1f3': .999, 'e1e2': .001},
        }, pgn='1. e4', player_side='white', opening_white='bongcloud',
            play_style='ragebait', preview=True)
        self.assertEqual(result['my_moves'][0]['uci'], 'e1e2')
        self.assertEqual(result['my_moves'][0]['probability'], .001)
        self.assertEqual(result['premove']['uci'], 'e1e2')
        self.assertEqual(result['premove']['probability'], .001)
        self.assertEqual(result['premove']['coverage'], 1.0)
        self.assertEqual(result['premove']['risk'], 0.0)

    def test_ragebait_blue_continuation_keeps_rare_conditional_probability(self):
        result = self.analyse({
            (): {'e2e4': 1.0},
            ('e2e4',): {'e7e5': 1.0},
            ('e2e4', 'e7e5'): {'g1f3': .999, 'e1e2': .001},
        }, opening_white='bongcloud', play_style='ragebait', preview=True)
        self.assertEqual(result['premove']['uci'], 'e1e2')
        self.assertEqual(result['premove']['probability'], .001)
        self.assertEqual(result['premove']['coverage'], 1.0)

    def test_blue_plan_avoids_mate_across_branches_without_inflating_coverage(self):
        for style in ('aggressive', 'ragebait'):
            with self.subTest(style=style):
                result = self.analyse({
                    ('f2f3',): {'e7e5': .6, 'd7d5': .4},
                    ('f2f3', 'e7e5'): {'e2e4': .99, 'g2g4': .01},
                    ('f2f3', 'd7d5'): {'d2d4': .99, 'g2g4': .01},
                }, pgn='1. f3', player_side='white', play_style=style, preview=True)
                self.assertEqual(result['my_moves'][0]['uci'], 'e2e4')
                self.assertEqual(result['premove']['uci'], 'e2e4')
                self.assertEqual(result['premove']['probability'], .594)
                self.assertEqual(result['premove']['coverage'], .6)
                self.assertEqual(result['premove']['risk'], .4)

    def test_blue_plan_preserves_own_mate_priority_across_branches(self):
        for style in ('aggressive', 'ragebait'):
            with self.subTest(style=style):
                result = self.analyse({
                    ('f2f3', 'e7e5'): {'g2g4': .6, 'h2h3': .4},
                    ('f2f3', 'e7e5', 'g2g4'): {'d8h4': .99, 'e5e4': .01},
                    ('f2f3', 'e7e5', 'h2h3'): {'g8f6': .99, 'e5e4': .01},
                }, pgn='1. f3 e5', player_side='black', play_style=style, preview=True)
                self.assertEqual(result['my_moves'][0]['uci'], 'd8h4')
                self.assertEqual(result['premove']['uci'], 'd8h4')
                self.assertEqual(result['premove']['probability'], .594)
                self.assertEqual(result['premove']['coverage'], .6)
                self.assertEqual(result['premove']['risk'], .4)

    def test_blue_checks_known_danger_even_outside_another_branchs_shortlist(self):
        result = self.analyse({
            ('f2f3',): {'d7d5': .6, 'e7e5': .4},
            ('f2f3', 'd7d5'): {'g2g4': 1.0},
            ('f2f3', 'e7e5'): {'e2e4': 1.0},
        }, pgn='1. f3', player_side='white', play_style='ragebait', preview=True)
        self.assertEqual(result['premove']['uci'], 'e2e4')
        self.assertEqual(result['premove']['probability'], .4)
        self.assertEqual(result['premove']['coverage'], .4)
        self.assertEqual(result['premove']['risk'], .6)

    def test_blue_coverage_keeps_terminal_opponent_branch_in_denominator(self):
        result = self.analyse({
            ('f2f3', 'e7e5', 'g2g4'): {'d8h4': .8, 'a7a6': .2},
            ('f2f3', 'e7e5', 'g2g4', 'a7a6'): {'e2e4': 1.0},
        }, pgn='1. f3 e5 2. g4', player_side='white', play_style='ragebait', preview=True)
        self.assertEqual(result['premove']['uci'], 'e2e4')
        self.assertEqual(result['premove']['probability'], .2)
        self.assertEqual(result['premove']['coverage'], .2)
        self.assertEqual(result['premove']['risk'], .8)

    def test_engine_mate_loss_is_demoted_without_discarding_all_moves(self):
        candidates = [{'uci': 'e2e4', 'probability': .8},
                      {'uci': 'd2d4', 'probability': .2}]
        ordered = safe_aggressive_order(candidates, engine_result(
            ('e2e4', None, -3), ('d2d4', -20, None)))
        self.assertEqual([move['uci'] for move in ordered], ['d2d4', 'e2e4'])
        all_losing = safe_aggressive_order(candidates, engine_result(
            ('e2e4', None, -3), ('d2d4', None, -5)))
        self.assertEqual({move['uci'] for move in all_losing}, {'e2e4', 'd2d4'})

    def test_ragebait_engine_margin_allows_a_gambit_but_demotes_large_loss(self):
        for cp, expected in ((-220, 'g2g4'), (-400, 'e2e4')):
            with self.subTest(cp=cp), patch(
                    'allie_local_server.stockfish_lines', return_value=engine_result(
                        ('g2g4', cp, None), ('e2e4', 0, None))):
                result = self.analyse({(): {'e2e4': .99, 'g2g4': .01}},
                                      opening_white='grob', play_style='ragebait',
                                      analysis_source='both')
                self.assertEqual(result['my_moves'][0]['uci'], expected)
                self.assertEqual(result['repertoire']['applied'], expected == 'g2g4')

    def test_fen_and_unknown_history_do_not_activate_repertoire_or_expose_moves(self):
        with patch('allie_local_server.stockfish_lines', return_value=engine_result(
                ('e2e4', 0, None))):
            result = self.analyse({}, pgn='', fen=chess.STARTING_FEN,
                                  analysis_source='stockfish', play_style='ragebait',
                                  show_moves=False)
        self.assertIsNone(result['repertoire']['expected_move'])
        self.assertIsNone(result['repertoire']['active_selection'])
        self.assertFalse(result['repertoire']['applied'])
        self.assertEqual(result['my_moves'], [])
        self.assertIsNone(result['premove'])

    def test_style_and_adaptation_reach_first_two_hud_messages(self):
        result = self.analyse({('e2e4',): {'g8f6': .7, 'e7e5': .3}},
                              pgn='1. e4', player_side='black', opening_black='englund',
                              play_style='ragebait')
        first_two = ' '.join(result['plan_messages'][:2])
        self.assertIn('Ragebait', first_two)
        self.assertIn('Aljechin', first_two)


if __name__ == '__main__':
    unittest.main()

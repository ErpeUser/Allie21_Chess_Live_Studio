"""Adaptive book choices stay legal and tied to the complete current position."""
from __future__ import annotations

import csv
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import chess
import chess.engine
import chess.pgn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import chess_extras


def moves_for(san: str) -> list[str]:
    board = chess.Board()
    for move in san.split():
        board.push_san(move)
    return [move.uci() for move in board.move_stack]


class AdaptiveRepertoireTests(unittest.TestCase):
    def test_existing_selected_lines_remain_exact_legal_own_turn_choices(self):
        for side in ('white', 'black'):
            options = {**chess_extras.OPENING_OPTIONS[side],
                       **chess_extras.TROLL_OPENING_OPTIONS[side]}
            for selected, (name, line) in options.items():
                board = chess.Board()
                for ply, uci in enumerate(line):
                    if board.turn == (side == 'white'):
                        with self.subTest(side=side, selection=selected, ply=ply):
                            candidates = chess_extras.adaptive_repertoire_candidates(
                                list(line[:ply]), side, selected)
                            match = next(item for item in candidates
                                         if item['selection'] == selected and item['uci'] == uci)
                            self.assertEqual(match, {
                                'selection': selected, 'primary': name, 'uci': uci,
                                'san': board.san(chess.Move.from_uci(uci)),
                                'match': 'exact', 'matched_plies': ply, 'preferred': True,
                            })
                            self.assertEqual(candidates[0]['selection'], selected)
                            identities = {(item['selection'], item['uci']) for item in candidates}
                            self.assertEqual(len(identities), len(candidates))
                            for item in candidates:
                                self.assertIn(chess.Move.from_uci(item['uci']), board.legal_moves)
                    board.push_uci(uci)

    def test_deviations_offer_only_compatible_existing_alternatives(self):
        cases = (
            ('white', 'vienna', 'e4 e5 Nc3 Nf6',
             {('halloween', 'g1f3'), ('frankenstein', 'f1c4')}),
            ('white', 'vienna', 'e4 e5 d4 exd4', {('danish', 'c2c3')}),
            ('black', 'englund', 'e4',
             {('alekhine', 'g8f6'), ('stafford', 'e7e5'), ('traxler', 'e7e5')}),
            ('black', 'englund', 'd4 Nf6 c4', {('budapest', 'e7e5')}),
            ('black', 'stafford', 'e4 e5 Nf3 Nc6 Bc4 Nf6 Ng5', {('traxler', 'f8c5')}),
        )
        for side, selected, san, expected in cases:
            with self.subTest(selection=selected, history=san):
                candidates = chess_extras.adaptive_repertoire_candidates(
                    moves_for(san), side, selected)
                self.assertEqual({(item['selection'], item['uci']) for item in candidates}, expected)
                self.assertTrue(all(not item['preferred'] for item in candidates))

    def test_equal_ply_transpositions_find_the_same_legal_continuation(self):
        cases = (
            ('white', 'halloween', 'e4 e5 Nc3 Nc6 Nf3 Nf6', 'f3e5'),
            ('white', 'steinitz', 'e4 e5 f4 Nc6 Nc3 exf4 d4 Qh4+', 'e1e2'),
            ('black', 'traxler', 'e4 e5 Bc4 Nf6 Nf3 Nc6 Ng5', 'f8c5'),
            ('black', 'stafford', 'Nf3 e5 e4 Nf6 Nxe5', 'b8c6'),
        )
        for side, selected, san, expected in cases:
            with self.subTest(selection=selected):
                history = moves_for(san)
                match = next(item for item in chess_extras.adaptive_repertoire_candidates(
                    history, side, selected) if item['selection'] == selected)
                self.assertEqual(match['uci'], expected)
                self.assertEqual(match['match'], 'transposition')
                self.assertEqual(match['matched_plies'], len(history))
                self.assertTrue(match['preferred'])

    def test_preferred_first_then_stable_opening_order_without_duplicate_moves(self):
        history = moves_for('e4')
        candidates = chess_extras.adaptive_repertoire_candidates(history, 'black', 'stafford')
        self.assertEqual([item['selection'] for item in candidates],
                         ['stafford', 'alekhine', 'traxler'])
        self.assertEqual([item['uci'] for item in candidates], ['e7e5', 'g8f6', 'e7e5'])
        self.assertEqual(candidates, chess_extras.adaptive_repertoire_candidates(
            history, 'black', 'stafford'))
        self.assertEqual(chess_extras.adaptive_repertoire_candidates([], 'white', 'invalid')[0]
                         ['selection'], 'grob')

    def test_equal_ply_matching_keeps_castling_and_legal_en_passant_state(self):
        # These equal-length legal histories isolate state beyond piece placement.
        cases = (
            ('e4 e5 Nf3 Nf6 Ng1 Ng8', 'e4 e5 Ke2 Ke7 Ke1 Ke8', 'g2g4'),
            ('e4 a6 e5 d5', 'e4 d5 e5 a6', 'h2h3'),
        )
        for book_san, actual_san, continuation in cases:
            with self.subTest(history=actual_san):
                book_moves, actual_moves = moves_for(book_san), moves_for(actual_san)
                book_board, actual_board = chess.Board(), chess.Board()
                for move in book_moves:
                    book_board.push_uci(move)
                for move in actual_moves:
                    actual_board.push_uci(move)
                self.assertEqual(len(book_moves), len(actual_moves))
                self.assertEqual(book_board.board_fen(), actual_board.board_fen())
                self.assertNotEqual(chess_extras.epd_key(book_board),
                                    chess_extras.epd_key(actual_board))
                self.assertIn(chess.Move.from_uci(continuation), actual_board.legal_moves)
                with patch.dict(chess_extras.OPENING_OPTIONS['white'], {
                    'grob': ('Position-state fixture', (*book_moves, continuation)),
                }):
                    self.assertTrue(chess_extras.adaptive_repertoire_candidates(
                        book_moves, 'white', 'grob'))
                    self.assertEqual(chess_extras.adaptive_repertoire_candidates(
                        actual_moves, 'white', 'grob'), [])

    def test_invalid_history_side_and_opponent_turn_produce_no_advice(self):
        cases = (
            ([], 'unknown'), ([], 'black'), (moves_for('e4'), 'white'),
            (['e2e5'], 'white'), (['not-a-move'], 'white'), (['0000'], 'white'),
            (['e2e4', 'e2e3'], 'white'), ([None], 'white'),
        )
        for history, side in cases:
            with self.subTest(history=history, side=side):
                self.assertEqual(chess_extras.adaptive_repertoire_candidates(history, side), [])

    def test_exhausted_or_unrelated_lines_and_late_repetition_do_not_restart_a_book(self):
        for san in ('g4 e5', 'e4 e5 Ke2 Nc6', ' '.join(['Nf3 Nf6 Ng1 Ng8'] * 12)):
            with self.subTest(history=san):
                self.assertEqual(chess_extras.adaptive_repertoire_candidates(
                    moves_for(san), 'white'), [])

    def test_verified_trap_continuations_remain_available_after_the_short_opening(self):
        cases = (
            ('white', 'halloween', 'e4 e5 Nf3 Nc6 Nc3 Nf6 Nxe5 Nxe5', 'd2d4'),
            ('black', 'stafford', 'e4 e5 Nf3 Nf6 Nxe5 Nc6 Nxc6', 'd7c6'),
            ('black', 'stafford', 'e4 e5 Nf3 Nf6 Nxe5 Nc6 Nxc6 dxc6 Nc3', 'f8c5'),
            ('black', 'stafford', 'e4 e5 Nf3 Nf6 Nxe5 Nc6 Nxc6 dxc6 d3', 'f8c5'),
            ('black', 'traxler', 'e4 e5 Nf3 Nc6 Bc4 Nf6 Ng5 Bc5 Nxf7', 'c5f2'),
            ('black', 'traxler', 'e4 e5 Nf3 Nc6 Bc4 Nf6 Ng5 Bc5 Nxf7 Bxf2+ Kxf2', 'f6e4'),
        )
        for side, selected, san, expected in cases:
            with self.subTest(selection=selected, history=san):
                candidates = chess_extras.adaptive_repertoire_candidates(
                    moves_for(san), side, selected)
                self.assertEqual(candidates[0]['selection'], selected)
                self.assertEqual(candidates[0]['uci'], expected)

    def test_added_trap_lines_are_exactly_sourced_from_the_bundled_eco(self):
        source_lines = set()
        with (chess_extras.BASE / 'openings' / 'c.tsv').open(
                encoding='utf-8-sig', newline='') as handle:
            for row in csv.DictReader(handle, delimiter='\t'):
                game = chess.pgn.read_game(io.StringIO(row['pgn']))
                if game is not None and not game.errors:
                    source_lines.add(tuple(move.uci() for move in game.mainline_moves()))
        for families in chess_extras.ADAPTIVE_TRAP_LINES.values():
            for lines in families.values():
                for line in lines:
                    self.assertIn(line, source_lines)
                    self.assertLessEqual(len(line), 16)


class StockfishMateMetadataTests(unittest.TestCase):
    def test_zero_and_forced_mate_scores_keep_their_actual_values(self):
        board = chess.Board()
        engine = Mock()
        engine.analyse.return_value = [
            {'pv': [chess.Move.from_uci('e2e4')],
             'score': chess.engine.PovScore(score, chess.WHITE), 'depth': 12}
            for score in (chess.engine.Cp(0), chess.engine.Mate(3), chess.engine.Mate(-2))
        ]
        with patch('chess_extras.find_stockfish', return_value='fake-stockfish'), \
                patch('chess_extras._get_stockfish', return_value=engine):
            result = chess_extras.stockfish_lines(board)
        self.assertTrue(result['available'])
        self.assertEqual(result['scope'], 'position')
        self.assertEqual([(line['score_cp'], line['score_mate'], line['score'])
                          for line in result['lines']],
                         [(0, None, '+0.00'), (None, 3, 'Matt +3'), (None, -2, 'Matt -2')])


if __name__ == '__main__':
    unittest.main()

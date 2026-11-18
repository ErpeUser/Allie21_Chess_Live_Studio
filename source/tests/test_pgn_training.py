"""Legal, bounded local PGN replay; no model, engine, or private metadata."""
from __future__ import annotations

import importlib
import io
import logging
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))


def replay(pgn):
    # An explicit assertion also gives the feature's initial RED run a useful
    # failure when the new module has not been implemented yet.
    assert importlib.util.find_spec("pgn_training") is not None, "Lokaler PGN-Rückblick fehlt"
    return importlib.import_module("pgn_training").build_replay(pgn)


class PgnTrainingTests(unittest.TestCase):
    def test_mainline_replays_each_position_with_legal_san_and_fen(self):
        result = replay("1. e4 e5 2. Nf3 Nc6 *")
        self.assertEqual(result["ply_count"], 4)
        self.assertEqual(len(result["positions"]), 5)
        self.assertEqual(result["positions"][0]["fen"],
                         "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        self.assertEqual(result["positions"][1]["fen"],
                         "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")
        self.assertEqual(result["positions"][4]["fen"],
                         "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        self.assertEqual(result["positions"][2]["last_move_label"], "1... e5")
        self.assertEqual(result["positions"][3]["uci"], "g1f3")
        self.assertEqual(result["positions"][3]["san"], "Nf3")
        self.assertEqual(result["positions"][3]["turn"], "black")

    def test_comments_variations_names_and_urls_are_not_returned(self):
        result = replay('[White "Private Player"]\n[Site "https://private.invalid/game"]\n\n'
                        '1. e4 { private notes } (1. d4 d5) e5 $1 *')
        self.assertEqual(result["ply_count"], 2)
        self.assertEqual([p["uci"] for p in result["positions"]], ["", "e2e4", "e7e5"])
        for sensitive in ("Private Player", "private.invalid", "private notes"):
            self.assertNotIn(sensitive, str(result))

    def test_castling_and_en_passant_are_replayed_from_the_full_history(self):
        castled = replay("1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. O-O *")["positions"][-1]
        self.assertEqual(castled["san"], "O-O")
        self.assertEqual(castled["fen"],
                         "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQ1RK1 b kq - 5 4")
        capture = replay("1. e4 a6 2. e5 d5 3. exd6 *")["positions"][-1]
        self.assertEqual(capture["fen"],
                         "rnbqkbnr/1pp1pppp/p2P4/8/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 3")

    def test_checkmate_is_displayed_as_the_actual_final_board(self):
        result = replay("1. f3 e5 2. g4 Qh4# 0-1")
        final = result["positions"][-1]
        self.assertEqual(final["ply"], 4)
        self.assertEqual(final["san"], "Qh4#")
        self.assertTrue(final["in_check"])
        self.assertTrue(final["game_over"])
        self.assertEqual(final["turn"], "white")

    def test_invalid_or_null_moves_fail_without_logging_private_pgn(self):
        capture = io.StringIO()
        handler = logging.StreamHandler(capture)
        logger = logging.getLogger("chess.pgn")
        logger.addHandler(handler)
        try:
            for pgn in ('[White "Private Player"]\n\n1. e4 e5 2. Bh6 *',
                        "1. e4 -- *", "1. e4 e5 2. Ke2 Ke7 3. Ke1 Ke8 4. O-O *"):
                with self.subTest(pgn=pgn), self.assertRaises(ValueError) as caught:
                    replay(pgn)
                self.assertNotIn("Private Player", str(caught.exception))
                self.assertNotIn("rnbq", str(caught.exception))
            self.assertEqual(capture.getvalue(), "")
        finally:
            logger.removeHandler(handler)

    def test_rejects_multiple_games_variants_and_setup_positions(self):
        for pgn in ("1. e4 1-0\n\n1. d4 0-1",
                    '[Variant "Atomic"]\n\n1. e4 *',
                    '[SetUp "1"]\n[FEN "8/8/8/3k4/8/8/4K3/8 w - - 0 1"]\n\n1. Kd3 *'):
            with self.subTest(pgn=pgn), self.assertRaises(ValueError):
                replay(pgn)

    def test_empty_and_oversized_input_cannot_produce_a_partial_replay(self):
        for pgn in ("", "   ", "garbage", "*", '{' + "x" * 40000 + '} 1. e4 *'):
            with self.subTest(length=len(pgn)), self.assertRaises(ValueError):
                replay(pgn)
        with self.assertRaises(TypeError):
            replay(None)

    def test_move_limit_matches_the_existing_allie_history_boundary(self):
        # The analysis API accepts at most 1013 plies (< 1014). Training uses
        # the same bounded history contract without loading that API or model.
        accepted = replay(" ".join(["Nf3 Nf6 Ng1 Ng8"] * 253) + " Nf3 *")
        self.assertEqual(accepted["ply_count"], 1013)
        with self.assertRaises(ValueError):
            replay(" ".join(["Nf3 Nf6 Ng1 Ng8"] * 253) + " Nf3 Nf6 *")


if __name__ == "__main__":
    unittest.main()

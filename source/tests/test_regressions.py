import os
import sys
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT, "source", "app", "backend"))

from security import RequestRateLimiter


class RegressionTests(unittest.TestCase):
    def test_rate_limiter_has_a_hard_key_bound(self):
        now = [0.0]
        limiter = RequestRateLimiter(clock=lambda: now[0], max_keys=4)
        for index in range(20):
            self.assertEqual(limiter.allow(f"session-{index}", 1, 60), index < 4)
        self.assertLessEqual(limiter.key_count, 4)
        # A fresh key must not evict an exhausted window and reset its budget.
        self.assertFalse(limiter.allow("session-0", 1, 60))
        now[0] = 60.0
        self.assertTrue(limiter.allow("new-session", 1, 60))

    def test_parse_history_rejects_multiple_games(self):
        try:
            from allie_local_server import parse_history
        except ModuleNotFoundError as exc:
            if exc.name == "chess":
                self.skipTest("python-chess is supplied by the locked project environment")
            raise
        pgn = "1. e4 e5 2. Nf3 Nc6 1-0\n\n1. d4 d5 2. c4 e6 1/2-1/2"
        with self.assertRaises(ValueError):
            parse_history(pgn)

    def test_analysis_cache_ignores_live_cursor_metadata(self):
        try:
            import allie_local_server as server
        except ModuleNotFoundError as exc:
            if exc.name == "chess":
                self.skipTest("python-chess is supplied by the locked project environment")
            raise
        calls = []

        def fake_uncached(payload):
            calls.append(dict(payload))
            return {"fen": payload.get("fen", ""), "moves": []}

        server._ANALYSIS_CACHE.clear()
        with patch.object(server, "_analyse_position_uncached", side_effect=fake_uncached):
            base = {"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "analysis_source": "stockfish"}
            server.analyse_position({**base, "session_id": "a", "generation": 1, "render_revision": 1})
            server.analyse_position({**base, "session_id": "b", "generation": 2, "render_revision": 9})
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()

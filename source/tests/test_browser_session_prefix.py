import sys
from pathlib import Path

import chess

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))

from browser_session import BrowserTrackerPool


def _board(*moves):
    board = chess.Board()
    for move in moves:
        board.push_uci(move)
    return board


def test_full_candidate_can_sync_to_an_earlier_manual_history_position():
    pool = BrowserTrackerPool()
    current = _board('e2e4', 'e7e5', 'g1f3')
    full_pgn = '1. e4 e5 2. Nf3'
    first = pool.observe('history-test', current.board_fen(), notations=[full_pgn])
    assert first['ready'] is True
    earlier = _board('e2e4')
    second = pool.observe('history-test', earlier.board_fen(), notations=[full_pgn])
    assert second['ready'] is True
    assert second['pgn'] == 'e2e4'


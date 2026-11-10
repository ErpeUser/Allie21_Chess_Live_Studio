"""Small reproducible runtime benchmark; never fabricates missing model data."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import chess
import chess.engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from chess_extras import find_stockfish


FENS = [chess.STARTING_FEN, 'r1bqk2r/pppp1ppp/2n2n2/4p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5']


def percentile(values: list[float], fraction: float) -> float:
    return statistics.quantiles(values, n=100, method='inclusive')[max(0, int(fraction * 100) - 1)] if len(values) > 1 else values[0]


def stockfish_benchmark() -> dict[str, object]:
    path = find_stockfish()
    if not path:
        return {'status': 'SKIPPED', 'reason': 'Stockfish unavailable'}
    timings: list[float] = []
    with chess.engine.SimpleEngine.popen_uci(str(path)) as engine:
        for fen in FENS:
            start = time.perf_counter_ns()
            result = engine.analyse(chess.Board(fen), chess.engine.Limit(time=0.08), multipv=1)
            elapsed = (time.perf_counter_ns() - start) / 1_000_000
            timings.append(elapsed)
            if not result:
                raise RuntimeError('Stockfish returned no analysis')
    return {'status': 'PASS', 'count': len(timings), 'p50_ms': statistics.median(timings),
            'p95_ms': percentile(timings, .95), 'max_ms': max(timings)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--stockfish', action='store_true')
    parser.add_argument('--with-model', action='store_true')
    parser.add_argument('--all', action='store_true')
    args = parser.parse_args()
    if not (args.stockfish or args.with_model or args.all):
        parser.error('one of --stockfish, --with-model or --all is required')
    result: dict[str, object] = {'timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    if args.stockfish or args.all:
        result['stockfish'] = stockfish_benchmark()
    if args.with_model or args.all:
        result['model'] = {'status': 'SKIPPED', 'reason': 'model benchmark requires explicit local weight run'}
    output = ROOT / '.build' / 'benchmarks' / 'latest.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

"""Compare tactical_hints with a local Git baseline; no model or engine startup.

Example: python tools/benchmark_tactical.py --baseline-ref <commit> --runs 25
The baseline must be a trusted local repository revision. Only its tactical
function is loaded, so importing an older server cannot trigger prewarming.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from types import CodeType, FunctionType
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

import chess
from chess_extras import tactical_hints

CASES = {
    'starting_position': chess.STARTING_FEN,
    'ruy_lopez': 'r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3',
    'middlegame_castling': 'r3k2r/p1ppqpb1/bn2pnp1/2P5/1p2P3/2N2N2/PPQBBPPP/R3K2R w KQkq - 0 1',
    'mate_in_one': '7k/5K2/6Q1/8/8/8/8/8 w - - 0 1',
    'mate_in_two': 'kr6/1r1N4/2Q5/8/8/8/8/K7 w - - 0 1',
    'rook_endgame': '7k/8/5K2/8/8/8/8/R7 w - - 0 1',
    'promotion': '7k/5P2/6K1/8/8/8/8/8 w - - 0 1',
    'en_passant': '7k/8/8/3pP3/8/8/8/K7 w - d6 0 1',
    'stalemate': '7k/5K2/6Q1/8/8/8/8/8 b - - 0 1',
    'checkmate': '7k/6Q1/6K1/8/8/8/8/8 b - - 0 1',
}
HintFunction = Callable[[chess.Board], list[str]]


def git(*args: str) -> str:
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def baseline_function(revision: str) -> tuple[HintFunction, str, str]:
    commit = git('rev-parse', '--verify', '--end-of-options', f'{revision}^{{commit}}')
    blob = git('rev-parse', f'{commit}:backend/chess_extras.py')
    source = git('show', f'{commit}:backend/chess_extras.py')
    tree = ast.parse(source)
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == 'tactical_hints')
    compiled = compile(ast.Module(body=[function], type_ignores=[]),
                       f'{commit}:backend/chess_extras.py', 'exec')
    # Instantiate only the function body; never run module startup statements.
    code = next(item for item in compiled.co_consts
                if isinstance(item, CodeType) and item.co_name == 'tactical_hints')
    return FunctionType(code, {'chess': chess}), commit, blob


def summary(values: list[float]) -> dict[str, float | list[float]]:
    return {
        'median_ms': statistics.median(values),
        'p95_ms': sorted(values)[math.ceil(len(values) * .95) - 1],
        'raw_ms': values,
    }


def measure(function: HintFunction, fen: str) -> tuple[list[str], float, float]:
    board = chess.Board(fen)
    before = board.copy(stack=True)
    wall_start = time.perf_counter_ns()
    cpu_start = time.process_time_ns()
    result = function(board)
    cpu_ms = (time.process_time_ns() - cpu_start) / 1_000_000
    wall_ms = (time.perf_counter_ns() - wall_start) / 1_000_000
    if board != before or board.move_stack != before.move_stack:
        raise AssertionError('tactical_hints changed its input board')
    return result, wall_ms, cpu_ms


def benchmark(revision: str, runs: int, warmups: int) -> dict:
    baseline, commit, blob = baseline_function(revision)
    functions = {'baseline': baseline, 'candidate': tactical_hints}
    samples: dict = {}
    totals = {arm: {'wall_ms': [0.0] * runs, 'cpu_ms': [0.0] * runs}
              for arm in functions}
    for name, fen in CASES.items():
        if not chess.Board(fen).is_valid():
            raise AssertionError(f'Invalid fixture: {name}')
        expected, _, _ = measure(baseline, fen)
        samples[name] = {'fen': fen, 'output': expected, 'arms': {}}
        for arm, function in functions.items():
            for _ in range(warmups):
                actual, _, _ = measure(function, fen)
                if actual != expected:
                    raise AssertionError(f'Output differs: {name}/{arm}')
            samples[name]['arms'][arm] = {'wall_ms': [], 'cpu_ms': []}

    # Alternate arm order on every round, on the same fixed FEN corpus.
    # Board creation, validation, mocks and JSON output are outside timings.
    for index in range(runs):
        arms = tuple(functions) if index % 2 == 0 else tuple(reversed(functions))
        for name, fen in CASES.items():
            for arm in arms:
                actual, wall_ms, cpu_ms = measure(functions[arm], fen)
                if actual != samples[name]['output']:
                    raise AssertionError(f'Output differs: {name}/{arm}/{index}')
                for metric, value in (('wall_ms', wall_ms), ('cpu_ms', cpu_ms)):
                    samples[name]['arms'][arm][metric].append(value)
                    totals[arm][metric][index] += value

    for case in samples.values():
        for arm, function in functions.items():
            with patch.object(chess.Board, 'san', autospec=True,
                              side_effect=chess.Board.san) as san:
                actual = function(chess.Board(case['fen']))
            if actual != case['output']:
                raise AssertionError('Instrumented output differs')
            case['arms'][arm] = {
                **{metric: summary(values) for metric, values in case['arms'][arm].items()},
                'san_calls': san.call_count,
            }

    return {
        'status': 'PASS',
        'baseline_commit': commit,
        'baseline_blob': blob,
        'candidate_source_sha256': hashlib.sha256(
            (ROOT / 'backend/chess_extras.py').read_bytes()).hexdigest(),
        'python': sys.version,
        'python_chess': chess.__version__,
        'platform': platform.platform(),
        'cpu_count': os.cpu_count(),
        'runs_per_case_per_arm': runs,
        'warmups_per_case_per_arm': warmups,
        'method': 'Alternating paired arms; nearest-rank P95; GC unchanged; input construction excluded',
        'scope': 'Synthetic local tactical scan only; no model, GPU, network or Stockfish',
        'output_equality': True,
        'board_unchanged': True,
        'cases': samples,
        'suite_totals': {arm: {metric: summary(values) for metric, values in measures.items()}
                         for arm, measures in totals.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-ref', required=True)
    parser.add_argument('--runs', type=int, default=25)
    parser.add_argument('--warmups', type=int, default=3)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.runs < 2 or args.warmups < 0:
        parser.error('--runs must be at least 2 and --warmups must be nonnegative')
    result = json.dumps(benchmark(args.baseline_ref, args.runs, args.warmups),
                        ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding='utf-8')
    else:
        print(result, end='')


if __name__ == '__main__':
    main()

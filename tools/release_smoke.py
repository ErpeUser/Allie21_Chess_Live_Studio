"""Offline smoke test for a portable Allie release bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

STOCKFISH_SHA256 = '45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0'
FORBIDDEN = {'pytest', 'ruff', 'mypy', 'playwright'}


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def verify_manifest(bundle: Path) -> None:
    manifest = bundle / 'SHA256SUMS.txt'
    if not manifest.is_file():
        raise RuntimeError('SHA256SUMS.txt fehlt')
    count = 0
    for line in manifest.read_text(encoding='utf-8-sig').splitlines():
        digest, relative = line.split('  ', 1)
        path = (bundle / relative).resolve()
        if not path.is_relative_to(bundle.resolve()):
            raise RuntimeError('Invalid manifest path')
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f'SHA-256 stimmt nicht: {relative}')
        count += 1
    if not count:
        raise RuntimeError('Empty release manifest')


def stop_process(process) -> str:
    """Drain stdout only after termination; a read() on a live child can hang."""
    if process.poll() is None:
        process.terminate()
    try:
        output, _ = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        output, _ = process.communicate(timeout=5)
    return (output or '')[-4000:]


def run(bundle: Path, with_model: bool = False) -> int:
    app, runtime = bundle / 'app', bundle / 'runtime'
    runtime_python = runtime / ('python.exe' if os.name == 'nt' else 'bin/python')
    for path in (bundle / 'Allie21 Chess Live Studio.exe', runtime_python, app / 'backend/live_server.py'):
        if not path.is_file():
            raise RuntimeError(f'Bundle-Datei fehlt: {path.relative_to(bundle)}')
    verify_manifest(bundle)
    stockfish = app / 'backend' / 'engines' / ('stockfish.exe' if os.name == 'nt' else 'stockfish')
    if not stockfish.is_file() or hashlib.sha256(stockfish.read_bytes()).hexdigest() != STOCKFISH_SHA256:
        raise RuntimeError('Stockfish fehlt oder SHA-256 stimmt nicht')
    inventory = app / 'runtime-packages.json'
    names = {str(item.get('name', '')).lower() for item in json.loads(inventory.read_text(encoding='utf-8'))}
    if names & FORBIDDEN:
        raise RuntimeError(f'Quality-Paket im Runtime-Inventar: {sorted(names & FORBIDDEN)}')
    env = os.environ.copy()
    env.update({'ALLIE_NO_PRELOAD': '1', 'ALLIE_NO_BROWSER': '1', 'ALLIE_PORT': str(free_port()),
                'PYTHONPATH': str(app / 'backend')})
    process = subprocess.Popen([str(runtime_python), str(app / 'backend/live_server.py')],
                               cwd=app, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True)
    ready = False
    output = ''
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and process.poll() is None:
            try:
                with urlopen(f"http://127.0.0.1:{env['ALLIE_PORT']}/health", timeout=1) as response:
                    if response.status == 200:
                        ready = True
                        break
            except OSError:
                time.sleep(0.25)
    finally:
        output = stop_process(process)
    if not ready:
        raise RuntimeError(f'Server wurde nicht bereit: {output}')
    print('RELEASE SMOKE: PASS (HTTP readiness; not a GUI/model acceptance test)')
    print('MODEL SMOKE: NOT RUN' + (' - local weights verification still required' if with_model else ''))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--with-model', action='store_true')
    args = parser.parse_args()
    return run(args.bundle.resolve(), args.with_model)


if __name__ == '__main__':
    raise SystemExit(main())

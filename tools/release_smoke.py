"""Offline smoke test for a portable Allie release bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
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
    for line in manifest.read_text(encoding='utf-8-sig').splitlines():
        digest, relative = line.split('  ', 1)
        path = bundle / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f'SHA-256 stimmt nicht: {relative}')


def run(bundle: Path, with_model: bool = False) -> int:
    app = bundle / 'app'
    runtime = bundle / 'runtime'
    runtime_python = runtime / ('python.exe' if os.name == 'nt' else 'bin/python')
    exe = bundle / 'Allie21 Chess Live Studio.exe'
    for path in (exe, runtime_python, app / 'backend' / 'live_server.py'):
        if not path.is_file():
            raise RuntimeError(f'Bundle-Datei fehlt: {path.relative_to(bundle)}')
    verify_manifest(bundle)
    stockfish = app / 'backend' / 'engines' / ('stockfish.exe' if os.name == 'nt' else 'stockfish')
    if not stockfish.is_file():
        raise RuntimeError('Stockfish fehlt')
    digest = hashlib.sha256(stockfish.read_bytes()).hexdigest()
    if digest != STOCKFISH_SHA256:
        raise RuntimeError('Stockfish-SHA-256 stimmt nicht')
    inventory = app / 'runtime-packages.json'
    if not inventory.is_file():
        raise RuntimeError('runtime-packages.json fehlt')
    names = {str(item.get('name', '')).lower() for item in json.loads(inventory.read_text(encoding='utf-8'))}
    if names & FORBIDDEN:
        raise RuntimeError(f'Quality-Paket im Runtime-Inventar: {sorted(names & FORBIDDEN)}')
    env = os.environ.copy()
    env.update({'ALLIE_NO_PRELOAD': '1', 'ALLIE_NO_BROWSER': '1', 'ALLIE_PORT': str(free_port()),
                'PYTHONPATH': str(app / 'backend')})
    process = subprocess.Popen([str(runtime_python), str(app / 'backend' / 'live_server.py')],
                               cwd=app, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True)
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                with urlopen(f"http://127.0.0.1:{env['ALLIE_PORT']}/health", timeout=1) as response:
                    if response.status == 200:
                        print('RELEASE SMOKE: PASS')
                        break
            except OSError:
                time.sleep(0.25)
        else:
            output = process.stdout.read(4000) if process.stdout else ''
            raise RuntimeError(f'Server wurde nicht bereit: {output}')
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    if with_model:
        print('MODEL SMOKE: NOT RUN - explicit model flag requires local weights verification')
    else:
        print('MODEL SMOKE: NOT RUN - use --with-model only with local weights')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--with-model', action='store_true')
    args = parser.parse_args()
    return run(args.bundle.resolve(), args.with_model)


if __name__ == '__main__':
    raise SystemExit(main())

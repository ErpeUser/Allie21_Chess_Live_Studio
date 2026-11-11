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
from urllib.request import Request, urlopen

STOCKFISH_SHA256 = '45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0'
FORBIDDEN = {'pytest', 'ruff', 'mypy', 'playwright'}


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def verify_release_version(bundle: Path) -> dict[str, object]:
    """Validate the machine-readable version proof emitted by the build."""
    path = bundle / 'app' / 'release-version.json'
    if not path.is_file():
        raise RuntimeError('app/release-version.json fehlt')
    try:
        record = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError('Ungültiger Versionsnachweis') from exc
    required = ('app_version', 'userscript_version', 'extension_version',
                'extension_version_name', 'source_revision', 'built_at_utc')
    if not isinstance(record, dict) or any(not record.get(key) for key in required):
        raise RuntimeError('Versionsnachweis ist unvollständig')
    if record['app_version'] != record['userscript_version']:
        raise RuntimeError('App- und Userscript-Version weichen ab')
    if str(record['extension_version_name']) != '.'.join(str(record['extension_version']).split('.')[:3]):
        raise RuntimeError('Extension-Version im Nachweis ist inkonsistent')
    return record


def fetch_json(url: str, *, timeout: float = 1.0) -> tuple[int, dict[str, object]]:
    request = Request(url, headers={'Accept': 'application/json', 'X-Allie-Smoke': '1'})
    with urlopen(request, timeout=timeout) as response:
        status = int(response.status)
        payload = json.loads(response.read(64 * 1024).decode('utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('JSON-Antwort ist kein Objekt')
    return status, payload


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
    """Stop only the smoke child and drain output without blocking."""
    if process.poll() is None:
        if os.name == 'nt' and getattr(process, 'pid', None):
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           capture_output=True, check=False)
        else:
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
    verify_release_version(bundle)
    stockfish = app / 'backend' / 'engines' / ('stockfish.exe' if os.name == 'nt' else 'stockfish')
    if not stockfish.is_file() or hashlib.sha256(stockfish.read_bytes()).hexdigest() != STOCKFISH_SHA256:
        raise RuntimeError('Stockfish fehlt oder SHA-256 stimmt nicht')
    inventory = app / 'runtime-packages.json'
    names = {str(item.get('name', '')).lower() for item in json.loads(inventory.read_text(encoding='utf-8'))}
    if names & FORBIDDEN:
        raise RuntimeError(f'Quality-Paket im Runtime-Inventar: {sorted(names & FORBIDDEN)}')
    env = os.environ.copy()
    env.update({'ALLIE_NO_BROWSER': '1', 'ALLIE_PORT': str(free_port()),
                'PYTHONPATH': str(app / 'backend')})
    # Exercise the actual double-click entry point on Windows.  Linux/macOS
    # CI cannot execute a PE bundle, so it uses the same bundled runtime and
    # backend path directly while preserving all HTTP checks.
    command = ([str(bundle / 'Allie21 Chess Live Studio.exe')] if os.name == 'nt'
               else [str(runtime_python), str(app / 'backend/live_server.py')])
    if not with_model:
        env['ALLIE_NO_PRELOAD'] = '1'
    process = subprocess.Popen(command, cwd=(bundle if os.name == 'nt' else app), env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    alive = False
    ready = False
    model_loaded = False
    stockfish_available = False
    output = ''
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and process.poll() is None:
            try:
                status, health = fetch_json(f"http://127.0.0.1:{env['ALLIE_PORT']}/health")
                if status == 200 and health.get('alive') is True:
                    alive = True
                    model_loaded = health.get('model_loaded') is True
                    stockfish_available = health.get('stockfish_available') is True
                    if with_model:
                        try:
                            ready_status, ready_payload = fetch_json(
                                f"http://127.0.0.1:{env['ALLIE_PORT']}/readyz?source=both")
                            ready = ready_status == 200 and ready_payload.get('ready') is True
                        except (OSError, ValueError, TimeoutError):
                            ready = False
                    else:
                        ready = health.get('ready') is True
                    if alive and (ready or not with_model):
                        break
            except (OSError, ValueError, TimeoutError):
                pass
            time.sleep(0.25)
    finally:
        output = stop_process(process)
    if not alive:
        raise RuntimeError(f'Server wurde nicht lebendig: {output}')
    if with_model and not (ready and model_loaded and stockfish_available):
        raise RuntimeError(
            'Server wurde lebendig, aber nicht bereit: '
            f'ready={ready}, model_loaded={model_loaded}, '
            f'stockfish_available={stockfish_available}; {output}'
        )
    print('RELEASE SMOKE: PASS (alive=true; ready/model checks=' + ('required' if with_model else 'optional') + ')')
    print('MODEL SMOKE: PASS' if with_model else 'MODEL SMOKE: NOT RUN - local weights verification still required')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--with-model', action='store_true')
    args = parser.parse_args()
    return run(args.bundle.resolve(), args.with_model)


if __name__ == '__main__':
    raise SystemExit(main())

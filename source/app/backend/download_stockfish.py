#!/usr/bin/env python3
"""Stream and atomically install the hash-pinned Stockfish Windows release."""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Protocol
from urllib.request import Request, urlopen

URL = 'https://github.com/official-stockfish/Stockfish/releases/download/sf_19/stockfish-windows-x86-64-universal.zip'
EXPECTED_SHA256 = '3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7'
EXPECTED_EXE_SHA256 = '45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0'
SOURCE_ROOT = Path(__file__).resolve().parents[3] if Path(__file__).resolve().parents[2].name == 'source' else None
DEST = ((SOURCE_ROOT / 'generated' / 'dependencies' / 'engines') if SOURCE_ROOT
        else Path(__file__).resolve().parent / 'engines')
MAX_ARCHIVE_SIZE = 125_000_000
MAX_EXE_SIZE = 175_000_000
CHUNK_SIZE = 1024 * 1024


def portable_engine_path(project_root: Path) -> Path:
    """Find the pinned executable that a source checkout may already bundle."""
    root = (project_root.parents[1] if project_root.name == 'app'
            and project_root.parent.name == 'source' else project_root)
    return (root / 'generated' / 'dist' / 'win' / 'Allie21 Chess Live Studio'
            / 'app' / 'backend' / 'engines' / 'stockfish.exe')


class _ReadableBinary(Protocol):
    def read(self, size: int = -1) -> bytes: ...


class _WritableBinary(Protocol):
    def write(self, data: bytes) -> int: ...


def verified_executable(path: Path) -> bool:
    """Check the actual binary, without starting it or accessing the network."""
    try:
        if not path.is_file() or not 0 < path.stat().st_size <= MAX_EXE_SIZE:
            return False
        with path.open('rb') as source:
            return hashlib.file_digest(source, 'sha256').hexdigest() == EXPECTED_EXE_SHA256
    except OSError:
        return False


def _copy_verified(source: _ReadableBinary, destination: _WritableBinary,
                   limit: int, expected: str) -> int:
    digest = hashlib.sha256()
    total = 0
    while chunk := source.read(CHUNK_SIZE):
        total += len(chunk)
        if total > limit:
            raise RuntimeError('Stockfish file exceeds the allowed size')
        digest.update(chunk)
        destination.write(chunk)
    if total == 0 or digest.hexdigest() != expected:
        raise RuntimeError('Stockfish SHA-256 verification failed')
    return total


def download() -> bool:
    if os.name != 'nt':
        print('Windows x64 executable only. On other systems install stockfish with your package manager.')
        return False
    target = DEST / 'stockfish.exe'
    if verified_executable(target):
        print('Stockfish ist verifiziert:', target)
        return True
    bundled = portable_engine_path(Path(__file__).resolve().parents[1])
    if verified_executable(bundled):
        print('Nutze bereits verifiziertes Stockfish im portablen Release:', bundled)
        return True
    DEST.mkdir(exist_ok=True, parents=True)
    print('Pruefe und installiere die offizielle Stockfish-19-Datei ...')
    request = Request(URL, headers={'User-Agent': 'Allie21ChessLiveStudio/Stockfish19'})
    # Disk-backed archive avoids retaining the entire download in RAM. The old
    # executable is untouched until both independent digest checks succeeded.
    with tempfile.TemporaryFile(dir=DEST) as archive_file:
        with urlopen(request, timeout=120) as response:
            _copy_verified(response, archive_file, MAX_ARCHIVE_SIZE, EXPECTED_SHA256)
        archive_file.seek(0)
        with zipfile.ZipFile(archive_file) as archive:
            candidates = [entry for entry in archive.infolist()
                          if not entry.is_dir() and entry.filename.lower().endswith('.exe')
                          and 'stockfish' in entry.filename.lower()]
            if len(candidates) != 1:
                raise RuntimeError('Expected exactly one Stockfish executable in the pinned archive')
            entry = candidates[0]
            if not 0 < entry.file_size <= MAX_EXE_SIZE:
                raise RuntimeError('Stockfish executable size is invalid')
            temporary = None
            try:
                # Unique name also prevents concurrent installers from writing
                # the same partial file. Close it before replace on Windows.
                with tempfile.NamedTemporaryFile(
                    dir=DEST, prefix='.stockfish-', suffix='.part', delete=False
                ) as output:
                    temporary = target.with_name(os.path.basename(output.name))
                    with archive.open(entry) as source:
                        size = _copy_verified(source, output, MAX_EXE_SIZE, EXPECTED_EXE_SHA256)
                    if size != entry.file_size:
                        raise RuntimeError('Stockfish executable was truncated')
                    output.flush()
                    os.fsync(output.fileno())
                temporary.replace(target)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
    print('Installed and verified:', target)
    return True


def main() -> int:
    try:
        return 0 if download() else 1
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f'Stockfish-Installation fehlgeschlagen: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

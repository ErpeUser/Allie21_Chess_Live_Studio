#!/usr/bin/env python3
"""Download and verify the official Stockfish 19 Windows release."""
from __future__ import annotations

import hashlib
import io
import os
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

URL = 'https://github.com/official-stockfish/Stockfish/releases/download/sf_19/stockfish-windows-x86-64-universal.zip'
EXPECTED_SHA256 = '3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7'
DEST = Path(__file__).resolve().parent / 'engines'


def download() -> bool:
    if os.name != 'nt':
        print('Windows x64 executable only. On other systems install stockfish with your package manager.')
        return False
    DEST.mkdir(exist_ok=True, parents=True)
    target = DEST / 'stockfish.exe'
    # Never trust an existing executable based only on size. Re-download the
    # signed-off archive so the archive digest and extracted path are checked
    # every time the launcher asks for a missing/repairable engine.
    print('Downloading official Stockfish 19 (around 81 MB)...')
    with urlopen(Request(URL, headers={'User-Agent': 'Allie21ChessLabEasy/7.0'}), timeout=120) as response:
        data = response.read(125_000_000)
    if len(data) >= 125_000_000:
        raise RuntimeError('Download unexpectedly large')
    if hashlib.sha256(data).hexdigest().lower() != EXPECTED_SHA256:
        raise RuntimeError('Stockfish archive failed official SHA256 verification')
    z = zipfile.ZipFile(io.BytesIO(data))
    exe_files = [f for f in z.infolist() if f.filename.lower().endswith('.exe')
                 and 'stockfish' in f.filename.lower() and not f.is_dir()]
    if not exe_files:
        raise RuntimeError('No Stockfish executable found in official archive')
    chosen = max(exe_files, key=lambda x: x.file_size)
    if chosen.file_size > 175_000_000:
        raise RuntimeError('Executable unexpectedly large')
    temporary = target.with_suffix('.download')
    with z.open(chosen) as source, temporary.open('wb') as output:
        while chunk := source.read(1024 * 1024):
            output.write(chunk)
    temporary.replace(target)
    print('Installed:', target, f'({chosen.file_size:,} bytes)')
    return True


if __name__ == '__main__':
    download()

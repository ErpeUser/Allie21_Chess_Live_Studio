#!/usr/bin/env python3
"""Optional Stockfish 19 Windows universal release downloader (official upstream)."""
from __future__ import annotations

import hashlib
import io
import os
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

URL = 'https://github.com/official-stockfish/Stockfish/releases/download/sf_19/stockfish-windows-x86-64-universal.zip'
# GitHub official release asset digest, verified against the upstream release API.
EXPECTED_SHA256 = '3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7'
DEST = Path(__file__).resolve().parent / 'engines'

def download():
    if os.name != 'nt':
        print('Windows x64 executable only. On other systems install stockfish with your package manager.')
        return False
    DEST.mkdir(exist_ok=True, parents=True)
    target = DEST / 'stockfish.exe'
    if target.exists() and target.stat().st_size > 30_000_000:
        print('Stockfish ist bereits installiert:', target)
        return True
    print('Downloading official Stockfish 19 (around 81 MB)...')
    with urlopen(Request(URL, headers={'User-Agent': 'Allie21ChessLabEasy/7.0'}), timeout=120) as response:
        data = response.read(125_000_000)
    if len(data) >= 125_000_000:
        raise RuntimeError('Download unexpectedly large')
    if hashlib.sha256(data).hexdigest().lower() != EXPECTED_SHA256:
        raise RuntimeError('Stockfish archive failed official SHA256 verification')
    z = zipfile.ZipFile(io.BytesIO(data))
    exe_files = [f for f in z.infolist() if f.filename.lower().endswith('.exe') and
                 'stockfish' in f.filename.lower() and not f.is_dir()]
    if not exe_files:
        raise RuntimeError('No Stockfish executable found in official archive')
    # Only extract the signed-off engine executable, not arbitrary paths or scripts.
    chosen = max(exe_files, key=lambda x: x.file_size)
    if chosen.file_size > 175_000_000:
        raise RuntimeError('Executable unexpectedly large')
    with z.open(chosen) as source, target.with_suffix('.download').open('wb') as output:
        while chunk := source.read(1024 * 1024):
            output.write(chunk)
    target.with_suffix('.download').replace(target)
    # NNUE weights are embedded in official universal binaries; none are needed separately.
    print('Installed:', DEST / 'stockfish.exe', f'({chosen.file_size:,} bytes)')
    return True

if __name__ == '__main__':
    download()

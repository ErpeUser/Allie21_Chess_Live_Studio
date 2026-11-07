#!/usr/bin/env python3
"""Download the CC0 Lichess opening data. Optional, one-time setup."""
from pathlib import Path
from urllib.request import urlopen

ROOT = 'https://raw.githubusercontent.com/lichess-org/chess-openings/master'
dest = Path(__file__).resolve().parent / 'openings'
dest.mkdir(parents=True, exist_ok=True)
for letter in 'abcde':
    url = f'{ROOT}/{letter}.tsv'
    target = dest / f'{letter}.tsv'
    if target.is_file() and target.stat().st_size > 500:
        print('Bereits vorhanden:', target.name)
        continue
    print('Lade', url)
    with urlopen(url, timeout=45) as resp:
        contents = resp.read()
    if not contents.splitlines()[0].split(b'\t')[:3] == [b'eco', b'name', b'pgn'] or len(contents) < 500:
        raise ValueError('Unerwartetes TSV-Format, Download abgebrochen')
    target.write_bytes(contents)
    print('  OK:', len(contents), 'Bytes')
print('Fertig. Quelle: github.com/lichess-org/chess-openings (CC0).')

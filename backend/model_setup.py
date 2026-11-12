"""Explicit preparation of pinned model data; never imports or executes model code."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from config import MODEL_ID, MODEL_REVISION

MODEL_FILES = ['config.json', 'model.safetensors']


def prepare_model(*, download: bool = False) -> Path:
    """Check the cache by default; only --download permits network transfers.

    These are the exact data files requested by the vendored api.resolve().
    The loader continues to use reviewed local classes with remote code off.
    File presence is not a model-inference or full weight-integrity test.
    """
    from huggingface_hub import snapshot_download

    location = snapshot_download(
        repo_id=MODEL_ID, revision=MODEL_REVISION,
        allow_patterns=MODEL_FILES, local_files_only=not download,
    )
    if not isinstance(location, str):
        raise TypeError('Model cache did not return a snapshot directory')
    folder = Path(location)
    for name in MODEL_FILES:
        path = folder / name
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f'Model data missing or empty: {name}')
    config = folder / 'config.json'
    if config.stat().st_size > 1024 * 1024:
        raise RuntimeError('Model config is unexpectedly large')
    try:
        settings = json.loads(config.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as exc:
        raise RuntimeError('Model config is unreadable') from exc
    if not isinstance(settings, dict) or settings.get('model_type') != 'allie':
        raise RuntimeError('Model config is not the expected Allie configuration')
    return folder


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true',
                        help='Download missing pinned weights (large transfer); default only checks offline.')
    args = parser.parse_args(argv)
    if args.download:
        print('Allie-Modell wird vorbereitet. Grosse Gewichte werden bei Bedarf heruntergeladen.', flush=True)
    try:
        prepare_model(download=args.download)
    except Exception as exc:  # noqa: BLE001 - CLI must report hub/network errors without tokens or URLs
        print(f'Modellvorbereitung nicht erfolgreich ({type(exc).__name__}). '
              'Fuer die Ersteinrichtung mit --download erneut ausfuehren. '
              'Speicherplatz, Verbindung und die Projektumgebung pruefen.', file=sys.stderr)
        return 1
    print(f'Modelldateien vorhanden: {MODEL_ID} @ {MODEL_REVISION}.')
    print('Server neu starten. Das Laden und die Inferenz werden erst dort geprueft.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

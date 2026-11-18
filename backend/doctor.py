"""Small diagnostics with no Allie weights download."""
import platform
from importlib import import_module
from pathlib import Path

from config import APP_VERSION

print(f'Allie 2.1 Live Studio v{APP_VERSION}')
print('System:', platform.platform(), '\nPython:', platform.python_version())
for name in ('chess', 'fastapi', 'pydantic', 'uvicorn', 'chessvision', 'PIL',
             'rapidocr', 'onnxruntime', 'transformers', 'torch'):
    try:
        mod = import_module(name)
        print('[OK]  ', name, getattr(mod, '__version__', ''))
    except Exception as exc:  # noqa: BLE001 - diagnostics must report any import failure
        print('[FAIL]', name, str(exc)[:180])
try:
    from chess_extras import find_stockfish
    print('Stockfish:', find_stockfish() or 'nicht gefunden')
except Exception as exc:  # noqa: BLE001 - diagnostics must report any engine failure
    print('Stockfish-Check:', exc)
print('Eröffnungsdateien:', len(list((Path(__file__).parent / 'openings').glob('?.tsv'))), '/ 5')
print('Allie-Modell: yimingzhang/allie-2.1 (Gewichte werden separat geladen)')
print('Browseraufnahme: getDisplayMedia, nicht mss/Win32')

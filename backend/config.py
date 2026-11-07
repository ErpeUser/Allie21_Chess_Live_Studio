"""Small, validated configuration. Official Allie 2.1 is never silently replaced."""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'config.json'
MODEL_ID = 'yimingzhang/allie-2.1'
DEFAULTS = {
    'white_elo': 1950, 'black_elo': 1950, 'time_control': '600+0',
    'auto_tune_by_time_control': True,
    'stockfish_seconds': 0.35, 'stockfish_threads': 2,
    'stockfish_hash_mb': 128, 'stockfish_path': '',
    'recognition_interval_ms': 750, 'recognition_max_width': 1280,
    'stability_frames': 2, 'ocr_history': True,
    'preview_opponent_replies': True, 'progressive_engine': True,
    'model_id': MODEL_ID, 'auto_download_stockfish': True,
    'auto_download_openings': True, 'prefetch_allie_weights': False,
}


def load_config() -> dict:
    try:
        raw = json.loads(PATH.read_text(encoding='utf-8-sig'))
        if not isinstance(raw, dict):
            raise ValueError('Expected JSON object')
    except FileNotFoundError:
        raw = {}
    except (OSError, ValueError) as exc:
        print(f'WARNING: config.json is invalid ({exc}); using defaults')
        raw = {}
    config = dict(DEFAULTS)
    for k, default in DEFAULTS.items():
        if k not in raw or k == 'model_id':
            continue
        value = raw[k]
        if type(default) is bool and type(value) is bool:
            config[k] = value
        elif type(default) is int and type(value) is int:
            limits = {
                'white_elo': (600, 2800), 'black_elo': (600, 2800),
                'stockfish_threads': (1, 32), 'stockfish_hash_mb': (16, 4096),
                'recognition_interval_ms': (400, 12000),
                'recognition_max_width': (480, 1920), 'stability_frames': (1, 5),
            }
            lo, hi = limits.get(k, (0, 100000))
            if lo <= value <= hi:
                config[k] = value
        elif type(default) is float and type(value) in (float, int):
            if 0.15 <= value <= 12:
                config[k] = float(value)
        elif type(default) is str and isinstance(value, str):
            if k == 'time_control':
                if re.fullmatch(r'\d{1,5}\+\d{1,4}', value):
                    base, inc = map(int, value.split('+'))
                    if 1 <= base <= 86400 and 0 <= inc <= 3600:
                        config[k] = value
            elif len(value) < 1024:
                config[k] = value
    return config


CONFIG = load_config()

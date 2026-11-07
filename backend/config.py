"""Validated configuration and the single time-control definition."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config.json"
MODEL_ID = "yimingzhang/allie-2.1"
MODEL_REVISION = "d2545701ff5af46a51ac947911844f779b355a08"
TIME_CONTROL_RE = re.compile(r"\d{1,5}\+\d{1,4}")


def parse_time_control(value: str) -> tuple[int, int]:
    value = str(value).strip()
    if not TIME_CONTROL_RE.fullmatch(value):
        raise ValueError("Zeitkontrolle muss wie 300+0 aussehen (Sekunden+Inkrement)")
    base, increment = map(int, value.split("+"))
    if not 1 <= base <= 86_400 or not 0 <= increment <= 3_600:
        raise ValueError("Ungültige Zeitkontrolle")
    return base, increment


def time_profile(value: str) -> tuple[str, float]:
    """Class and one Stockfish budget, using base + 40 increments everywhere."""
    base, increment = parse_time_control(value)
    effective = base + 40 * increment
    if effective < 180:
        return "Bullet", 0.25
    if effective < 600:
        return "Blitz", 0.65
    if effective < 1_800:
        return "Rapid", 1.1
    return "Classical", 2.0


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    white_elo: int = Field(1950, ge=600, le=2800)
    black_elo: int = Field(1950, ge=600, le=2800)
    player_side: Literal["white", "black"] = "white"
    time_control: str = "300+0"
    stockfish_threads: int = Field(2, ge=1, le=32)
    stockfish_hash_mb: int = Field(128, ge=16, le=4096)
    stockfish_path: str = Field("", max_length=1024)
    recognition_interval_ms: int = Field(750, ge=400, le=12_000)
    recognition_max_width: int = Field(1280, ge=480, le=1920)
    stability_frames: int = Field(2, ge=1, le=5)
    ocr_history: bool = True
    preview_opponent_replies: bool = True
    model_id: Literal[MODEL_ID] = MODEL_ID
    model_revision: Literal[MODEL_REVISION] = MODEL_REVISION
    auto_download_stockfish: bool = True
    prefetch_allie_weights: bool = False

    @field_validator("time_control")
    @classmethod
    def valid_time_control(cls, value: str) -> str:
        parse_time_control(value)
        return value


def load_config() -> dict:
    try:
        raw = json.loads(PATH.read_text(encoding="utf-8-sig"))
        return AppConfig.model_validate(raw).model_dump()
    except FileNotFoundError:
        return AppConfig().model_dump()
    except (OSError, ValueError) as exc:
        print(f"WARNING: config.json ist ungültig ({exc}); verwende Standardwerte")
        return AppConfig().model_dump()


CONFIG = load_config()

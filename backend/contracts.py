"""Strict wire models shared by the local overlay clients."""
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Rect(ContractModel):
    left: float
    top: float
    width: float = Field(gt=0, le=100_000)
    height: float = Field(gt=0, le=100_000)

    @field_validator('left', 'top', 'width', 'height')
    @classmethod
    def finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError('Koordinaten müssen endlich sein')
        return value


class Viewport(ContractModel):
    width: float = Field(gt=0, le=100_000)
    height: float = Field(gt=0, le=100_000)
    offset_left: float = 0
    offset_top: float = 0
    scale: float = Field(1, gt=0, le=10)

    @field_validator('width', 'height', 'offset_left', 'offset_top', 'scale')
    @classmethod
    def finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError('Viewport-Werte müssen endlich sein')
        return value


class Geometry(ContractModel):
    viewport: Viewport | None = None
    device_pixel_ratio: float = Field(1, gt=0, le=10)
    orientation: Literal['white', 'black'] = 'white'
    board: Rect | None = None
    screen_board: Rect | None = None
    revision: int = Field(0, ge=0)

    @field_validator('device_pixel_ratio')
    @classmethod
    def finite_dpr(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError('DPI-Wert muss endlich sein')
        return value


class Arrow(ContractModel):
    uci: str = Field(pattern=r'^[a-h][1-8][a-h][1-8][qrbn]?$', max_length=5)
    color: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')
    opacity: float = Field(1, ge=0, le=1)
    width: float = Field(5, gt=0, le=64)

    @field_validator('opacity', 'width')
    @classmethod
    def finite_visual_value(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError('Visualisierungswerte müssen endlich sein')
        return value


class VisualUpdateRequest(ContractModel):
    schema_version: int = Field(1, ge=1, le=1)
    session_id: str = Field(min_length=1, max_length=180)
    generation: int = Field(0, ge=0)
    render_revision: int = Field(0, ge=0)
    analysis_key: str = Field('', max_length=256)
    fen: str = Field('', max_length=200)
    mode: Literal['private', 'normal', 'unsupported', 'exclusion_error', 'stale', 'stopped']
    source: Literal['chesscom_dom', 'lichess_dom', 'video', 'manual', 'unknown'] = 'unknown'
    geometry: Geometry | None = None
    arrows: list[Arrow] = Field(default_factory=list, max_length=8)
    messages: list[str] = Field(default_factory=list, max_length=8)
    visible: bool = False

    @field_validator('messages')
    @classmethod
    def bounded_messages(cls, value: list[str]) -> list[str]:
        if any(len(item) > 240 for item in value):
            raise ValueError('Overlay-Nachricht ist zu lang')
        return value

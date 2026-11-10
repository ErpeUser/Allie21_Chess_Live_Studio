"""Small shared readiness policy; no model imports or network access."""
from __future__ import annotations

from typing import Literal, TypedDict

AnalysisSource = Literal['allie', 'stockfish', 'both']


class Readiness(TypedDict):
    ready: bool
    phase: str
    error_id: str | None


def readiness_status(*, model_loaded: bool, stockfish_available: bool,
                     model_phase: str, source: AnalysisSource = 'both') -> Readiness:
    """Describe the requested engine combination, not just HTTP availability."""
    if source not in {'allie', 'stockfish', 'both'}:
        raise ValueError('Unknown analysis source')
    if source in {'allie', 'both'} and not model_loaded:
        phase = {
            'failed': 'model_failed',
            'not_started': 'model_not_started',
            'loading': 'model_loading',
        }.get(model_phase, 'model_unavailable')
        return {'ready': False, 'phase': phase, 'error_id': 'model_not_loaded'}
    if source in {'stockfish', 'both'} and not stockfish_available:
        return {'ready': False, 'phase': 'stockfish_unavailable', 'error_id': 'stockfish_unavailable'}
    return {'ready': True, 'phase': 'ready', 'error_id': None}

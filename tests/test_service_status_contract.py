import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from service_status import readiness_status


def test_loading_phase_is_not_ready_even_when_model_object_exists():
    report = readiness_status(
        model_loaded=True,
        stockfish_available=True,
        model_phase='loading',
        source='both',
    )
    assert report == {'ready': False, 'phase': 'model_loading', 'error_id': 'model_not_loaded'}


def test_failed_phase_is_not_ready_even_when_model_object_exists():
    report = readiness_status(
        model_loaded=True,
        stockfish_available=True,
        model_phase='failed',
        source='allie',
    )
    assert report == {'ready': False, 'phase': 'model_failed', 'error_id': 'model_not_loaded'}

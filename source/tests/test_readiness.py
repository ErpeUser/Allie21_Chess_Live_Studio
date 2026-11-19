"""Readiness must describe actual capability rather than an eternal load state."""
import ast
import asyncio
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'source/app/backend'))


def route_functions():
    """Execute actual lightweight route bodies without loading the model stack."""
    source = ast.parse((ROOT / 'source/app/backend' / 'live_server.py').read_text(encoding='utf-8'))
    names = {'health', 'readyz', 'analyze', 'http_error', 'error', 'run'}
    definitions = []
    for item in source.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name in names:
            item.decorator_list = []
            definitions.append(item)
    namespace = {
        'JSONResponse': JSONResponse, 'HTTPException': HTTPException,
        'MODEL_STATE_LOCK': threading.RLock(), 'MODEL_STATE': 'failed',
        'allie': SimpleNamespace(_model=None), 'find_stockfish': lambda: 'engine',
        'MODEL_NAME': 'test', 'MODEL_REVISION': 'revision', 'APP_VERSION': 'test',
        'INSTANCE_ID': 'a' * 32, 'API_VERSION': 2, 'SCHEMA_VERSION': 1,
        'PRIVATE_OVERLAY': SimpleNamespace(status=lambda: {'available': False}),
        'ANALYZE_GATE': threading.Semaphore(1),
        'analyse_position': Mock(return_value={'fen': 'position'}),
    }
    try:
        from service_status import readiness_status
        namespace['readiness_status'] = readiness_status
    except ImportError:
        pass
    code = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *definitions], type_ignores=[])
    exec(compile(ast.fix_missing_locations(code), 'live_server_routes', 'exec'), namespace)  # noqa: S102
    return namespace


def test_failed_model_is_not_reported_as_loading():
    routes = route_functions()
    report = routes['health']()
    assert report['phase'] == 'model_failed'
    assert report['ready'] is False
    result = routes['readyz']()
    assert result.status_code == 503
    assert json.loads(result.body)['phase'] == 'model_failed'


def test_readiness_can_report_stockfish_only_while_allie_failed():
    routes = route_functions()
    assert routes['readyz'](source='stockfish')['ready'] is True


def test_not_started_is_distinct_from_loading():
    routes = route_functions()
    routes['MODEL_STATE'] = 'not_started'
    assert routes['health']()['phase'] == 'model_not_started'
    routes['MODEL_STATE'] = 'loading'
    assert routes['health']()['phase'] == 'model_loading'


def test_allie_only_does_not_require_stockfish():
    routes = route_functions()
    routes['allie']._model = object()
    routes['MODEL_STATE'] = 'ready'
    routes['find_stockfish'] = lambda: None
    assert routes['readyz'](source='allie')['ready'] is True
    assert routes['health']()['phase'] == 'stockfish_unavailable'


def test_fen_analysis_is_not_blocked_by_allie_loading():
    routes = route_functions()
    routes['MODEL_STATE'] = 'loading'
    request = SimpleNamespace(analysis_source='both', fen='some FEN', pgn='', model_dump=lambda: {'fen': 'some FEN'})
    assert routes['analyze'](request) == {'fen': 'position'}
    routes['analyse_position'].assert_called_once_with({'fen': 'some FEN'})


def test_conflicting_fen_and_pgn_rejected_before_model_loading_gate():
    routes = route_functions()
    routes['MODEL_STATE'] = 'loading'
    request = SimpleNamespace(analysis_source='both', fen='some FEN', pgn='1. e4')
    with pytest.raises(HTTPException) as failure:
        routes['analyze'](request)
    assert failure.value.status_code == 400


def test_http_exception_keeps_retry_after():
    routes = route_functions()
    response = asyncio.run(routes['http_error'](None, HTTPException(429, 'busy', headers={'Retry-After': '2'})))
    assert response.headers['retry-after'] == '2'


def test_busy_analysis_advertises_bounded_retry():
    routes = route_functions()
    request = SimpleNamespace(analysis_source='stockfish', fen='', pgn='*')
    routes['ANALYZE_GATE'].acquire()
    try:
        with pytest.raises(HTTPException) as failure:
            routes['analyze'](request)
        assert failure.value.status_code == 429
        assert failure.value.headers['Retry-After'] == '2'
    finally:
        routes['ANALYZE_GATE'].release()

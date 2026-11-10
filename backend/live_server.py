#!/usr/bin/env python3
"""FastAPI boundary for the local-only studio."""
from __future__ import annotations

import html
import json
import os
import threading
import time
import uuid
import webbrowser
from collections.abc import Mapping
from pathlib import Path
from typing import Literal
from urllib.error import URLError
from urllib.request import Request as URLRequest
from urllib.request import urlopen

import allie_local_server as allie
import uvicorn
from allie_local_server import HOST, MODEL_NAME, PORT, analyse_position
from browser_session import BrowserTrackerPool
from chess_extras import find_stockfish
from chess_tcn import tcn_to_pgn
from config import APP_VERSION, CONFIG, MODEL_REVISION, parse_time_control
from contracts import VisualUpdateRequest
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from http_boundary import EXTENSION_ORIGINS, LocalBoundaryMiddleware
from live_session import MAX_JPEG, LiveSession
from native_overlay import PrivateOverlayController
from overlay_lease import OverlayLeaseConflict, OverlayLeaseManager
from pydantic import BaseModel, ConfigDict, Field, field_validator
from security import (
    API_VERSION,
    CAPABILITY_TOKEN,
    INSTANCE_ID,
    SCHEMA_VERSION,
    RequestRateLimiter,
    capability_payload,
    get_pairing_code,
    pairing_attempt_allowed,
    regenerate_pairing_code,
    verify_pairing_code,
)
from service_status import readiness_status
from starlette.concurrency import run_in_threadpool

ROOT = Path(__file__).resolve().parents[1]
MAX_JSON = 64 * 1024
SESSION = LiveSession()
BROWSER_TRACKERS = BrowserTrackerPool()
PRIVATE_OVERLAY = PrivateOverlayController()
OVERLAY_LEASES = OverlayLeaseManager()
REQUEST_LIMITER = RequestRateLimiter()
ANALYZE_GATE = threading.Semaphore(1)
FRAME_GATE = threading.Semaphore(1)
MODEL_STATE_LOCK = threading.RLock()
MODEL_STATE = 'not_started'
_CHESSCOM_HISTORY_CACHE: dict[str, tuple[float, str]] = {}
_CHESSCOM_HISTORY_LOCK = threading.RLock()
app = FastAPI(title="Allie21 Live Studio", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(LocalBoundaryMiddleware, max_json=MAX_JSON, max_frame=MAX_JPEG)


def _preload_model() -> None:
    global MODEL_STATE
    with MODEL_STATE_LOCK:
        MODEL_STATE = 'loading'
    try:
        model = allie.get_model()
        allie.analyse_position({
            'pgn': '*',
            'white_elo': CONFIG['white_elo'],
            'black_elo': CONFIG['black_elo'],
            'player_side': CONFIG['player_side'],
            'time_control': CONFIG['time_control'],
            'analysis_source': 'allie',
            'preview': False,
        }, model=model)
        with MODEL_STATE_LOCK:
            MODEL_STATE = 'ready'
        print('Allie-Modell und Startstellungscache sind bereit.', flush=True)
    except Exception as exc:  # noqa: BLE001 - background warmup must not block HTTP startup
        with MODEL_STATE_LOCK:
            MODEL_STATE = 'failed'
        print('Allie-Modell konnte im Hintergrund nicht vorgewärmt werden:', repr(exc))


def start_model_preload() -> threading.Thread:
    """Load Allie and warm its opening cache while the local UI starts."""
    global MODEL_STATE
    with MODEL_STATE_LOCK:
        MODEL_STATE = 'loading'
    worker = threading.Thread(
        target=_preload_model, name='allie-model-warmup', daemon=True
    )
    worker.start()
    return worker


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StartRequest(InputModel):
    white_elo: int = Field(CONFIG['white_elo'], ge=600, le=2800)
    black_elo: int = Field(CONFIG['black_elo'], ge=600, le=2800)
    player_side: Literal['white', 'black'] = CONFIG['player_side']
    time_control: str = CONFIG['time_control']
    ocr_history: bool = CONFIG['ocr_history']
    recommendations_enabled: bool = True
    play_style: Literal['normal', 'aggressive'] = 'normal'
    opening_white: Literal['grob', 'vienna', 'danish', 'bongcloud', 'halloween', 'steinitz', 'frankenstein'] = 'grob'
    opening_black: Literal['englund', 'budapest', 'alekhine', 'stafford', 'traxler'] = 'englund'

    @field_validator('time_control')
    @classmethod
    def valid_time_control(cls, value: str) -> str:
        parse_time_control(value)
        return value


class AnalysisRequest(StartRequest):
    pgn: str = Field('', max_length=40_000)
    fen: str = Field('', max_length=200)
    analysis_source: Literal['allie', 'stockfish', 'both'] = 'both'
    review_finished: bool = False
    preview: bool = True
    recommendations_enabled: bool = True
    ocr_history: bool = False
    show_moves: bool = True
    clock_history: list[float | None] | None = Field(default=None, max_length=1014)


class HistoryRequest(InputModel):
    pgn: str = Field(min_length=1, max_length=40_000)


class RecommendationRequest(InputModel):
    enabled: bool


class BrowserPositionRequest(InputModel):
    session_id: str = Field(min_length=1, max_length=180)
    placement: str = Field(min_length=1, max_length=100)
    pgn: str = Field('', max_length=40_000)
    pgn_candidates: list[str] = Field(default_factory=list, max_length=16)
    tcn: str = Field('', max_length=40_000)
    game_id: str = Field('', pattern=r'^(?:\d{1,20})?$')


class BrowserSessionRequest(InputModel):
    session_id: str = Field(min_length=1, max_length=180)


class OverlayModeRequest(InputModel):
    session_id: str = Field(min_length=1, max_length=180)
    owner_token: str = Field(min_length=20, max_length=200)
    mode: Literal['private', 'normal']


class OverlayClaimRequest(InputModel):
    session_id: str = Field(min_length=1, max_length=180)


class OverlayReleaseRequest(InputModel):
    session_id: str = Field(min_length=1, max_length=180)
    owner_token: str = Field(min_length=20, max_length=200)


class OverlayClearRequest(InputModel):
    session_id: str | None = Field(None, min_length=1, max_length=180)
    owner_token: str | None = Field(None, min_length=20, max_length=200)
    generation: int | None = Field(None, ge=0)
    render_revision: int | None = Field(None, ge=0)
    reason: str = Field('cleared', max_length=120)


def _fetch_chesscom_tcn(game_id: str) -> str:
    """Best-effort full live history for virtualised spectator move lists."""
    if os.environ.get('ALLIE_ENABLE_CHESSCOM_CALLBACK', '0') != '1':
        return ''
    now = time.monotonic()
    with _CHESSCOM_HISTORY_LOCK:
        cached = _CHESSCOM_HISTORY_CACHE.get(game_id)
        if cached and now - cached[0] < 1.2:
            return cached[1]
    request = URLRequest(
        f'https://www.chess.com/callback/live/game/{game_id}',
        headers={'Accept': 'application/json',
                 'User-Agent': f'Mozilla/5.0 Allie21-Live-Studio/{APP_VERSION}'},
    )
    try:
        with urlopen(request, timeout=3) as response:
            raw = response.read(MAX_JSON + 1)
        if len(raw) > MAX_JSON:
            return ''
        payload = json.loads(raw)
        game = payload.get('game', payload) if isinstance(payload, dict) else {}
        value = game.get('moveList', '') if isinstance(game, dict) else ''
        if not isinstance(value, str) or len(value) > 40_000 or len(value) % 2:
            return ''
    except (OSError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return cached[1] if cached else ''
    with _CHESSCOM_HISTORY_LOCK:
        _CHESSCOM_HISTORY_CACHE[game_id] = (time.monotonic(), value)
        if len(_CHESSCOM_HISTORY_CACHE) > 32:
            oldest = min(_CHESSCOM_HISTORY_CACHE,
                         key=lambda key: _CHESSCOM_HISTORY_CACHE[key][0])
            _CHESSCOM_HISTORY_CACHE.pop(oldest, None)
    return value


def error(status: int, message: str, headers: Mapping[str, str] | None = None) -> JSONResponse:
    return JSONResponse({'error': message[:240]}, status_code=status, headers=headers)


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError):
    issue = exc.errors()[0] if exc.errors() else {'msg': 'Ungültige Anfrage'}
    where = '.'.join(str(item) for item in issue.get('loc', ()) if item != 'body')
    return error(400, f"{where}: {issue.get('msg', 'ungültig')}" if where else issue.get('msg', 'ungültig'))


@app.exception_handler(HTTPException)
async def http_error(_request: Request, exc: HTTPException):
    return error(exc.status_code, str(exc.detail), headers=exc.headers)



def run(action, unavailable='Analyse nicht verfügbar'):
    try:
        return action()
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(400, str(exc)[:240]) from exc
    except Exception as exc:
        error_id = f'err-{uuid.uuid4().hex[:12]}'
        print(f'{unavailable} ({error_id}):', repr(exc), flush=True)
        raise HTTPException(503, f'{unavailable} (Fehler-ID {error_id})') from exc


@app.get('/', response_class=HTMLResponse)
@app.get('/viewer', response_class=HTMLResponse)
def viewer():
    body = (ROOT / 'viewer' / 'index.html').read_text(encoding='utf-8')
    viewer_config = dict(CONFIG, capability_token=CAPABILITY_TOKEN,
                         instance_id=INSTANCE_ID, api_version=API_VERSION,
                         schema_version=SCHEMA_VERSION)
    return body.replace('__ALLIE_CONFIG__', json.dumps(viewer_config, ensure_ascii=False).replace('<', '\\u003c'))


@app.get('/install', response_class=HTMLResponse)
def extension_installer():
    manifest = json.loads((ROOT / 'browser' / 'manifest.json').read_text(encoding='utf-8'))
    version = html.escape(str(manifest.get('version_name', 'aktuell')))
    return f'''<!doctype html><html lang="de"><meta charset="utf-8"><title>Allie Overlay installieren</title>
<style>body{{font:16px system-ui;background:#071522;color:#edf7ff;max-width:720px;margin:50px auto;padding:24px}}.card{{background:#10283d;border:1px solid #43657e;border-radius:14px;padding:24px}}a{{display:inline-block;margin:6px 6px 6px 0;padding:11px 15px;border-radius:8px;background:#16a777;color:white;font-weight:700;text-decoration:none}}code{{background:#06101a;padding:3px 6px;border-radius:4px}}li{{margin:10px 0}}</style>
<div class="card"><h1>Allie Overlay {version}</h1><p>Verwende die fertige direkte Edge-Erweiterung im Projektordner <code>browser</code> oder <a href="/install/allie21_overlay.user.js">installiere das Userscript in Tampermonkey</a>.</p>
<ol><li>Doppelklicke im Projekt auf <code>EDGE_OVERLAY_INSTALLIEREN.bat</code>.</li><li>Schalte in <code>edge://extensions</code> den <b>Entwicklermodus</b> ein.</li><li>Klicke <b>Entpackte Erweiterung laden</b> und wähle den automatisch geöffneten Ordner <code>browser</code>.</li><li>Lade Chess.com oder Lichess einmal neu.</li></ol>
</div></html>'''


@app.get('/install/allie21_overlay.user.js', response_class=Response)
def extension_userscript():
    script = (ROOT / 'browser' / 'allie21_overlay.user.js').read_text(encoding='utf-8')
    return Response(script, media_type='text/javascript', headers={'Cache-Control': 'no-store'})


@app.get('/health')
def health():
    model_loaded = allie._model is not None
    stockfish_available = bool(find_stockfish())
    with MODEL_STATE_LOCK:
        model_phase = MODEL_STATE
    report = readiness_status(model_loaded=model_loaded,
                              stockfish_available=stockfish_available,
                              model_phase=model_phase)
    return {'alive': True, **report,
            'model': MODEL_NAME, 'model_revision': MODEL_REVISION,
            'app_version': APP_VERSION, 'model_phase': model_phase,
            'instance_id': INSTANCE_ID, 'api_version': API_VERSION,
            'schema_version': SCHEMA_VERSION,
            'model_loaded': model_loaded,
            'stockfish_available': stockfish_available,
            'overlay': PRIVATE_OVERLAY.status()}


@app.get('/readyz')
def readyz(source: Literal['allie', 'stockfish', 'both'] = 'both'):
    """Report readiness for one engine or the default combined service."""
    try:
        with MODEL_STATE_LOCK:
            model_phase = MODEL_STATE
        report = readiness_status(
            model_loaded=allie._model is not None,
            stockfish_available=bool(find_stockfish()),
            model_phase=model_phase, source=source,
        )
        if not report['ready']:
            return JSONResponse(report, status_code=503)
        return report
    except Exception:  # noqa: BLE001 - readiness must not leak internals
        error_id = f'readyz-{uuid.uuid4().hex[:12]}'
        print(f'readyz failed ({error_id})', flush=True)
        return JSONResponse(
            {'ready': False, 'phase': 'error', 'error_id': error_id},
            status_code=503,
        )


@app.get('/api/capability')
def capability(request: Request):
    if not request.headers.get('origin') or request.headers.get('x-allie-overlay') != '1':
        raise HTTPException(403, 'Capability-Handshake benötigt eine erlaubte Overlay-Herkunft')
    origin = request.headers.get('origin', '')
    local_origin = origin in {
        f'http://127.0.0.1:{PORT}', f'http://localhost:{PORT}',
        'http://127.0.0.1', 'http://localhost',
    }
    if not local_origin:
        if not pairing_attempt_allowed(origin):
            raise HTTPException(429, 'Zu viele Pairing-Versuche')
        if not verify_pairing_code(request.headers.get('x-allie-pairing', '')):
            raise HTTPException(401, 'Browser-Pairing erforderlich')
    return capability_payload()


@app.get('/api/pairing')
def pairing_status(request: Request):
    origin = request.headers.get('origin', '')
    if origin.startswith('http://127.0.0.1') or origin.startswith('http://localhost'):
        return {'pairing_code': get_pairing_code()}
    if origin in EXTENSION_ORIGINS and request.headers.get('x-allie-overlay') == '1':
        return {'pairing_code': get_pairing_code()}
    raise HTTPException(403, 'Nur der lokale Viewer darf den Pairing-Code anzeigen')


@app.post('/api/pairing/regenerate')
def pairing_regenerate(request: Request):
    origin = request.headers.get('origin', '')
    if origin.startswith('http://127.0.0.1') or origin.startswith('http://localhost'):
        return {'pairing_code': regenerate_pairing_code()}
    raise HTTPException(403, 'Nur der lokale Viewer darf den Pairing-Code ändern')


@app.get('/api/state')
def state():
    return SESSION.get_state()


@app.post('/analyze')
def analyze(request: AnalysisRequest):
    if request.fen.strip() and request.pgn.strip():
        raise HTTPException(400, 'Bitte entweder PGN oder FEN angeben, nicht beide gleichzeitig.')
    needs_model = request.analysis_source in ('allie', 'both') and not request.fen.strip()
    with MODEL_STATE_LOCK:
        model_phase = MODEL_STATE
    if needs_model and model_phase == 'loading':
        response = JSONResponse(
            {'error': 'Allie-Modell wird noch geladen', 'phase': 'model_loading'},
            status_code=503,
            headers={'Retry-After': '5'},
        )
        return response
    if needs_model and model_phase == 'failed' and allie._model is None:
        response = JSONResponse(
            {'error': 'Allie-Modell konnte nicht geladen werden', 'phase': 'model_failed'},
            status_code=503,
            headers={'Retry-After': '15'},
        )
        return response
    if not ANALYZE_GATE.acquire(blocking=False):
        raise HTTPException(429, 'Analyse bereits aktiv', headers={'Retry-After': '2'})
    try:
        return run(lambda: analyse_position(request.model_dump()))
    finally:
        ANALYZE_GATE.release()


@app.post('/api/start')
def start(request: StartRequest):
    return run(lambda: (PRIVATE_OVERLAY.clear('session-start'), SESSION.start(request.model_dump()))[1])


@app.post('/api/stop')
def stop():
    PRIVATE_OVERLAY.clear('session-stop')
    return SESSION.stop()


@app.post('/api/frame')
async def frame(request: Request):
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_JPEG:
            raise HTTPException(413, 'Videoframe zu groß (maximal 3,5 MB)')
        chunks.append(chunk)
    raw = b''.join(chunks)
    if not FRAME_GATE.acquire(blocking=False):
        raise HTTPException(429, 'Bretterkennung bereits aktiv')
    try:
        return await run_in_threadpool(
            lambda: run(lambda: SESSION.submit_frame(raw), 'Bretterkennung nicht verfügbar')
        )
    finally:
        FRAME_GATE.release()


@app.post('/api/history')
def history(request: HistoryRequest):
    return run(lambda: SESSION.import_pgn(request.pgn))


@app.post('/api/recommendations')
def recommendations(request: RecommendationRequest):
    return run(lambda: SESSION.set_recommendations(request.enabled))


@app.post('/api/browser-position')
def browser_position(request: BrowserPositionRequest):
    if not REQUEST_LIMITER.allow(f'browser:{request.session_id}', 10, 1.0):
        raise HTTPException(429, 'Zu viele Browser-Positionsupdates')
    candidates = list(request.pgn_candidates)
    tcn = request.tcn or (_fetch_chesscom_tcn(request.game_id) if request.game_id else '')
    if tcn:
        try:
            candidates.insert(0, tcn_to_pgn(tcn))
        except (ValueError, TypeError, IndexError, KeyError):
            pass
    return run(lambda: BROWSER_TRACKERS.observe(
        request.session_id, request.placement, request.pgn, candidates[:16]
    ))


@app.post('/api/browser-position/reset')
def reset_browser_position(request: BrowserSessionRequest):
    def reset() -> dict[str, bool]:
        BROWSER_TRACKERS.reset(request.session_id)
        return {'ok': True}

    return run(reset)


@app.get('/api/overlay/status')
def overlay_status():
    return PRIVATE_OVERLAY.status()


@app.post('/api/overlay/mode')
def overlay_mode(request: OverlayModeRequest):
    try:
        OVERLAY_LEASES.touch(request.session_id, request.owner_token)
    except OverlayLeaseConflict as exc:
        raise HTTPException(409, 'Privates Overlay wird bereits von einer anderen Sitzung verwendet') from exc
    return run(lambda: PRIVATE_OVERLAY.set_mode(request.mode))


@app.post('/api/overlay/claim')
def overlay_claim(request: OverlayClaimRequest):
    try:
        lease = OVERLAY_LEASES.claim(request.session_id)
    except OverlayLeaseConflict as exc:
        raise HTTPException(409, 'Privates Overlay wird bereits von einer anderen Sitzung verwendet') from exc
    return {'session_id': lease.session_id, 'owner_token': lease.owner_token,
            'expires_at': lease.expires_at}


@app.post('/api/overlay/release')
def overlay_release(request: OverlayReleaseRequest):
    if not OVERLAY_LEASES.release(request.session_id, request.owner_token):
        raise HTTPException(409, 'Privates Overlay wird bereits von einer anderen Sitzung verwendet')
    return {'released': True}


@app.post('/api/overlay/update')
def overlay_update(request: VisualUpdateRequest):
    try:
        OVERLAY_LEASES.touch(request.session_id, request.owner_token)
    except OverlayLeaseConflict as exc:
        raise HTTPException(409, 'Privates Overlay wird bereits von einer anderen Sitzung verwendet') from exc
    if not REQUEST_LIMITER.allow(f'overlay:{request.session_id}', 30, 1.0):
        raise HTTPException(429, 'Zu viele Overlay-Updates')
    try:
        return PRIVATE_OVERLAY.update(request.model_dump())
    except (KeyError, TypeError, ValueError, OverflowError):
        # Never let malformed geometry reach a visible fallback.  The native
        # controller is cleared and the request remains fail-closed.  Scope
        # that clear to the same cursor: a delayed malformed frame from a
        # retired session must not hide a newer session's overlay.
        return PRIVATE_OVERLAY.clear(
            'invalid_overlay_payload',
            session_id=request.session_id,
            generation=request.generation,
            render_revision=request.render_revision,
        )


@app.post('/api/overlay/clear')
def overlay_clear(request: OverlayClearRequest | None = None):
    data = request.model_dump() if request is not None else {}
    if data.get('session_id'):
        try:
            OVERLAY_LEASES.touch(data['session_id'], data.get('owner_token', ''))
        except OverlayLeaseConflict as exc:
            raise HTTPException(409, 'Privates Overlay wird bereits von einer anderen Sitzung verwendet') from exc
    return run(lambda: PRIVATE_OVERLAY.clear(
        data.get('reason', 'cleared'),
        session_id=data.get('session_id'),
        generation=data.get('generation'),
        render_revision=data.get('render_revision'),
    ))


def main():
    print('Allie 2.1 Live Studio v11 (nur lokal)')
    print('Viewer:', f'http://{HOST}:{PORT}/viewer')
    print('Modellrevision:', MODEL_REVISION)
    if os.environ.get('ALLIE_NO_PRELOAD') != '1':
        start_model_preload()
    if os.environ.get('ALLIE_NO_BROWSER') != '1':
        threading.Timer(1.0, lambda: webbrowser.open(f'http://{HOST}:{PORT}/viewer')).start()
    try:
        uvicorn.run(app, host=HOST, port=PORT, access_log=False, server_header=False)
    finally:
        SESSION.stop()
        OVERLAY_LEASES.force_release()
        PRIVATE_OVERLAY.close()


if __name__ == '__main__':
    main()

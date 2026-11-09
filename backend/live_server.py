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
from pathlib import Path
from typing import Literal
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request as URLRequest
from urllib.request import urlopen

import allie_local_server as allie
import uvicorn
from allie_local_server import HOST, MODEL_NAME, PORT, analyse_position
from browser_session import BrowserTrackerPool
from chess_extras import find_stockfish
from chess_tcn import tcn_to_pgn
from config import CONFIG, MODEL_REVISION, parse_time_control
from contracts import VisualUpdateRequest
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from live_session import MAX_JPEG, LiveSession
from native_overlay import PrivateOverlayController
from pydantic import BaseModel, ConfigDict, Field, field_validator
from security import (
    API_VERSION,
    CAPABILITY_TOKEN,
    INSTANCE_ID,
    SCHEMA_VERSION,
    RequestRateLimiter,
    capability_payload,
    require_capability,
)
from starlette.concurrency import run_in_threadpool

ROOT = Path(__file__).resolve().parents[1]
MAX_JSON = 64 * 1024
SESSION = LiveSession()
BROWSER_TRACKERS = BrowserTrackerPool()
PRIVATE_OVERLAY = PrivateOverlayController()
REQUEST_LIMITER = RequestRateLimiter()
ANALYZE_GATE = threading.Semaphore(1)
FRAME_GATE = threading.Semaphore(1)
_CHESSCOM_HISTORY_CACHE: dict[str, tuple[float, str]] = {}
_CHESSCOM_HISTORY_LOCK = threading.RLock()
app = FastAPI(title="Allie21 Live Studio", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https://(?:[a-z0-9-]+\.)?chess\.com$|^https://lichess\.org$",
    allow_methods=['GET', 'POST'],
    allow_headers=['Content-Type', 'Authorization', 'X-Allie-Overlay', 'X-Allie-Instance'],
    max_age=3600,
)


def _preload_model() -> None:
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
        print('Allie-Modell und Startstellungscache sind bereit.', flush=True)
    except Exception as exc:  # noqa: BLE001 - background warmup must not block HTTP startup
        print('Allie-Modell konnte im Hintergrund nicht vorgewärmt werden:', repr(exc))


def start_model_preload() -> threading.Thread:
    """Load Allie and warm its opening cache while the local UI starts."""
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
    mode: Literal['private', 'normal']


class OverlayClearRequest(InputModel):
    session_id: str | None = Field(None, min_length=1, max_length=180)
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
                 'User-Agent': 'Mozilla/5.0 Allie21-Live-Studio/11.2.16'},
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


def error(status: int, message: str) -> JSONResponse:
    return JSONResponse({'error': message[:240]}, status_code=status)


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError):
    issue = exc.errors()[0] if exc.errors() else {'msg': 'Ungültige Anfrage'}
    where = '.'.join(str(item) for item in issue.get('loc', ()) if item != 'body')
    return error(400, f"{where}: {issue.get('msg', 'ungültig')}" if where else issue.get('msg', 'ungültig'))


@app.exception_handler(HTTPException)
async def http_error(_request: Request, exc: HTTPException):
    return error(exc.status_code, str(exc.detail))


@app.middleware('http')
async def local_boundary(request: Request, call_next):
    host = request.headers.get('host', '').split(':', 1)[0].lower()
    if host not in {'127.0.0.1', 'localhost', 'testserver'}:
        return error(403, 'Host not allowed')
    origin = request.headers.get('origin', '')
    if origin:
        parsed = urlparse(origin)
        local = parsed.scheme in {'http', 'https'} and parsed.hostname in {'127.0.0.1', 'localhost'}
        website = parsed.scheme == 'https' and (
            parsed.hostname == 'lichess.org' or parsed.hostname == 'chess.com'
            or bool(parsed.hostname and parsed.hostname.endswith('.chess.com'))
        )
        extension = parsed.scheme in {'chrome-extension', 'extension'} and bool(parsed.hostname)
        preflight = (request.method == 'OPTIONS'
                     and 'x-allie-overlay' in request.headers.get('access-control-request-headers', '').lower())
        overlay = (website or extension) and (
            request.headers.get('x-allie-overlay') == '1' or preflight
        )
        if not (local or overlay):
            return error(403, 'Local host or origin invalid')
    if request.method != 'OPTIONS' and request.url.path in {
        '/analyze', '/api/start', '/api/stop', '/api/frame', '/api/history',
        '/api/recommendations', '/api/browser-position',
        '/api/browser-position/reset', '/api/overlay/mode',
        '/api/overlay/update', '/api/overlay/clear',
    }:
        try:
            require_capability(request)
        except HTTPException as exc:
            return error(exc.status_code, str(exc.detail))
    if request.method == 'POST':
        maximum = MAX_JPEG if request.url.path == '/api/frame' else MAX_JSON
        try:
            length = int(request.headers.get('content-length', '0'))
        except ValueError:
            length = 0
        if not 0 < length <= maximum:
            return error(413, 'Request too large or empty')
    response = await call_next(request)
    response.headers.update({
        'Cache-Control': 'no-store',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Referrer-Policy': 'no-referrer',
        'Content-Security-Policy': "default-src 'self' 'unsafe-inline' blob: data:; connect-src 'self'; media-src blob:; object-src 'none'; frame-ancestors 'none'",
    })
    return response


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
    return {'alive': True, 'ready': model_loaded and stockfish_available,
            'phase': 'ready' if model_loaded and stockfish_available else
            ('model_loading' if not model_loaded else 'stockfish_unavailable'),
            'model': MODEL_NAME, 'model_revision': MODEL_REVISION,
            'instance_id': INSTANCE_ID, 'api_version': API_VERSION,
            'schema_version': SCHEMA_VERSION,
            'model_loaded': model_loaded,
            'stockfish_available': stockfish_available,
            'overlay': PRIVATE_OVERLAY.status()}


@app.get('/readyz')
def readyz():
    """Report whether the local analysis service can accept work.

    Readiness failures intentionally expose only a coarse phase and an opaque
    error identifier.  Internal exception messages (which may contain paths,
    model details, or credentials) never cross the HTTP boundary.
    """
    try:
        if allie._model is None:
            return JSONResponse(
                {'ready': False, 'phase': 'model_loading',
                 'error_id': 'model_not_loaded'}, status_code=503)
        if not find_stockfish():
            return JSONResponse(
                {'ready': False, 'phase': 'stockfish_unavailable',
                 'error_id': 'stockfish_unavailable'}, status_code=503)
        return {'ready': True, 'phase': 'ready', 'error_id': None}
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
    return capability_payload()


@app.get('/api/state')
def state():
    return SESSION.get_state()


@app.post('/analyze')
def analyze(request: AnalysisRequest):
    if not ANALYZE_GATE.acquire(blocking=False):
        raise HTTPException(429, 'Analyse bereits aktiv')
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
    return run(lambda: PRIVATE_OVERLAY.set_mode(request.mode))


@app.post('/api/overlay/update')
def overlay_update(request: VisualUpdateRequest):
    if not REQUEST_LIMITER.allow(f'overlay:{request.session_id}', 30, 1.0):
        raise HTTPException(429, 'Zu viele Overlay-Updates')
    try:
        return PRIVATE_OVERLAY.update(request.model_dump())
    except (KeyError, TypeError, ValueError, OverflowError):
        # Never let malformed geometry reach a visible fallback.  The native
        # controller is cleared and the request remains fail-closed.
        return PRIVATE_OVERLAY.clear('invalid_overlay_payload')


@app.post('/api/overlay/clear')
def overlay_clear(request: OverlayClearRequest | None = None):
    data = request.model_dump() if request is not None else {}
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
        PRIVATE_OVERLAY.close()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""FastAPI boundary for the local-only studio."""
from __future__ import annotations

import html
import json
import logging
import os
import threading
import time
import uuid
import webbrowser
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast
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
from http_boundary import EXTENSION_ORIGINS, WEB_ORIGINS, LocalBoundaryMiddleware
from live_session import MAX_JPEG, LiveSession
from native_overlay import PrivateOverlayController
from overlay_lease import OverlayLeaseConflict, OverlayLeaseManager
from pgn_training import build_replay
from pydantic import BaseModel, ConfigDict, Field, field_validator
from security import (
    API_VERSION,
    CAPABILITY_TOKEN,
    INSTANCE_ID,
    SCHEMA_VERSION,
    RequestRateLimiter,
    capability_payload,
    get_pairing_code,
    regenerate_pairing_code,
    verify_pairing_attempt,
)
from service_status import readiness_status
from starlette.concurrency import run_in_threadpool

ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)
MAX_JSON = 64 * 1024
SESSION = LiveSession()
BROWSER_TRACKERS = BrowserTrackerPool()
PRIVATE_OVERLAY = PrivateOverlayController()


def _expire_overlay(_lease) -> None:
    PRIVATE_OVERLAY.clear('lease_expired')


OVERLAY_LEASES = OverlayLeaseManager(on_expire=_expire_overlay)
REQUEST_LIMITER = RequestRateLimiter()
ANALYZE_GATE = threading.Semaphore(1)
FRAME_GATE = threading.Semaphore(1)
MODEL_STATE_LOCK = threading.RLock()
MODEL_STATE = 'not_started'
_MODEL_PRELOAD_THREAD: threading.Thread | None = None
_CHESSCOM_HISTORY_CACHE: dict[str, tuple[float, str]] = {}
_CHESSCOM_HISTORY_LOCK = threading.RLock()
_OVERLAY_SETTINGS_LOCK = threading.RLock()
_OVERLAY_SETTINGS_PATH = Path(
    os.environ.get('ALLIE_OVERLAY_SETTINGS_PATH', '')
    or (Path(os.environ['LOCALAPPDATA']) / 'Allie21' / 'overlay-settings.json'
        if os.environ.get('LOCALAPPDATA') else Path.home() / '.allie21' / 'overlay-settings.json')
)


def _load_overlay_settings() -> dict[str, object]:
    """Load desired and last natively confirmed modes from local state."""
    try:
        value = json.loads(_OVERLAY_SETTINGS_PATH.read_text(encoding='utf-8'))
        if (isinstance(value, dict) and value.get('mode') in {'private', 'share', 'normal'}
                and isinstance(value.get('version'), int) and value['version'] >= 1):
            confirmed = value.get('confirmed_mode', value['mode'])
            if confirmed not in {'private', 'share', 'normal'}:
                confirmed = 'private'
            return {
                'mode': value['mode'],
                'confirmed_mode': confirmed,
                'version': int(value['version']),
                'updated_at': float(value.get('updated_at', time.time())),
            }
    except (OSError, ValueError, TypeError, OverflowError):
        pass
    return {'mode': 'private', 'confirmed_mode': 'private', 'version': 1, 'updated_at': time.time()}


OVERLAY_SETTINGS = _load_overlay_settings()
app = FastAPI(title="Allie21 Live Studio", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(LocalBoundaryMiddleware, max_json=MAX_JSON, max_frame=MAX_JPEG)


def _persist_overlay_settings(value: Mapping[str, object]) -> None:
    try:
        _OVERLAY_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = _OVERLAY_SETTINGS_PATH.with_suffix('.tmp')
        temporary.write_text(json.dumps(dict(value), ensure_ascii=False), encoding='utf-8')
        temporary.replace(_OVERLAY_SETTINGS_PATH)
    except OSError:
        # Persistence is best-effort; the in-process version remains authoritative.
        pass


def restore_overlay_mode() -> dict[str, object]:
    """Reapply the last natively confirmed mode after a process restart."""
    mode = str(OVERLAY_SETTINGS.get('confirmed_mode', 'private'))
    try:
        return PRIVATE_OVERLAY.set_mode(mode)
    except Exception as exc:  # noqa: BLE001 - caller exposes a safe diagnostic
        return {
            'mode': mode,
            'state': 'error',
            'reason': f'overlay_restore_failed: {type(exc).__name__}',
            'available': False,
            'visible': False,
            'capture_excluded': False,
            'status_text': 'Overlay nicht gekoppelt',
        }


@app.on_event('startup')
async def _restore_overlay_on_startup() -> None:
    restore_overlay_mode()


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
    """Load Allie once and warm its opening cache while the UI starts.

    Startup hooks can be invoked more than once by a tray/reloader host.
    Reusing the existing worker avoids duplicate multi-gigabyte loads and keeps
    the health phase monotonic.
    """
    global MODEL_STATE, _MODEL_PRELOAD_THREAD
    with MODEL_STATE_LOCK:
        if _MODEL_PRELOAD_THREAD is not None:
            return _MODEL_PRELOAD_THREAD
        MODEL_STATE = 'loading'
        worker = threading.Thread(
            target=_preload_model, name='allie-model-warmup', daemon=True
        )
        _MODEL_PRELOAD_THREAD = worker
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
    mode: Literal['private', 'share', 'normal']


class OverlaySettingsRequest(InputModel):
    """Versioned shared overlay setting used by viewer and MV3 clients."""

    mode: Literal['private', 'share', 'normal']
    version: int | None = Field(None, ge=0)
    updated_at: float | str | None = None
    source: str = Field('unknown', max_length=32)

    @field_validator('updated_at', mode='before')
    @classmethod
    def normalize_timestamp(cls, value):
        if value is None:
            return None
        if isinstance(value, bool):
            raise TypeError('updated_at muss ein Zeitstempel sein')
        if isinstance(value, (int, float)):
            if value < 0 or not float(value) == float(value):
                raise ValueError('updated_at muss ein Zeitstempel sein')
            return float(value)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                return parsed.timestamp()
            except ValueError as exc:
                raise ValueError('updated_at muss ein ISO-Zeitstempel sein') from exc
        raise ValueError('updated_at muss ein Zeitstempel sein')


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
    origin = request.headers.get('origin', '')
    extension_worker = not origin and request.headers.get('x-allie-extension') == '1'
    if (not origin and not extension_worker) or request.headers.get('x-allie-overlay') != '1':
        raise HTTPException(403, 'Capability-Handshake benötigt eine erlaubte Overlay-Herkunft')
    local_origin = origin in {
        f'http://127.0.0.1:{PORT}', f'http://localhost:{PORT}',
        'http://127.0.0.1', 'http://localhost',
    }
    if (not local_origin and not extension_worker
            and not verify_pairing_attempt(origin, request.headers.get('x-allie-pairing', ''))):
        raise HTTPException(401, 'Browser-Pairing erforderlich')
    return capability_payload()


@app.get('/api/pairing')
def pairing_status(request: Request):
    origin = request.headers.get('origin', '')
    if origin.startswith(('http://127.0.0.1', 'http://localhost')):
        return {'pairing_code': get_pairing_code()}
    extension_worker = not origin and request.headers.get('x-allie-extension') == '1'
    if (origin in EXTENSION_ORIGINS or extension_worker) and request.headers.get('x-allie-overlay') == '1':
        return {'pairing_code': get_pairing_code()}
    raise HTTPException(403, 'Nur der lokale Viewer darf den Pairing-Code anzeigen')


@app.post('/api/pairing/regenerate')
def pairing_regenerate(request: Request):
    origin = request.headers.get('origin', '')
    if origin.startswith(('http://127.0.0.1', 'http://localhost')):
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
    if needs_model and model_phase == 'failed':
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
    # A new capture session invalidates every delayed frame and lease first.
    OVERLAY_LEASES.force_release()
    PRIVATE_OVERLAY.reset('session-start')
    return run(lambda: SESSION.start(request.model_dump()))


@app.post('/api/stop')
def stop():
    OVERLAY_LEASES.force_release()
    PRIVATE_OVERLAY.reset('session-stop')
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


@app.post('/api/pgn/replay')
def pgn_replay(request: HistoryRequest):
    return run(lambda: build_replay(request.pgn))


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
    payload = PRIVATE_OVERLAY.status()
    payload['lease'] = OVERLAY_LEASES.status()
    return payload


def _overlay_settings_payload(*, accepted: bool = True, conflict: bool = False) -> dict[str, object]:
    with _OVERLAY_SETTINGS_LOCK:
        value = dict(OVERLAY_SETTINGS)
    value['status'] = PRIVATE_OVERLAY.status()
    value['accepted'] = accepted
    value['conflict'] = conflict
    return value


def _overlay_mode_confirmed(status: Mapping[str, object], mode: str) -> bool:
    """Persist only a native mode whose capture policy was verified."""
    if mode == 'private':
        return status.get('private_verified') is True
    if mode == 'share':
        return status.get('share_visible') is True
    return True


def _require_overlay_settings_access(request: Request) -> None:
    """Authorize the non-secret mode store for localhost and MV3 clients.

    The extension worker intentionally reads this endpoint before it has a
    capability token; its pairing header and explicit extension marker are the
    bridge. Chess-site origins still need a valid pairing code.
    """
    origin = request.headers.get('origin', '')
    extension_worker = not origin and request.headers.get('x-allie-extension') == '1'
    local_origin = origin.startswith(('http://127.0.0.1', 'http://localhost'))
    extension_origin = origin in EXTENSION_ORIGINS and request.headers.get('x-allie-overlay') == '1'
    web_origin = origin in WEB_ORIGINS and request.headers.get('x-allie-overlay') == '1'
    if local_origin or extension_worker:
        return
    if ((extension_origin or web_origin)
            and verify_pairing_attempt(origin, request.headers.get('x-allie-pairing', ''))):
        return
    raise HTTPException(403, 'Overlay-Einstellung benötigt eine erlaubte lokale Sitzung')


@app.get('/api/overlay/settings')
def overlay_settings(request: Request):
    """Return the versioned mode shared by the local viewer and extension."""
    _require_overlay_settings_access(request)
    return _overlay_settings_payload()


@app.api_route('/api/overlay/settings', methods=['POST', 'PUT'])
def overlay_settings_update(payload: OverlaySettingsRequest, request: Request):
    _require_overlay_settings_access(request)
    # Last-write-wins is unsafe when a sleeping MV3 worker wakes with stale
    # state. A supplied version must be at least the current monotonic value;
    # stale writes are reported without changing the mode.
    with _OVERLAY_SETTINGS_LOCK:
        current_version = int(cast(int, OVERLAY_SETTINGS.get('version', 1)))
        current_mode = str(OVERLAY_SETTINGS.get('mode', 'private'))
        requested_timestamp = float(cast(float | str | None, payload.updated_at) or 0)
        current_timestamp = float(cast(float, OVERLAY_SETTINGS.get('updated_at', 0)))
        if (payload.version is not None
                and (payload.version < current_version
                     or (payload.version == current_version and payload.mode != current_mode
                         and requested_timestamp <= current_timestamp))):
            return _overlay_settings_payload(accepted=False, conflict=True)
        if payload.version == current_version and payload.mode == current_mode:
            # Keep the normal-mode transition idempotent.  A sleeping client
            # can repeat the same request after a worker restart; the native
            # window and lease must still be released on that retry.
            unchanged = _overlay_settings_payload()
        else:
            unchanged = None
        if unchanged is not None and payload.mode != 'normal':
            return unchanged
        if unchanged is None:
            next_version = max(current_version + 1, int(payload.version or 0))
            next_updated = max(
                time.time(), requested_timestamp,
                float(cast(float, OVERLAY_SETTINGS.get('updated_at', 0))) + 1e-6,
            )
            OVERLAY_SETTINGS.update({
                'mode': payload.mode,
                'version': next_version,
                'updated_at': next_updated,
            })
            _persist_overlay_settings(OVERLAY_SETTINGS)
    # Turning the shared setting off must hide an existing native frame even
    # when no browser tab currently owns the lease.  Enabling private/share is
    # intentionally still lease-gated through /api/overlay/mode.
    if payload.mode == 'normal':
        try:
            PRIVATE_OVERLAY.set_mode('normal')
        except Exception:
            LOGGER.debug('Normal overlay transition failed during settings update', exc_info=True)
        OVERLAY_LEASES.force_release()
        with _OVERLAY_SETTINGS_LOCK:
            OVERLAY_SETTINGS['confirmed_mode'] = 'normal'
            _persist_overlay_settings(OVERLAY_SETTINGS)
    result = _overlay_settings_payload()
    result['source'] = payload.source
    return result


@app.post('/api/overlay/mode')
def overlay_mode(request: OverlayModeRequest):
    try:
        OVERLAY_LEASES.touch(request.session_id, request.owner_token)
    except OverlayLeaseConflict as exc:
        raise HTTPException(409, 'Privates Overlay wird bereits von einer anderen Sitzung verwendet') from exc
    result = run(lambda: PRIVATE_OVERLAY.set_mode(request.mode))
    confirmed = request.mode not in {'private', 'share'} or _overlay_mode_confirmed(result, request.mode)
    if request.mode in {'private', 'share'} and not confirmed:
        # A failed native transition must not leave a lease that looks like a
        # successful claim to every other client.
        OVERLAY_LEASES.release(request.session_id, request.owner_token)
        result = dict(result)
        result['lease_active'] = False
    if request.mode in {'private', 'share', 'normal'} and confirmed:
        if request.mode == 'normal':
            OVERLAY_LEASES.force_release()
        with _OVERLAY_SETTINGS_LOCK:
            current_version = int(cast(int, OVERLAY_SETTINGS.get('version', 1)))
            current_mode = str(OVERLAY_SETTINGS.get('mode', 'private'))
            current_confirmed = str(OVERLAY_SETTINGS.get('confirmed_mode', 'private'))
            if current_mode != request.mode or current_confirmed != request.mode:
                OVERLAY_SETTINGS.update({
                    'mode': request.mode,
                    'confirmed_mode': request.mode,
                    'version': current_version + 1,
                    'updated_at': max(time.time(), float(cast(float, OVERLAY_SETTINGS.get('updated_at', 0))) + 1e-6),
                })
                _persist_overlay_settings(OVERLAY_SETTINGS)
    return result


@app.post('/api/overlay/claim')
def overlay_claim(request: OverlayClaimRequest):
    try:
        lease = OVERLAY_LEASES.claim(request.session_id)
    except OverlayLeaseConflict as exc:
        raise HTTPException(409, 'Privates Overlay wird bereits von einer anderen Sitzung verwendet') from exc
    # A fresh lease is a new client incarnation even when the browser reused
    # its logical session id after the global start/stop reset.
    PRIVATE_OVERLAY.resume_session(request.session_id)
    return {'session_id': lease.session_id, 'owner_token': lease.owner_token,
            'expires_at': lease.expires_at}


@app.post('/api/overlay/release')
def overlay_release(request: OverlayReleaseRequest):
    if not OVERLAY_LEASES.release(request.session_id, request.owner_token):
        raise HTTPException(409, 'Privates Overlay wird bereits von einer anderen Sitzung verwendet')
    return {'released': True}


@app.post('/api/overlay/renew')
def overlay_renew(request: OverlayReleaseRequest):
    try:
        lease = OVERLAY_LEASES.renew(request.session_id, request.owner_token)
    except OverlayLeaseConflict as exc:
        raise HTTPException(409, 'Privates Overlay ist nicht mehr gekoppelt') from exc
    return {
        'session_id': lease.session_id,
        'owner_token': lease.owner_token,
        'expires_at': lease.expires_at,
    }


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
    # Restore only the last confirmed explicit mode. A failed native start is
    # reported through status and never falls back to a browser HUD in private
    # mode.
    restored = restore_overlay_mode()
    if restored.get('state') == 'error':
        print('Overlay-Modus konnte nicht wiederhergestellt werden:', restored.get('reason'), flush=True)
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

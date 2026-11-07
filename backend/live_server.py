#!/usr/bin/env python3
"""FastAPI boundary for the local-only studio."""
from __future__ import annotations

import html
import json
import os
import re
import threading
import webbrowser
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

import allie_local_server as allie
from allie_local_server import HOST, PORT, MODEL_NAME, analyse_position
from browser_session import BrowserTrackerPool
from chess_extras import find_stockfish
from config import CONFIG, parse_time_control
from live_session import LiveSession, MAX_JPEG

ROOT = Path(__file__).resolve().parents[1]
MAX_JSON = 64 * 1024
SESSION = LiveSession()
BROWSER_TRACKERS = BrowserTrackerPool()
app = FastAPI(title="Allie21 Live Studio", docs_url=None, redoc_url=None, openapi_url=None)


def _preload_model() -> None:
    try:
        allie.get_model()
    except Exception as exc:
        print('Allie-Modell konnte im Hintergrund nicht vorgeladen werden:', repr(exc))


def start_model_preload() -> threading.Thread:
    """Start loading Allie while the local UI is already becoming available."""
    worker = threading.Thread(
        target=_preload_model, name='allie-model-loader', daemon=True
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


class HistoryRequest(InputModel):
    pgn: str = Field(min_length=1, max_length=40_000)


class RecommendationRequest(InputModel):
    enabled: bool


class BrowserPositionRequest(InputModel):
    session_id: str = Field(min_length=1, max_length=180)
    placement: str = Field(min_length=1, max_length=100)
    pgn: str = Field('', max_length=40_000)


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
        overlay = (parsed.scheme in {'http', 'https'} and parsed.hostname
                   and request.headers.get('x-allie-overlay') == '1')
        if not (local or overlay):
            return error(403, 'Local host or origin invalid')
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
        print(unavailable + ':', repr(exc))
        raise HTTPException(503, unavailable + ': ' + str(exc)[:180]) from exc


@app.get('/', response_class=HTMLResponse)
@app.get('/viewer', response_class=HTMLResponse)
def viewer():
    body = (ROOT / 'viewer' / 'index.html').read_text(encoding='utf-8')
    return body.replace('__ALLIE_CONFIG__', json.dumps(CONFIG, ensure_ascii=False).replace('<', '\\u003c'))


@app.get('/install/allie21_overlay.user.js')
def userscript():
    body = (ROOT / 'browser' / 'allie21_overlay.user.js').read_bytes()
    return Response(body, media_type='text/javascript; charset=utf-8')


@app.get('/install', response_class=HTMLResponse)
def userscript_installer():
    """Local fallback when Chromium does not hand .user.js to Tampermonkey."""
    source = (ROOT / 'browser' / 'allie21_overlay.user.js').read_text(encoding='utf-8')
    match = re.search(r'^// @version\s+(.+)$', source, re.MULTILINE)
    version = html.escape(match.group(1).strip() if match else 'aktuell')
    return f'''<!doctype html><html lang="de"><meta charset="utf-8"><title>Allie Overlay installieren</title>
<style>body{{font:16px system-ui;background:#071522;color:#edf7ff;max-width:720px;margin:50px auto;padding:24px}}.card{{background:#10283d;border:1px solid #43657e;border-radius:14px;padding:24px}}a{{display:inline-block;margin:6px 6px 6px 0;padding:11px 15px;border-radius:8px;background:#16a777;color:white;font-weight:700;text-decoration:none}}code{{background:#06101a;padding:3px 6px;border-radius:4px}}li{{margin:10px 0}}</style>
<div class="card"><h1>Allie Overlay {version}</h1><p>Wenn Tampermonkey nur seine leere Zwischenseite zeigt, fehlt in Edge die Freigabe für Userscripts.</p>
<ol><li>Öffne <code>edge://extensions</code>.</li><li>Öffne <b>Tampermonkey → Details</b>.</li><li>Aktiviere <b>Benutzerskripts zulassen / Allow user scripts</b>. Falls der Schalter fehlt: oben den <b>Entwicklermodus</b> einschalten.</li><li>Klicke danach hier:</li></ol>
<a href="/install/allie21_overlay.user.js">Overlay in Tampermonkey öffnen</a><a href="/install/allie21_overlay.download.user.js">Datei herunterladen</a>
<p>Nach der Installation Chess.com oder Lichess einmal neu laden.</p></div></html>'''


@app.get('/install/allie21_overlay.download.user.js')
def userscript_download():
    body = (ROOT / 'browser' / 'allie21_overlay.user.js').read_bytes()
    return Response(body, media_type='application/javascript; charset=utf-8', headers={
        'Content-Disposition': 'attachment; filename="allie21_overlay.user.js"',
    })


@app.get('/health')
def health():
    return {'alive': True, 'model': MODEL_NAME, 'model_revision': CONFIG['model_revision'],
            'model_loaded': allie._model is not None,
            'stockfish_available': bool(find_stockfish())}


@app.get('/api/state')
def state():
    return SESSION.get_state()


@app.post('/analyze')
def analyze(request: AnalysisRequest):
    return run(lambda: analyse_position(request.model_dump()))


@app.post('/api/start')
def start(request: StartRequest):
    return run(lambda: SESSION.start(request.model_dump()))


@app.post('/api/stop')
def stop():
    return SESSION.stop()


@app.post('/api/frame')
async def frame(request: Request):
    raw = await request.body()
    return run(lambda: SESSION.submit_frame(raw), 'Bretterkennung nicht verfügbar')


@app.post('/api/history')
def history(request: HistoryRequest):
    return run(lambda: SESSION.import_pgn(request.pgn))


@app.post('/api/recommendations')
def recommendations(request: RecommendationRequest):
    return run(lambda: SESSION.set_recommendations(request.enabled))


@app.post('/api/browser-position')
def browser_position(request: BrowserPositionRequest):
    return run(lambda: BROWSER_TRACKERS.observe(
        request.session_id, request.placement, request.pgn
    ))


def main():
    print('Allie 2.1 Live Studio v11 (nur lokal)')
    print('Viewer:', f'http://{HOST}:{PORT}/viewer')
    print('Modellrevision:', CONFIG['model_revision'])
    if os.environ.get('ALLIE_NO_PRELOAD') != '1':
        start_model_preload()
    if os.environ.get('ALLIE_NO_BROWSER') != '1':
        threading.Timer(1.0, lambda: webbrowser.open(f'http://{HOST}:{PORT}/viewer')).start()
    try:
        uvicorn.run(app, host=HOST, port=PORT, access_log=False, server_header=False)
    finally:
        SESSION.stop()


if __name__ == '__main__':
    main()

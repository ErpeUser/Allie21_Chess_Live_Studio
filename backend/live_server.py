#!/usr/bin/env python3
"""Local-only server. Browser capture means no OS-specific screen capture is needed."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import threading
import webbrowser
from urllib.parse import urlparse

from allie_local_server import HOST, PORT, MODEL_NAME, analyse_position
from live_session import LiveSession, MAX_JPEG
from config import CONFIG
from chess_extras import find_stockfish
from browser_session import BrowserTrackerPool

ROOT = Path(__file__).resolve().parents[1]
SESSION = LiveSession()
BROWSER_TRACKERS = BrowserTrackerPool()


class Handler(BaseHTTPRequestHandler):
    server_version = 'Allie21LiveStudio/10.0'

    def send_json(self, status, body):
        payload = json.dumps(body, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self._raw(status, payload, 'application/json; charset=utf-8')

    def log_message(self, fmt, *args):
        # Never log URL credentials or PGN content.
        if args and str(args[-1]).startswith('5'):
            print('HTTP server error', args[-1])

    def _host_ok(self):
        return self.headers.get('Host', '').lower() in {
            f'127.0.0.1:{PORT}', f'localhost:{PORT}', '127.0.0.1', 'localhost'}

    def _origin_ok(self):
        origin = self.headers.get('Origin', '')
        if not origin:
            return True
        parsed = urlparse(origin)
        if parsed.hostname in ('127.0.0.1', 'localhost') and parsed.scheme in ('http', 'https'):
            return True
        # Tampermonkey may originate on any chess site. The marker is not a
        # secret or access key: it only distinguishes the userscript request
        # from ordinary cross-site form/fetch requests (no CORS is exposed).
        return (parsed.scheme in ('http', 'https') and bool(parsed.hostname)
                and self.headers.get('X-Allie-Overlay') == '1')

    def _raw(self, status, content, mime):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy',
                         "default-src 'self' 'unsafe-inline' blob: data:; connect-src 'self'; media-src blob:; object-src 'none'; frame-ancestors 'none'")
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if not self._host_ok():
            return self.send_json(403, {'error': 'Host not allowed'})
        if self.path in ('/', '/viewer'):
            body = (ROOT / 'viewer' / 'index.html').read_text(encoding='utf-8')
            body = body.replace('__ALLIE_CONFIG__', json.dumps(CONFIG, ensure_ascii=False).replace('<', '\\u003c'))
            return self._raw(200, body.encode('utf-8'), 'text/html; charset=utf-8')
        if self.path == '/install/allie21_overlay.user.js':
            body = (ROOT / 'browser' / 'allie21_overlay.user.js').read_text(encoding='utf-8')
            return self._raw(200, body.encode('utf-8'), 'text/javascript; charset=utf-8')
        if self.path == '/health':
            from allie_local_server import _model
            return self.send_json(200, {'alive': True, 'model': MODEL_NAME,
                                        'model_loaded': _model is not None,
                                        'stockfish_available': bool(find_stockfish())})
        if self.path == '/api/state':
            return self.send_json(200, SESSION.get_state())
        return self.send_json(404, {'error': 'Not found'})

    def _analyse_post(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 65536:
                return self.send_json(413, {'error': 'Request too large or empty'})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('JSON object required')
            return self.send_json(200, analyse_position(data))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self.send_json(400, {'error': str(exc)[:240]})
        except Exception as exc:
            print('Chess analysis error:', repr(exc))
            return self.send_json(503, {'error': 'Analyse nicht verfügbar: ' + str(exc)[:160]})

    def do_POST(self):
        if not self._host_ok() or not self._origin_ok():
            return self.send_json(403, {'error': 'Local host or origin invalid'})
        if self.path == '/analyze':
            return self._analyse_post()
        if self.path not in ('/api/start', '/api/stop', '/api/frame', '/api/history',
                             '/api/recommendations', '/api/browser-position'):
            return self.send_json(404, {'error': 'Not found'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= (MAX_JPEG if self.path == '/api/frame' else 65536):
                return self.send_json(413, {'error': 'Request too large or empty'})
            raw = self.rfile.read(size)
            if self.path == '/api/frame':
                return self.send_json(200, SESSION.submit_frame(raw))
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError('JSON object required')
            if self.path == '/api/browser-position':
                return self.send_json(200, BROWSER_TRACKERS.observe(
                    str(data.get('session_id', '')),
                    str(data.get('placement', '')),
                    str(data.get('pgn', '')),
                ))
            if self.path == '/api/start':
                return self.send_json(200, SESSION.start(data))
            if self.path == '/api/stop':
                return self.send_json(200, SESSION.stop())
            if self.path == '/api/history':
                return self.send_json(200, SESSION.import_pgn(str(data.get('pgn', ''))))
            if self.path == '/api/recommendations':
                if not isinstance(data.get('enabled'), bool):
                    raise ValueError('enabled muss true oder false sein')
                return self.send_json(200, SESSION.set_recommendations(data['enabled']))
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            return self.send_json(400, {'error': str(exc)[:240]})
        except Exception as exc:
            print('Local server error:', repr(exc))
            return self.send_json(503, {'error': 'Analyse nicht verfügbar: ' + str(exc)[:200]})


def main():
    print('Allie 2.1 Live Studio v10 (nur lokal)')
    print('Viewer:', f'http://{HOST}:{PORT}/viewer')
    print('Model:', CONFIG['model_id'], '(weights are downloaded on first analysis)')
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    if os.environ.get('ALLIE_NO_BROWSER') != '1':
        threading.Timer(1.0, lambda: webbrowser.open(f'http://{HOST}:{PORT}/viewer')).start()
    try:
        httpd.serve_forever(poll_interval=.5)
    except KeyboardInterrupt:
        pass
    finally:
        SESSION.stop()
        httpd.server_close()


if __name__ == '__main__':
    main()

"""HTTP boundary tests without installing chess/ONNX/Allie or starting a real model.

This verifies security and routes, not engine correctness or Discord capture.
"""
import importlib.util
import json
import sys
import threading
import types
import unittest
from contextlib import ExitStack
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


class FakeSession:
    def __init__(self):
        self.running = False
    def get_state(self):
        return {'running': self.running}
    def start(self, settings):
        self.running = True
        return self.get_state()
    def stop(self):
        self.running = False
        return self.get_state()
    def import_pgn(self, pgn):
        return {'accepted': True}
    def set_recommendations(self, enabled):
        return {'running': self.running, 'recommendations_enabled': enabled}
    def submit_frame(self, raw):
        return {'bytes': len(raw)}


class FakeBrowserTrackerPool:
    def observe(self, session_id, placement, pgn=''):
        return {'ready': True, 'pgn': pgn or '*', 'session_id': session_id,
                'placement': placement}


class HTTPBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack = ExitStack()
        cls.addClassCleanup(cls.stack.close)
        allie = types.ModuleType('allie_local_server')
        allie.HOST = '127.0.0.1'; allie.PORT = 8765
        allie.MODEL_NAME = 'yimingzhang/allie-2.1'; allie._model = None
        allie.analyse_position = lambda payload: {'fen': payload.get('fen', ''), 'moves': []}
        live = types.ModuleType('live_session'); live.LiveSession = FakeSession; live.MAX_JPEG = 3500000
        extras = types.ModuleType('chess_extras'); extras.find_stockfish = lambda: None
        browser_session = types.ModuleType('browser_session')
        browser_session.BrowserTrackerPool = FakeBrowserTrackerPool
        cls.stack.enter_context(patch.dict(sys.modules, {
            'allie_local_server': allie, 'live_session': live, 'chess_extras': extras,
            'browser_session': browser_session,
        }))
        spec = importlib.util.spec_from_file_location('allie_v10_test_http', ROOT / 'backend' / 'live_server.py')
        app = importlib.util.module_from_spec(spec); spec.loader.exec_module(app)
        cls.app = app
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        cls.app.PORT = cls.server.server_port
        cls.addClassCleanup(cls.server.server_close)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.addClassCleanup(cls.server.shutdown)

    def call(self, method, path, origin='', host=None, payload=None, overlay=False):
        client = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        headers = {}
        if origin:
            headers['Origin'] = origin
        if host:
            headers['Host'] = host
        if payload is not None:
            headers['Content-Type'] = 'application/json'
        if overlay:
            headers['X-Allie-Overlay'] = '1'
        client.request(method, path, body=json.dumps(payload).encode() if payload is not None else None, headers=headers)
        response = client.getresponse()
        status = response.status
        data = response.read()
        client.close()
        return status, data

    def test_viewer_has_no_access_key_ui_or_placeholder(self):
        status, data = self.call('GET', '/viewer')
        self.assertEqual(status, 200)
        self.assertNotIn(b'__ALLIE_TOKEN__', data)
        self.assertNotIn(b'copyToken', data)

    def test_health_and_state_work_locally_without_key(self):
        self.assertEqual(self.call('GET', '/health')[0], 200)
        self.assertEqual(self.call('GET', '/api/state')[0], 200)

    def test_csrf_origin_blocked_and_host_checked(self):
        self.assertEqual(self.call('POST', '/api/start',
                                   origin='https://attacker.example', payload={})[0], 403)
        self.assertEqual(self.call('GET', '/viewer', host='attacker.example')[0], 403)

    def test_generic_chess_site_overlay_can_submit_visible_board(self):
        status, data = self.call(
            'POST', '/api/browser-position', origin='https://chess.example', overlay=True,
            payload={'session_id': 'web-test', 'placement': 'board', 'pgn': '*'},
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)['session_id'], 'web-test')

    def test_start_stop_and_analyze_are_separate(self):
        self.assertEqual(self.call('POST','/api/start',payload={})[0],200)
        status, data = self.call('POST','/api/recommendations',payload={'enabled':False})
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(data)['recommendations_enabled'])
        self.assertEqual(json.loads(self.call('POST','/analyze',payload={'fen':'test'})[1])['fen'],'test')
        self.assertEqual(self.call('POST','/api/stop',payload={})[0],200)

    def test_userscript_download_needs_no_ticket(self):
        status,data = self.call('GET','/install/allie21_overlay.user.js')
        self.assertEqual(status,200)
        self.assertNotIn(b'__ALLIE_INSTALL_TOKEN__',data)

if __name__ == '__main__':
    unittest.main()

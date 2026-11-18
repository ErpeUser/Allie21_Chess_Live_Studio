"""Exercise the shared pairing budget through the real local HTTP boundary."""
import json
import socket
import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
import live_server as app
import security


class HTTPPairingRateLimitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.socket = socket.socket()
        cls.socket.bind(('127.0.0.1', 0))
        cls.port = cls.socket.getsockname()[1]
        cls.server = uvicorn.Server(uvicorn.Config(
            app.app, host='127.0.0.1', log_level='critical',
            access_log=False, lifespan='off', ws='none',
        ))
        cls.thread = threading.Thread(
            target=cls.server.run, kwargs={'sockets': [cls.socket]}, daemon=True,
        )
        cls.thread.start()
        deadline = time.monotonic() + 5
        while not cls.server.started and time.monotonic() < deadline:
            time.sleep(.01)
        if not cls.server.started:
            cls.server.should_exit = True
            cls.thread.join(5)
            cls.socket.close()
            raise RuntimeError('Uvicorn pairing test server did not start')

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(5)
        cls.socket.close()

    def setUp(self):
        self.now = 100.0
        self.failures = {}
        self.origin = 'https://www.chess.com'
        self.code = '12345678'
        for target, name, value in (
            (security, '_PAIRING_CODE', self.code),
            (security, '_PAIRING_FAILURES', self.failures),
            (security, 'time', SimpleNamespace(monotonic=lambda: self.now)),
            (app, 'OVERLAY_SETTINGS', {
                'mode': 'private', 'confirmed_mode': 'private',
                'version': 1, 'updated_at': 1.0,
            }),
            (app, 'PRIVATE_OVERLAY', app.PrivateOverlayController()),
        ):
            replacement = patch.object(target, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)

    def call(self, method='GET', path='/api/overlay/settings', *,
             code='00000000', origin=None, extension=False):
        headers = {'X-Allie-Overlay': '1', 'X-Allie-Pairing': code}
        headers['Origin'] = self.origin if origin is None else origin
        if not headers['Origin']:
            del headers['Origin']
        if extension:
            headers['X-Allie-Extension'] = '1'
        body = None
        if method in {'POST', 'PUT'}:
            headers['Content-Type'] = 'application/json'
            body = json.dumps({'mode': 'private', 'version': 1})
        client = HTTPConnection('127.0.0.1', self.port, timeout=5)
        try:
            client.request(method, path, body=body, headers=headers)
            response = client.getresponse()
            return response.status, json.loads(response.read())
        finally:
            client.close()

    def test_settings_methods_stop_pairing_guesses_after_five_failures(self):
        for origin in (self.origin, 'chrome-extension://omboihgfgofgmidefcpkihgglhkiielo'):
            for method in ('GET', 'POST', 'PUT'):
                with self.subTest(origin=origin, method=method):
                    self.failures.clear()
                    statuses = [self.call(method, origin=origin)[0] for _ in range(5)]
                    self.assertEqual(statuses, [403] * 5)
                    status, payload = self.call(method, origin=origin, code=self.code)
                    self.assertEqual(status, 429, payload)
                    self.assertNotIn('mode', payload)

    def test_capability_and_settings_share_one_failure_budget(self):
        requests = [
            ('GET', '/api/capability', 401),
            ('GET', '/api/overlay/settings', 403),
            ('POST', '/api/overlay/settings', 403),
            ('GET', '/api/capability', 401),
            ('PUT', '/api/overlay/settings', 403),
        ]
        for method, path, expected in requests:
            self.assertEqual(self.call(method, path)[0], expected)
        for path in ('/api/capability', '/api/overlay/settings'):
            with self.subTest(path=path):
                status, payload = self.call(path=path, code=self.code)
                self.assertEqual(status, 429)
                self.assertNotIn('token', payload)

    def test_valid_polling_does_not_spend_or_reset_the_failure_budget(self):
        for _ in range(4):
            for method in ('GET', 'POST', 'PUT'):
                status, payload = self.call(method, code=self.code)
                self.assertEqual(status, 200, payload)
                self.assertEqual(payload['mode'], 'private')
        for _ in range(4):
            self.assertEqual(self.call()[0], 403)
        self.assertEqual(self.call(code=self.code)[0], 200)
        self.assertEqual(self.call()[0], 403)
        self.assertEqual(self.call(code=self.code)[0], 429)

    def test_expired_failure_budget_allows_pairing_again(self):
        for _ in range(5):
            self.assertEqual(self.call()[0], 403)
        self.assertEqual(self.call(code=self.code)[0], 429)
        self.now += 60.0
        status, payload = self.call(path='/api/capability', code=self.code)
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload['instance_id'], app.INSTANCE_ID)

    def test_trusted_viewer_and_extension_worker_keep_bootstrap_access(self):
        for _ in range(5):
            self.assertEqual(self.call()[0], 403)
        viewer_origin = f'http://127.0.0.1:{self.port}'
        self.assertEqual(self.call(origin=viewer_origin)[0], 200)
        self.assertEqual(self.call(origin='', extension=True)[0], 200)
        status, payload = self.call(path='/api/capability', origin='', extension=True)
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload['instance_id'], app.INSTANCE_ID)

    def test_concurrent_settings_guesses_cannot_overrun_the_budget(self):
        with ThreadPoolExecutor(max_workers=10) as pool:
            statuses = list(pool.map(lambda _: self.call()[0], range(10)))
        self.assertEqual(sorted(statuses), [403] * 5 + [429] * 5)


if __name__ == '__main__':
    unittest.main()

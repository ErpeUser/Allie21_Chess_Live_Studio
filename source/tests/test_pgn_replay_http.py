"""Exercise the local training route through real HTTP, without chess engines."""
from __future__ import annotations

import json
import socket
import sys
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
import live_server as server

ROUTE = '/api/pgn/replay'
PGN = '1. e4 e5 2. Nf3 Nc6 *'


class PgnReplayHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.socket = socket.socket()
        cls.socket.bind(('127.0.0.1', 0))
        cls.port = cls.socket.getsockname()[1]
        cls.server = uvicorn.Server(uvicorn.Config(
            server.app, host='127.0.0.1', log_level='critical',
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
            raise RuntimeError('Uvicorn training test server did not start')

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(5)
        cls.socket.close()

    def request(self, payload=None, *, headers=None, auth=True, body=None,
                method='POST'):
        supplied = {'Content-Type': 'application/json'}
        if auth:
            supplied.update({
                'Authorization': 'Bearer ' + server.CAPABILITY_TOKEN,
                'X-Allie-Instance': server.INSTANCE_ID,
            })
        supplied.update(headers or {})
        if body is None and payload is not None:
            body = json.dumps(payload).encode()
        client = HTTPConnection('127.0.0.1', self.port, timeout=5)
        try:
            client.request(method, ROUTE, body=body, headers=supplied)
            response = client.getresponse()
            return response.status, dict(response.getheaders()), json.loads(response.read())
        finally:
            client.close()

    def test_replay_returns_real_positions_without_model_or_live_session(self):
        with (patch.object(server, 'analyse_position', side_effect=AssertionError('engine called')),
              patch.object(server.allie, 'get_model', side_effect=AssertionError('model called')),
              patch.object(server.SESSION, 'import_pgn', side_effect=AssertionError('session mutated'))):
            for phase in ('loading', 'failed'):
                with self.subTest(phase=phase), patch.object(server, 'MODEL_STATE', phase):
                    status, headers, result = self.request({'pgn': PGN})
                    self.assertEqual(status, 200, result)
                    self.assertEqual(result['ply_count'], 4)
                    self.assertEqual(result['positions'][-1]['fen'],
                                     'r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3')
                    self.assertEqual(headers.get('cache-control'), 'no-store')

    def test_replay_requires_current_capability_and_instance(self):
        cases = [
            (False, {}),
            (True, {'Authorization': 'Bearer wrong-token'}),
            (True, {'X-Allie-Instance': 'previous-server-instance'}),
        ]
        for auth, headers in cases:
            with self.subTest(auth=auth, headers=headers):
                status, _, result = self.request({'pgn': PGN}, auth=auth, headers=headers)
                self.assertEqual(status, 401, result)
                self.assertNotIn('positions', result)

    def test_replay_preserves_host_and_origin_boundary(self):
        for headers in ({'Host': 'remote.invalid'}, {'Origin': 'https://remote.invalid'},
                        {'Origin': 'http://127.0.0.1:1'}):
            with self.subTest(headers=headers):
                status, _, _ = self.request({'pgn': PGN}, headers=headers)
                self.assertEqual(status, 403)
        status, _, result = self.request(
            {'pgn': PGN}, headers={'Origin': f'http://127.0.0.1:{self.port}'})
        self.assertEqual(status, 200, result)

    def test_replay_rejects_empty_oversized_and_unexpected_payloads(self):
        status, _, _ = self.request(body=b'')
        self.assertEqual(status, 413)
        status, _, _ = self.request(body=b'x' * (64 * 1024 + 1))
        self.assertEqual(status, 413)
        for payload in ({'pgn': 'x' * 40_001}, {'pgn': ''}, {'pgn': PGN, 'fen': 'extra'},
                        {'pgn': None}, {'pgn': ['1. e4 *']}):
            with self.subTest(payload_type=type(payload['pgn']).__name__):
                status, _, result = self.request(payload)
                self.assertEqual(status, 400, result)

    def test_invalid_pgn_returns_a_bounded_error_without_private_metadata(self):
        private = '[White "Private Fixture Name"]\n\n1. e4 e5 2. Bh6 *'
        status, _, result = self.request({'pgn': private})
        self.assertEqual(status, 400, result)
        self.assertEqual(set(result), {'error'})
        self.assertLessEqual(len(result['error']), 240)
        self.assertNotIn('Private Fixture Name', result['error'])
        self.assertNotIn('rnbq', result['error'])

    def test_replay_returns_no_headers_comments_or_pairing_secrets(self):
        pgn = '[White "Private Fixture Name"]\n[Site "https://private.invalid/"]\n\n1. e4 {hidden note} *'
        status, _, result = self.request({'pgn': pgn})
        self.assertEqual(status, 200, result)
        serialized = json.dumps(result)
        for private in ('Private Fixture Name', 'private.invalid', 'hidden note',
                        server.CAPABILITY_TOKEN, server.INSTANCE_ID):
            self.assertNotIn(private, serialized)

    def test_replay_is_post_only_and_does_not_put_pgn_in_a_get_url(self):
        status, _, _ = self.request(method='GET')
        self.assertEqual(status, 405)


if __name__ == '__main__':
    unittest.main()

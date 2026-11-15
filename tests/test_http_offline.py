"""Exercise the real FastAPI/Uvicorn boundary without loading chess models."""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
import live_server as app


class FakeSession:
    def __init__(self):
        self.running = False

    def get_state(self):
        return {'running': self.running}

    def start(self, _settings):
        self.running = True
        return self.get_state()

    def stop(self):
        self.running = False
        return self.get_state()

    def import_pgn(self, _pgn):
        return {'accepted': True}

    def set_recommendations(self, enabled):
        return {'running': self.running, 'recommendations_enabled': enabled}

    def submit_frame(self, raw):
        return {'bytes': len(raw)}


class FakeBrowserTrackerPool:
    def __init__(self):
        self.reset_session = ''

    def observe(self, session_id, placement, pgn='', pgn_candidates=None):
        return {'ready': True, 'pgn': pgn or '*', 'session_id': session_id,
                'placement': placement, 'candidates': pgn_candidates or []}

    def reset(self, session_id):
        self.reset_session = session_id


class HTTPBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.originals = (app.SESSION, app.BROWSER_TRACKERS, app.analyse_position,
                         app.find_stockfish)
        app.SESSION = FakeSession()
        app.BROWSER_TRACKERS = FakeBrowserTrackerPool()
        app.analyse_position = lambda payload: {'fen': payload.get('fen', ''), 'moves': []}
        app.find_stockfish = lambda: None
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            cls.port = probe.getsockname()[1]
        config = uvicorn.Config(app.app, host='127.0.0.1', port=cls.port,
                                log_level='critical', access_log=False)
        cls.server = uvicorn.Server(config)
        cls.server.install_signal_handlers = lambda: None
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()
        deadline = time.monotonic() + 5
        while not cls.server.started and time.monotonic() < deadline:
            time.sleep(.02)
        if not cls.server.started:
            raise RuntimeError('Uvicorn test server did not start')

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(5)
        (app.SESSION, app.BROWSER_TRACKERS, app.analyse_position,
         app.find_stockfish) = cls.originals

    def call(self, method, path, origin='', host=None, payload=None, overlay=False,
             preflight=False, auth=True, pairing=False, extension=False):
        client = HTTPConnection('127.0.0.1', self.port, timeout=5)
        headers = {}
        if origin:
            headers['Origin'] = origin
        if host:
            headers['Host'] = host
        if payload is not None:
            headers['Content-Type'] = 'application/json'
        if overlay:
            headers['X-Allie-Overlay'] = '1'
        if extension:
            headers['X-Allie-Extension'] = '1'
        if pairing:
            headers['X-Allie-Pairing'] = app.get_pairing_code()
        if auth and (method.upper() == 'POST' or path == '/api/state'):
            headers['Authorization'] = f'Bearer {app.CAPABILITY_TOKEN}'
            headers['X-Allie-Instance'] = app.INSTANCE_ID
        if preflight:
            headers['Access-Control-Request-Method'] = 'POST'
            headers['Access-Control-Request-Headers'] = 'content-type,x-allie-overlay,authorization,x-allie-instance'
        body = json.dumps(payload).encode() if payload is not None else None
        client.request(method, path, body=body, headers=headers)
        response = client.getresponse()
        status, data = response.status, response.read()
        client.close()
        return status, data

    def test_model_preload_warms_start_position_in_background(self):
        fake_model = object()
        with (patch('live_server.allie.get_model', return_value=fake_model) as load_model,
              patch('live_server.allie.analyse_position') as analyse):
            worker = app.start_model_preload()
            worker.join(1)
        self.assertFalse(worker.is_alive())
        load_model.assert_called_once_with()
        analyse.assert_called_once_with({
            'pgn': '*',
            'white_elo': app.CONFIG['white_elo'],
            'black_elo': app.CONFIG['black_elo'],
            'player_side': app.CONFIG['player_side'],
            'time_control': app.CONFIG['time_control'],
            'analysis_source': 'allie',
            'preview': False,
        }, model=fake_model)

    def test_mutating_request_requires_current_capability_token(self):
        status, _ = self.call('POST', '/api/start', payload={}, auth=False)
        self.assertEqual(status, 401)
        status, _ = self.call('POST', '/api/start', payload={},
                              auth=False)
        self.assertEqual(status, 401)

        client = HTTPConnection('127.0.0.1', self.port, timeout=5)
        client.request('POST', '/api/start', body=b'{}', headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer wrong-token',
        })
        response = client.getresponse()
        self.assertEqual(response.status, 401)
        response.read()
        client.close()

    def test_ragebait_style_crosses_http_and_live_validation(self):
        from live_session import LiveSession
        live = LiveSession()
        try:
            with patch.object(app, 'SESSION', live):
                status, data = self.call('POST', '/api/start', payload={
                    'play_style': 'ragebait', 'opening_white': 'halloween',
                    'opening_black': 'stafford',
                })
                self.assertEqual(status, 200, data)
                self.assertTrue(json.loads(data)['running'])
                self.assertEqual(live.settings['play_style'], 'ragebait')
                self.assertEqual(live.settings['opening_white'], 'halloween')
                self.assertEqual(live.settings['opening_black'], 'stafford')
            status, data = self.call('POST', '/analyze', payload={
                'pgn': '*', 'play_style': 'ragebait', 'analysis_source': 'allie',
            })
            self.assertEqual(status, 200, data)
            status, _ = self.call('POST', '/api/start', payload={'play_style': 'invalid-style'})
            self.assertEqual(status, 400)
        finally:
            live.stop()

    def test_capability_handshake_returns_instance_metadata(self):
        status, data = self.call('GET', '/api/capability',
                                 origin='https://www.chess.com', overlay=True,
                                 pairing=True)
        self.assertEqual(status, 200, data)
        capability = json.loads(data)
        self.assertEqual(capability['token'], app.CAPABILITY_TOKEN)
        self.assertEqual(capability['instance_id'], app.INSTANCE_ID)
        self.assertEqual(capability['api_version'], app.API_VERSION)
        self.assertEqual(capability['schema_version'], app.SCHEMA_VERSION)

    def test_overlay_payload_is_strictly_typed(self):
        payload = {
            'schema_version': 1, 'session_id': 'contract-test',
            'mode': 'private', 'geometry': {
                'board': {'left': 0, 'top': 0, 'width': 800, 'height': 800,
                          'unexpected': 1},
            },
        }
        status, _ = self.call('POST', '/api/overlay/update',
                              origin='https://www.chess.com', overlay=True,
                              payload=payload)
        self.assertEqual(status, 400)

    def test_browser_position_is_rate_limited(self):
        payload = {'session_id': 'rate-limited',
                   'placement': '8/8/8/3k4/8/8/4K3/8', 'pgn': '*'}
        statuses = [self.call('POST', '/api/browser-position',
                              origin='https://www.chess.com', overlay=True,
                              payload=payload)[0] for _ in range(11)]
        self.assertEqual(statuses[-1], 429)

    def test_viewer_has_no_access_key_ui_or_placeholder(self):
        status, data = self.call('GET', '/viewer')
        self.assertEqual(status, 200)
        self.assertNotIn(b'__ALLIE_TOKEN__', data)
        self.assertNotIn(b'copyToken', data)

    def test_health_and_state_work_locally_without_key(self):
        self.assertEqual(self.call('GET', '/health')[0], 200)
        self.assertEqual(self.call('GET', '/api/state')[0], 200)

    def test_readyz_reports_model_phase_without_internal_details(self):
        with (patch.object(app.allie, '_model', None),
              patch.object(app, 'MODEL_STATE', 'loading')):
            response = app.readyz()
        self.assertEqual(response.status_code, 503)
        payload = json.loads(response.body)
        self.assertEqual(payload, {
            'ready': False, 'phase': 'model_loading',
            'error_id': 'model_not_loaded',
        })

    def test_readyz_success_has_structured_shape(self):
        with patch.object(app.allie, '_model', object()), patch.object(
            app, 'find_stockfish', return_value='stockfish'
        ):
            payload = app.readyz()
        self.assertEqual(payload, {'ready': True, 'phase': 'ready', 'error_id': None})

    def test_engine_specific_readiness_is_exposed_over_http(self):
        with (patch.object(app.allie, '_model', None),
              patch.object(app, 'MODEL_STATE', 'failed'),
              patch.object(app, 'find_stockfish', return_value='stockfish')):
            status, data = self.call('GET', '/readyz?source=stockfish')
            self.assertEqual(status, 200, data)
            self.assertTrue(json.loads(data)['ready'])
            status, data = self.call('GET', '/readyz?source=allie')
            self.assertEqual(status, 503, data)
            self.assertEqual(json.loads(data)['phase'], 'model_failed')

    def test_fen_route_remains_available_during_model_loading(self):
        with patch.object(app, 'MODEL_STATE', 'loading'):
            status, data = self.call('POST', '/analyze', payload={
                'fen': '8/8/8/3k4/8/8/4K3/8 w - - 0 1', 'analysis_source': 'both'})
        self.assertEqual(status, 200, data)

    def test_analysis_accepts_only_known_play_styles(self):
        self.assertEqual(self.call('POST', '/analyze', payload={
            'pgn': '*', 'analysis_source': 'allie', 'play_style': 'aggressive'
        })[0], 200)
        self.assertEqual(self.call('POST', '/analyze', payload={
            'pgn': '*', 'analysis_source': 'allie', 'play_style': 'reckless'
        })[0], 400)

    def test_analysis_accepts_opening_selection(self):
        status, data = self.call('POST', '/analyze', payload={
            'pgn': '*', 'analysis_source': 'allie',
            'opening_white': 'vienna', 'opening_black': 'alekhine'
        })
        self.assertEqual(status, 200)
        self.assertIn(b'fen', data)

    def test_csrf_origin_blocked_and_host_checked(self):
        self.assertEqual(self.call('POST', '/api/start',
                                   origin='https://attacker.example', payload={})[0], 403)
        self.assertEqual(self.call('GET', '/viewer', host='attacker.example')[0], 403)

    def test_edge_extension_origin_is_allowed_only_for_overlay_requests(self):
        payload = {'session_id': 'web-edge', 'placement': '8/8/8/3k4/8/8/4K3/8', 'pgn': '*'}
        self.assertEqual(self.call('POST', '/api/browser-position',
                                   origin='chrome-extension://untrusted', payload=payload)[0], 403)
        self.assertEqual(self.call('POST', '/api/browser-position',
                                   origin='chrome-extension://omboihgfgofgmidefcpkihgglhkiielo', overlay=True, payload=payload)[0], 200)

    def test_extension_worker_pairing_without_browser_origin_is_allowed(self):
        status, data = self.call('GET', '/api/pairing', overlay=True, extension=True)
        self.assertEqual(status, 200, data)
        self.assertRegex(data.decode(), r'"pairing_code":"\d{8}"')
        status, data = self.call('GET', '/api/capability', overlay=True,
                                 pairing=True, extension=True)
        self.assertEqual(status, 200, data)
        self.assertIn(b'instance_id', data)

    def test_overlay_settings_write_requires_pairing_for_web_origin(self):
        payload = {'mode': 'normal', 'version': 1, 'source': 'auth-test'}
        for method in ('POST', 'PUT'):
            with self.subTest(method=method):
                status, data = self.call(
                    method, '/api/overlay/settings',
                    origin='https://www.chess.com', overlay=True,
                    payload=payload, auth=False, pairing=False,
                )
                self.assertEqual(status, 403, data)

    def test_overlay_request_must_explicitly_identify_itself(self):
        payload = {'session_id': 'web-test', 'placement': '8/8/8/3k4/8/8/4K3/8', 'pgn': '*'}
        self.assertEqual(self.call('POST', '/api/browser-position',
                                   origin='https://chess.example', payload=payload)[0], 403)
        self.assertEqual(self.call('POST', '/api/browser-position',
                                   origin='https://chess.example', overlay=True, payload=payload)[0], 403)
        status, data = self.call('POST', '/api/browser-position',
                                 origin='https://www.chess.com', overlay=True, payload=payload)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)['session_id'], 'web-test')

    def test_supported_site_cors_preflight(self):
        status, data = self.call('OPTIONS', '/api/browser-position',
                                 origin='https://www.chess.com', preflight=True)
        self.assertEqual(status, 200, data)

    def test_browser_session_can_be_reset_for_a_new_game(self):
        status, data = self.call('POST', '/api/browser-position/reset',
                                 origin='https://www.chess.com', overlay=True,
                                 payload={'session_id': 'web-new-game'})
        self.assertEqual(status, 200, data)
        self.assertEqual(app.BROWSER_TRACKERS.reset_session, 'web-new-game')

    def test_overlay_clear_carries_session_boundary(self):
        status, data = self.call(
            'POST', '/api/overlay/clear', origin='https://www.chess.com', overlay=True,
            payload={'session_id': 'web-clear-boundary', 'generation': 3,
                     'render_revision': 7, 'reason': 'navigation',
                     'owner_token': app.OVERLAY_LEASES.claim('web-clear-boundary').owner_token},
        )
        self.assertEqual(status, 200, data)
        self.assertEqual(json.loads(data)['reason'], 'navigation')

    def test_chesscom_tcn_becomes_complete_pgn_candidate(self):
        payload = {'session_id': 'web-spectator',
                   'placement': '8/8/8/3k4/8/8/4K3/8',
                   'tcn': 'mC0Kgv5Q'}
        status, data = self.call('POST', '/api/browser-position',
                                 origin='https://www.chess.com', overlay=True,
                                 payload=payload)
        self.assertEqual(status, 200, data)
        self.assertTrue(json.loads(data)['candidates'][0].startswith(
            '1. e4 e5 2. Nf3 Nc6'))

    def test_server_fetches_virtualised_chesscom_spectator_history(self):
        payload = {'session_id': 'web-spectator-server',
                   'placement': '8/8/8/3k4/8/8/4K3/8',
                   'game_id': '186750736526'}
        with patch('live_server._fetch_chesscom_tcn', return_value='mC0Kgv5Q') as fetch:
            status, data = self.call('POST', '/api/browser-position',
                                     origin='https://www.chess.com', overlay=True,
                                     payload=payload)
        self.assertEqual(status, 200, data)
        fetch.assert_called_once_with('186750736526')
        self.assertTrue(json.loads(data)['candidates'][0].startswith(
            '1. e4 e5 2. Nf3 Nc6'))

    def test_start_stop_and_analyze_are_separate(self):
        self.assertEqual(self.call('POST', '/api/start', payload={})[0], 200)
        status, data = self.call('POST', '/api/recommendations', payload={'enabled': False})
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(data)['recommendations_enabled'])
        response = self.call('POST', '/analyze', payload={'fen': 'test'})
        self.assertEqual(json.loads(response[1])['fen'], 'test')
        self.assertEqual(self.call('POST', '/api/stop', payload={})[0], 200)

    def test_size_validation_and_unknown_fields(self):
        self.assertEqual(self.call('POST', '/api/start', payload={'unknown': True})[0], 400)
        self.assertEqual(self.call('POST', '/api/start')[0], 413)

    def test_direct_extension_installer(self):
        status, page = self.call('GET', '/install')
        self.assertEqual(status, 200)
        self.assertIn(b'edge://extensions', page)
        extension_version = json.loads((ROOT / 'browser/manifest.json').read_text())['version_name']
        self.assertIn(extension_version.encode(), page)
        status, script = self.call('GET', '/install/allie21_overlay.user.js')
        self.assertEqual(status, 200)
        userscript_version = next(
            line.split()[-1] for line in
            (ROOT / 'browser/allie21_overlay.user.js').read_text(encoding='utf-8').splitlines()
            if line.startswith('// @version')
        )
        self.assertIn(f'@version      {userscript_version}'.encode(), script)


if __name__ == '__main__':
    unittest.main()

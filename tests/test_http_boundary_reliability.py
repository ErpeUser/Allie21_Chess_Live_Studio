"""Real ASGI request/response regressions, without loading model or vision code."""
from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI, Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from security import CAPABILITY_TOKEN, INSTANCE_ID


class HTTPBoundaryReliabilityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from http_boundary import LocalBoundaryMiddleware
        self.called = 0
        app = FastAPI()

        @app.api_route('/api/start', methods=['POST'])
        @app.api_route('/api/frame', methods=['POST'])
        @app.api_route('/api/stop', methods=['POST'])
        @app.get('/api/state')
        @app.get('/viewer')
        async def echo(request: Request):
            self.called += 1
            raw = await request.body()
            return {'body': raw.decode('ascii'), 'bytes': len(raw)}

        app.add_middleware(LocalBoundaryMiddleware, max_json=32, max_frame=128, body_timeout=0.05)
        self.app = app
        self.client = SimpleNamespace(post=lambda path, **kw: self.request('POST', path, **kw),
                                      options=lambda path, **kw: self.request('OPTIONS', path, **kw))
        self.auth = {'Authorization': 'Bearer ' + CAPABILITY_TOKEN, 'X-Allie-Instance': INSTANCE_ID}

    async def request(self, method, path, content=b'', headers=None):
        supplied = {key.lower(): str(value) for key, value in (headers or {}).items()}
        supplied.setdefault('host', '127.0.0.1:8765')
        scope = {'type':'http', 'asgi':{'version':'3.0'}, 'http_version':'1.1',
                 'method':method, 'scheme':'http', 'path':path, 'raw_path':path.encode(),
                 'query_string':b'', 'server':('127.0.0.1',8765), 'client':('127.0.0.1',1),
                 'root_path':'', 'headers':[(key.encode(), value.encode()) for key,value in supplied.items()]}
        chunks = content.__aiter__() if hasattr(content, '__aiter__') else None
        finished = False
        async def receive():
            nonlocal finished
            if finished:
                return {'type':'http.disconnect'}
            if chunks is None:
                finished = True
                return {'type':'http.request', 'body':content, 'more_body':False}
            try:
                return {'type':'http.request', 'body':await anext(chunks), 'more_body':True}
            except StopAsyncIteration:
                finished = True
                return {'type':'http.request', 'body':b'', 'more_body':False}
        messages = []
        async def send(message):
            messages.append(message)
        await self.app(scope, receive, send)
        start = next(message for message in messages if message['type']=='http.response.start')
        body = b''.join(message.get('body',b'') for message in messages if message['type']=='http.response.body')
        return SimpleNamespace(status_code=start['status'],
                               headers={key.decode():value.decode() for key,value in start.get('headers',[])},
                               json=lambda:json.loads(body))

    async def test_false_small_content_length_cannot_bypass_body_limit(self):
        r = await self.client.post('/api/start', content=b'x'*64, headers={**self.auth, 'content-length':'1'})
        self.assertEqual(r.status_code, 413)
        self.assertEqual(self.called, 0)

    async def test_declared_length_mismatch_is_rejected_before_dispatch(self):
        r = await self.client.post('/api/start', content=b'{}', headers={**self.auth, 'content-length':'1'})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.called, 0)

    async def test_chunked_body_is_replayed_exactly_once(self):
        async def chunks():
            yield b'{"a":'
            yield b'123}'
        r = await self.client.post('/api/start', content=chunks(), headers=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {'body':'{"a":123}', 'bytes':9})
        self.assertEqual(self.called, 1)

    async def test_frame_and_json_have_independent_size_limits(self):
        r = await self.client.post('/api/frame', content=b'x'*64, headers=self.auth)
        self.assertEqual(r.status_code, 200)
        r = await self.client.post('/api/start', content=b'x'*64, headers=self.auth)
        self.assertEqual(r.status_code, 413)

    async def test_slow_incomplete_body_has_deadline(self):
        async def chunks():
            yield b'{'
            await asyncio.sleep(1)
            yield b'}'
        r = await self.client.post('/api/start', content=chunks(), headers=self.auth)
        self.assertEqual(r.status_code, 408)
        self.assertEqual(self.called, 0)

    async def test_authentication_failure_has_cors_and_security_headers(self):
        r = await self.client.post('/api/start', content=b'{}', headers={
            'Origin':'https://www.chess.com', 'X-Allie-Overlay':'1'})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.headers.get('access-control-allow-origin'), 'https://www.chess.com')
        self.assertEqual(r.headers.get('cache-control'), 'no-store')
        self.assertEqual(r.headers.get('x-content-type-options'), 'nosniff')

    async def test_malformed_origin_is_forbidden_not_server_error(self):
        r = await self.client.post('/api/start', content=b'{}', headers={**self.auth, 'Origin':'https://['})
        self.assertEqual(r.status_code, 403)

    async def test_other_local_port_cannot_bootstrap_an_origin(self):
        r = await self.client.post('/api/start', content=b'{}', headers={**self.auth, 'Origin':'http://127.0.0.1:9999'})
        self.assertEqual(r.status_code, 403)

    async def test_current_local_origin_remains_allowed(self):
        r = await self.client.post('/api/start', content=b'{}', headers={**self.auth, 'Origin':'http://127.0.0.1:8765'})
        self.assertEqual(r.status_code, 200)

    async def test_website_origin_needs_overlay_header(self):
        r = await self.client.post('/api/start', content=b'{}', headers={**self.auth, 'Origin':'https://www.chess.com'})
        self.assertEqual(r.status_code, 403)

    async def test_viewer_bootstrap_is_not_exposed_to_website_origins(self):
        r = await self.request('GET', '/viewer', headers={'Origin':'https://www.chess.com', 'X-Allie-Overlay':'1'})
        self.assertEqual(r.status_code, 403)

    async def test_state_requires_capability(self):
        r = await self.request('GET', '/api/state')
        self.assertEqual(r.status_code, 401)
        r = await self.request('GET', '/api/state', headers=self.auth)
        self.assertEqual(r.status_code, 200)

    async def test_preflight_allows_current_protocol_headers(self):
        r = await self.client.options('/api/start', headers={'Origin':'https://www.chess.com',
            'Access-Control-Request-Method':'POST',
            'Access-Control-Request-Headers':'content-type,x-allie-overlay,authorization,x-allie-instance'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get('access-control-allow-origin'), 'https://www.chess.com')

    async def test_foreign_host_is_forbidden(self):
        r = await self.client.post('/api/start', content=b'{}', headers={**self.auth, 'Host':'other.example'})
        self.assertEqual(r.status_code, 403)

    async def test_body_required_and_optional_endpoints(self):
        r = await self.client.post('/api/start', headers=self.auth)
        self.assertEqual(r.status_code, 413)
        r = await self.client.post('/api/stop', headers=self.auth)
        self.assertEqual(r.status_code, 200)


class RealHTTPBoundaryTests(unittest.TestCase):
    def test_real_uvicorn_replays_chunked_body_and_rejects_invalid_token(self):
        import socket
        import threading
        import time
        from http.client import HTTPConnection

        import uvicorn
        from http_boundary import LocalBoundaryMiddleware

        app = FastAPI()

        @app.post('/api/start')
        async def echo(request: Request):
            return {'bytes': len(await request.body())}

        app.add_middleware(LocalBoundaryMiddleware, max_json=32)
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', log_level='critical', access_log=False, ws='none'))
        thread = threading.Thread(target=server.run, kwargs={'sockets':[sock]}, daemon=True)
        thread.start()
        deadline = time.monotonic() + 5
        try:
            while not server.started and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(server.started)
            client = HTTPConnection('127.0.0.1', port, timeout=5)
            try:
                client.request('POST', '/api/start', body=iter([b'{', b'}']), encode_chunked=True, headers={
                    'Authorization':'Bearer ' + CAPABILITY_TOKEN, 'X-Allie-Instance':INSTANCE_ID})
                response = client.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read()), {'bytes':2})
                client.request('POST', '/api/start', body=b'{}', headers={
                    'Authorization':'Bearer ' + chr(255), 'X-Allie-Instance':INSTANCE_ID,
                    'Origin':'https://www.chess.com', 'X-Allie-Overlay':'1'})
                response = client.getresponse()
                self.assertEqual(response.status, 401)
                self.assertEqual(response.getheader('Access-Control-Allow-Origin'), 'https://www.chess.com')
                response.read()
            finally:
                client.close()
        finally:
            server.should_exit = True
            thread.join(5)
            sock.close()


if __name__ == '__main__':
    unittest.main()

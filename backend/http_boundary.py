"""Local HTTP authorization and bounded body replay using public ASGI APIs."""
from __future__ import annotations

import asyncio
import math
import re
from urllib.parse import urlsplit

from fastapi import HTTPException
from security import require_capability
from starlette.datastructures import Headers, MutableHeaders
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

WEB_ORIGINS = frozenset({
    'https://chess.com', 'https://www.chess.com',
    'https://lichess.org', 'https://www.lichess.org',
})
EXTENSION_ORIGINS = frozenset({'chrome-extension://omboihgfgofgmidefcpkihgglhkiielo'})
PROTECTED_PATHS = frozenset({
    '/analyze', '/api/start', '/api/stop', '/api/frame', '/api/history',
    '/api/recommendations', '/api/browser-position', '/api/browser-position/reset',
    '/api/overlay/mode', '/api/overlay/update', '/api/overlay/clear',
})
BODY_REQUIRED = PROTECTED_PATHS - {'/api/stop', '/api/overlay/clear'}
SECURITY_HEADERS = {
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'no-referrer',
    'Content-Security-Policy': (
        "default-src 'self' 'unsafe-inline' blob: data:; connect-src 'self'; "
        "media-src blob:; object-src 'none'; frame-ancestors 'none'"
    ),
}


def _valid_host(host: str) -> bool:
    try:
        parsed = urlsplit('//' + host)
        return (parsed.hostname in {'127.0.0.1', 'localhost', 'testserver'}
                and parsed.username is None and parsed.password is None
                and not parsed.path and not parsed.query and not parsed.fragment
                and (parsed.port is None or 1 <= parsed.port <= 65535))
    except ValueError:
        return False


def _allowed_origin(origin: str, headers: Headers, scheme: str) -> bool:
    if not origin:
        return True
    if origin in WEB_ORIGINS or origin in EXTENSION_ORIGINS:
        return headers.get('x-allie-overlay') == '1'
    try:
        parsed = urlsplit(origin)
        host = urlsplit('//' + headers.get('host', ''))
        default_port = 443 if scheme == 'https' else 80
        return (parsed.scheme == scheme and scheme in {'http', 'https'}
                and parsed.hostname in {'127.0.0.1', 'localhost'}
                and parsed.username is None and parsed.password is None
                and not parsed.path and not parsed.query and not parsed.fragment
                and (parsed.port or default_port) == (host.port or default_port))
    except ValueError:
        return False


class LocalBoundaryMiddleware:
    """Bound all POST bodies, including dishonest or absent Content-Length.

    CORS wraps authorization so allowed clients can read JSON error responses.
    Only one bounded bytearray is accumulated before the application parses it;
    private Starlette Request attributes and unbounded chunk lists are avoided.
    """

    def __init__(self, app: ASGIApp, *, max_json: int = 64 * 1024,
                 max_frame: int = 3_500_000, body_timeout: float = 15.0) -> None:
        if max_json < 1 or max_frame < 1 or not math.isfinite(body_timeout) or body_timeout <= 0:
            raise ValueError('HTTP limits and timeout must be positive')
        self.app = app
        self.max_json = max_json
        self.max_frame = max_frame
        self.body_timeout = body_timeout
        self.cors = CORSMiddleware(
            self._guarded,
            allow_origins=sorted(WEB_ORIGINS | EXTENSION_ORIGINS),
            allow_methods=['GET', 'POST'],
            allow_headers=['Content-Type', 'Authorization', 'X-Allie-Overlay', 'X-Allie-Instance'],
            expose_headers=['Retry-After'],
            max_age=3600,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        async def secured_send(message: Message) -> None:
            if message['type'] == 'http.response.start':
                headers = MutableHeaders(scope=message)
                headers.update(SECURITY_HEADERS)
            await send(message)

        headers = Headers(scope=scope)
        if len(headers.getlist('host')) != 1 or not _valid_host(headers.get('host', '')):
            await self._error(403, 'Host not allowed', scope, receive, secured_send)
            return
        await self.cors(scope, receive, secured_send)

    @staticmethod
    async def _error(status: int, message: str, scope: Scope, receive: Receive, send: Send) -> None:
        headers = {'WWW-Authenticate': 'Bearer'} if status == 401 else None
        await JSONResponse({'error': message}, status_code=status, headers=headers)(scope, receive, send)

    async def _guarded(self, scope: Scope, receive: Receive, send: Send) -> None:
        headers = Headers(scope=scope)
        if len(headers.getlist('origin')) > 1 or not _allowed_origin(
            headers.get('origin', ''), headers, scope.get('scheme', 'http')
        ):
            await self._error(403, 'Local host or origin invalid', scope, receive, send)
            return
        if scope['method'] != 'OPTIONS' and scope['path'] in PROTECTED_PATHS:
            try:
                require_capability(Request(scope))
            except HTTPException as exc:
                await self._error(exc.status_code, str(exc.detail), scope, receive, send)
                return
        if scope['method'] != 'POST':
            await self.app(scope, receive, send)
            return
        maximum = self.max_frame if scope['path'] == '/api/frame' else self.max_json
        lengths = headers.getlist('content-length')
        declared = None
        if lengths:
            if len(lengths) != 1 or re.fullmatch(r'[0-9]{1,12}', lengths[0]) is None:
                await self._error(413, 'Request length invalid', scope, receive, send)
                return
            declared = int(lengths[0])
            if declared > maximum:
                await self._error(413, 'Request too large', scope, receive, send)
                return
            if headers.get('transfer-encoding'):
                await self._error(400, 'Ambiguous request framing', scope, receive, send)
                return
        body = bytearray()
        try:
            async with asyncio.timeout(self.body_timeout):
                while True:
                    message = await receive()
                    if message['type'] == 'http.disconnect':
                        return
                    chunk = message.get('body', b'')
                    if len(body) + len(chunk) > maximum:
                        await self._error(413, 'Request too large', scope, receive, send)
                        return
                    body.extend(chunk)
                    if not message.get('more_body', False):
                        break
        except TimeoutError:
            await self._error(408, 'Request body timed out', scope, receive, send)
            return
        if not body and scope['path'] in BODY_REQUIRED:
            await self._error(413, 'Request body required', scope, receive, send)
            return
        if declared is not None and declared != len(body):
            await self._error(400, 'Request length does not match body', scope, receive, send)
            return
        pending = True
        payload = bytes(body)
        del body

        async def replay() -> Message:
            nonlocal pending
            if pending:
                pending = False
                return {'type': 'http.request', 'body': payload, 'more_body': False}
            return await receive()

        await self.app(scope, replay, send)

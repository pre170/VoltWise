"""Small, deployment-only controls for a shared public hackathon demo."""

from __future__ import annotations

import asyncio
import base64
from collections import defaultdict, deque
import secrets
from threading import Lock
import time

from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import Settings


class RequestBodyTooLarge(Exception):
    pass


class PublicDemoSecurityMiddleware:
    """Protect the public demo while leaving local development unchanged."""

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.settings = settings
        credentials = (
            f"{settings.demo_basic_username}:{settings.demo_basic_password}".encode(
                "utf-8"
            )
        )
        self.expected_basic = "Basic " + base64.b64encode(credentials).decode("ascii")
        self._requests: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._rate_lock = Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path == "/health":
            await self.app(scope, receive, send)
            return
        if path == self.settings.mcp_path or path.startswith(
            f"{self.settings.mcp_path.rstrip('/')}/"
        ):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        supplied = headers.get(b"authorization", b"").decode("latin-1")
        if not secrets.compare_digest(supplied, self.expected_basic):
            response = JSONResponse(
                {"error": {"code": "AUTHENTICATION_REQUIRED", "message": "Authentication required."}},
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="VoltWise demo", charset="UTF-8"'},
            )
            await response(scope, receive, send)
            return

        if not path.startswith("/api/"):
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        bucket = "mutation" if method not in {"GET", "HEAD", "OPTIONS"} else "read"
        limit = (
            self.settings.rest_mutation_rate_limit_per_minute
            if bucket == "mutation"
            else self.settings.rest_rate_limit_per_minute
        )
        if not self._allow(client_ip, bucket, limit):
            response = JSONResponse(
                {"error": {"code": "RATE_LIMITED", "message": "Too many requests. Try again shortly."}},
                status_code=429,
                headers={"Retry-After": "60"},
            )
            await response(scope, receive, send)
            return

        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.settings.rest_max_request_body_size:
                    await self._too_large(scope, receive, send)
                    return
            except ValueError:
                response = JSONResponse(
                    {"error": {"code": "INVALID_REQUEST", "message": "Invalid Content-Length."}},
                    status_code=400,
                )
                await response(scope, receive, send)
                return

        try:
            body = await asyncio.wait_for(
                self._read_body(receive),
                timeout=self.settings.rest_request_timeout_seconds,
            )
        except RequestBodyTooLarge:
            await self._too_large(scope, receive, send)
            return
        except TimeoutError:
            await self._timeout(scope, receive, send)
            return

        body_delivered = False

        async def replay_receive() -> Message:
            nonlocal body_delivered
            if not body_delivered:
                body_delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        response_messages: list[Message] = []

        async def buffered_send(message: Message) -> None:
            response_messages.append(message)

        try:
            await asyncio.wait_for(
                self.app(scope, replay_receive, buffered_send),
                timeout=self.settings.rest_request_timeout_seconds,
            )
        except TimeoutError:
            await self._timeout(scope, receive, send)
            return

        for message in response_messages:
            await send(message)

    def _allow(self, client_ip: str, bucket: str, limit: int) -> bool:
        now = time.monotonic()
        cutoff = now - 60
        key = (client_ip, bucket)
        with self._rate_lock:
            requests = self._requests[key]
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= limit:
                return False
            requests.append(now)
            return True

    async def _read_body(self, receive: Receive) -> bytes:
        parts: list[bytes] = []
        received = 0
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.disconnect":
                break
            if message["type"] != "http.request":
                continue
            chunk = message.get("body", b"")
            received += len(chunk)
            if received > self.settings.rest_max_request_body_size:
                raise RequestBodyTooLarge
            parts.append(chunk)
            more_body = bool(message.get("more_body", False))
        return b"".join(parts)

    async def _too_large(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            {"error": {"code": "REQUEST_TOO_LARGE", "message": "Request body too large."}},
            status_code=413,
        )
        await response(scope, receive, send)

    async def _timeout(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            {"error": {"code": "REQUEST_TIMEOUT", "message": "Request timed out."}},
            status_code=504,
        )
        await response(scope, receive, send)

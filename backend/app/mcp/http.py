"""Official MCP Streamable HTTP transport for the shared VoltWise tool server."""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING, TypeAlias

from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import Settings
from app.mcp.server import bind_application, mcp, reset_application_binding

if TYPE_CHECKING:
    from app.application import VoltWiseApplication


class BearerTokenMiddleware:
    """Require one configured bearer token without logging or exposing it."""

    def __init__(
        self,
        app: ASGIApp,
        token: str | None,
        application: "VoltWiseApplication | None" = None,
    ) -> None:
        self.app = app
        self.token = token
        self.application = application

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        binding = bind_application(self.application) if self.application else None
        try:
            if scope["type"] != "http" or self.token is None:
                await self.app(scope, receive, send)
                return

            headers = dict(scope.get("headers", []))
            supplied = headers.get(b"authorization", b"").decode("latin-1")
            expected = f"Bearer {self.token}"
            if not secrets.compare_digest(supplied, expected):
                response = JSONResponse(
                    {"error": "Unauthorized"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
                await response(scope, receive, send)
                return
            await self.app(scope, receive, send)
        finally:
            if binding is not None:
                reset_application_binding(binding)


MCPHTTPApplication: TypeAlias = ASGIApp


def create_mcp_http_app(
    settings: Settings | None = None,
    application: "VoltWiseApplication | None" = None,
) -> MCPHTTPApplication:
    """Build the SDK's Streamable HTTP ASGI app with VoltWise security policy."""

    settings = settings or Settings.from_environment()
    if not settings.mcp_path.startswith("/"):
        raise ValueError("VOLTWISE_MCP_PATH must start with '/'")
    if settings.mcp_max_request_body_size <= 0:
        raise ValueError("VOLTWISE_MCP_MAX_REQUEST_BODY_SIZE must be positive")

    sdk_app = mcp.streamable_http_app(
        streamable_http_path=settings.mcp_path,
        max_request_body_size=settings.mcp_max_request_body_size,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=list(settings.mcp_allowed_hosts),
            allowed_origins=list(settings.mcp_allowed_origins),
        ),
        host=settings.mcp_host,
    )
    return BearerTokenMiddleware(sdk_app, settings.mcp_bearer_token, application)


def main() -> None:
    """Run the standalone Streamable HTTP MCP endpoint."""

    import uvicorn

    settings = Settings.from_environment()
    uvicorn.run(
        create_mcp_http_app(settings),
        host=settings.mcp_host,
        port=settings.mcp_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()

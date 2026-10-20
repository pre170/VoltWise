"""Single-port production ASGI composition for VoltWise.

The simulator gateway deliberately calls the MCP endpoint over loopback HTTP.
This module only composes transports and static hosting; it does not introduce
a direct application fallback.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.app import create_app
from app.application import get_application
from app.config import Settings
from app.mcp.http import BearerTokenMiddleware, create_mcp_http_app
from app.security import PublicDemoSecurityMiddleware


class SPAStaticFiles(StaticFiles):
    """Serve Vite assets and fall back to index.html for client-side routes."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            response = await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            response = None
        if response is not None and response.status_code != 404:
            return response
        if Path(path).suffix:
            if response is not None:
                return response
            raise HTTPException(status_code=404)
        return await super().get_response("index.html", scope)


class DeploymentApplication:
    """Route one public socket without stripping the MCP transport path."""

    def __init__(
        self,
        api_app: ASGIApp,
        mcp_app: ASGIApp,
        static_app: ASGIApp,
        *,
        mcp_path: str,
    ) -> None:
        self.api_app = api_app
        self.mcp_app = mcp_app
        self.static_app = static_app
        self.mcp_path = mcp_path.rstrip("/") or "/mcp"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self.api_app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path == self.mcp_path or path.startswith(f"{self.mcp_path}/"):
            await self.mcp_app(scope, receive, send)
            return
        if (
            path == "/health"
            or path.startswith("/api/")
            or path in ("/api", "/docs", "/redoc", "/openapi.json")
        ):
            await self.api_app(scope, receive, send)
            return
        await self.static_app(scope, receive, send)


def _deployment_settings() -> Settings:
    settings = Settings.from_environment()
    if "VOLTWISE_MCP_URL" not in os.environ:
        port = int(os.getenv("PORT", "8080"))
        settings = settings.model_copy(
            update={"mcp_url": f"http://127.0.0.1:{port}{settings.mcp_path}"}
        )
    return settings


def _static_directory() -> Path:
    configured = os.getenv("VOLTWISE_STATIC_DIR")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_deployment_app(
    settings: Settings | None = None,
    static_dir: Path | str | None = None,
) -> ASGIApp:
    """Compose static web, REST, and genuine MCP transport on one ASGI port."""

    settings = settings or _deployment_settings()
    static_path = Path(static_dir).resolve() if static_dir else _static_directory()
    if not (static_path / "index.html").is_file():
        raise RuntimeError(
            f"Frontend production build missing at {static_path}. Run npm run build first."
        )

    # Both adapters share one application container initialized from the same
    # settings and SQLite path. The MCP binding is request-local so constructing
    # a deployment app in tests cannot replace the standalone server singleton.
    application = get_application(settings)
    api: FastAPI = create_app(application, settings=settings)

    @api.get("/health", include_in_schema=False)
    def container_health() -> dict[str, str]:
        return {"status": "ok", "service": "voltwise"}

    mcp_http = create_mcp_http_app(settings, application)
    if not isinstance(mcp_http, BearerTokenMiddleware):
        raise RuntimeError("Unexpected MCP HTTP application wrapper")
    sdk_app = mcp_http.app
    api_lifespan = api.router.lifespan_context
    mcp_lifespan = sdk_app.router.lifespan_context

    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        async with api_lifespan(app):
            async with mcp_lifespan(sdk_app):
                yield

    api.router.lifespan_context = combined_lifespan
    static = SPAStaticFiles(directory=static_path, html=True, check_dir=True)
    deployment = DeploymentApplication(
        api,
        mcp_http,
        static,
        mcp_path=settings.mcp_path,
    )
    if settings.public_demo_enabled:
        return PublicDemoSecurityMiddleware(deployment, settings)
    return deployment


def main() -> None:
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    uvicorn.run(
        "app.deployment:create_deployment_app",
        factory=True,
        host=os.getenv("VOLTWISE_HOST", "0.0.0.0"),
        port=port,
        proxy_headers=True,
        forwarded_allow_ips=os.getenv("VOLTWISE_FORWARDED_ALLOW_IPS", "127.0.0.1"),
        log_level=os.getenv("VOLTWISE_LOG_LEVEL", "info"),
        workers=1,
    )


if __name__ == "__main__":
    main()

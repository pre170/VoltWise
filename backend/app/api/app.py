from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import demo, devices, energy, events, health, household, simulator, tariff
from app.application import VoltWiseApplication, get_application
from app.config import ApplicationMode, Settings
from app.errors import VoltWiseError
from app.repositories import SQLiteMCPTraceRepository
from app.services.simulator_gateway import SimulatorGateway


def create_app(
    application: VoltWiseApplication | None = None,
    *,
    settings: Settings | None = None,
) -> FastAPI:
    if application is None:
        application = get_application(settings) if settings is not None else get_application()
    settings = settings or application.settings
    public_docs = not settings.public_demo_enabled
    api = FastAPI(
        title="VoltWise API",
        version="0.4.0",
        description="Local API for deterministic VoltWise simulation and intelligence.",
        docs_url="/docs" if public_docs else None,
        redoc_url="/redoc" if public_docs else None,
        openapi_url="/openapi.json" if public_docs else None,
    )
    api.state.voltwise = application
    api.state.simulator_gateway = SimulatorGateway(
        settings,
        SQLiteMCPTraceRepository(settings.database_path),
    )
    api.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Accept"],
    )

    @api.exception_handler(VoltWiseError)
    async def voltwise_error_handler(request: Request, exc: VoltWiseError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @api.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        message = str(first.get("msg", "Invalid request"))
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "INVALID_REQUEST", "message": message}},
        )

    for router in (
        health.router,
        household.router,
        devices.router,
        energy.router,
        tariff.router,
        events.router,
        simulator.router,
    ):
        api.include_router(router, prefix="/api")
    if settings.mode is ApplicationMode.SIMULATION:
        api.include_router(demo.router, prefix="/api")
    return api


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("app.api.app:app", host="127.0.0.1", port=8000, reload=False)

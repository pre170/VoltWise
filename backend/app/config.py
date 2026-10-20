import os
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, model_validator


class ApplicationMode(StrEnum):
    SIMULATION = "SIMULATION"
    PRODUCTION = "PRODUCTION"


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: ApplicationMode = ApplicationMode.SIMULATION
    database_path: Path = Path("data/voltwise.db")
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000
    mcp_path: str = "/mcp"
    mcp_allowed_hosts: tuple[str, ...] = ("127.0.0.1:*", "localhost:*")
    mcp_allowed_origins: tuple[str, ...] = (
        "http://localhost:*",
        "http://127.0.0.1:*",
    )
    mcp_bearer_token: str | None = None
    mcp_max_request_body_size: int = 1_048_576
    mcp_url: str = "http://127.0.0.1:8001/mcp"
    mcp_client_timeout_seconds: float = 8.0
    public_demo_enabled: bool = False
    demo_basic_username: str | None = None
    demo_basic_password: str | None = None
    rest_max_request_body_size: int = 65_536
    rest_request_timeout_seconds: float = 12.0
    rest_rate_limit_per_minute: int = 120
    rest_mutation_rate_limit_per_minute: int = 30

    @model_validator(mode="after")
    def validate_public_demo_security(self):
        if self.rest_max_request_body_size <= 0:
            raise ValueError("VOLTWISE_REST_MAX_REQUEST_BODY_SIZE must be positive")
        if self.rest_request_timeout_seconds <= 0:
            raise ValueError("VOLTWISE_REST_REQUEST_TIMEOUT_SECONDS must be positive")
        if self.rest_rate_limit_per_minute <= 0:
            raise ValueError("VOLTWISE_REST_RATE_LIMIT_PER_MINUTE must be positive")
        if self.rest_mutation_rate_limit_per_minute <= 0:
            raise ValueError(
                "VOLTWISE_REST_MUTATION_RATE_LIMIT_PER_MINUTE must be positive"
            )
        if self.public_demo_enabled and not all(
            (
                self.demo_basic_username,
                self.demo_basic_password,
                self.mcp_bearer_token,
            )
        ):
            raise ValueError(
                "Public demo mode requires Basic credentials and an MCP bearer token"
            )
        return self

    @classmethod
    def from_environment(cls) -> "Settings":
        raw_origins = os.getenv(
            "VOLTWISE_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        )
        raw_mcp_hosts = os.getenv(
            "VOLTWISE_MCP_ALLOWED_HOSTS", "127.0.0.1:*,localhost:*"
        )
        raw_mcp_origins = os.getenv(
            "VOLTWISE_MCP_ALLOWED_ORIGINS",
            "http://localhost:*,http://127.0.0.1:*",
        )
        return cls(
            mode=ApplicationMode(
                os.getenv("VOLTWISE_MODE", ApplicationMode.SIMULATION.value).upper()
            ),
            database_path=Path(os.getenv("VOLTWISE_DB_PATH", "data/voltwise.db")),
            cors_origins=tuple(
                origin.strip() for origin in raw_origins.split(",") if origin.strip()
            ),
            mcp_host=os.getenv("VOLTWISE_MCP_HOST", "127.0.0.1"),
            mcp_port=int(os.getenv("VOLTWISE_MCP_PORT", "8000")),
            mcp_path=os.getenv("VOLTWISE_MCP_PATH", "/mcp"),
            mcp_allowed_hosts=tuple(
                host.strip() for host in raw_mcp_hosts.split(",") if host.strip()
            ),
            mcp_allowed_origins=tuple(
                origin.strip()
                for origin in raw_mcp_origins.split(",")
                if origin.strip()
            ),
            mcp_bearer_token=os.getenv("VOLTWISE_MCP_BEARER_TOKEN") or None,
            mcp_max_request_body_size=int(
                os.getenv("VOLTWISE_MCP_MAX_REQUEST_BODY_SIZE", "1048576")
            ),
            mcp_url=os.getenv(
                "VOLTWISE_MCP_URL", "http://127.0.0.1:8001/mcp"
            ),
            mcp_client_timeout_seconds=float(
                os.getenv("VOLTWISE_MCP_CLIENT_TIMEOUT_SECONDS", "8")
            ),
            public_demo_enabled=_environment_bool("VOLTWISE_PUBLIC_DEMO", False),
            demo_basic_username=os.getenv("VOLTWISE_DEMO_USERNAME") or None,
            demo_basic_password=os.getenv("VOLTWISE_DEMO_PASSWORD") or None,
            rest_max_request_body_size=int(
                os.getenv("VOLTWISE_REST_MAX_REQUEST_BODY_SIZE", "65536")
            ),
            rest_request_timeout_seconds=float(
                os.getenv("VOLTWISE_REST_REQUEST_TIMEOUT_SECONDS", "12")
            ),
            rest_rate_limit_per_minute=int(
                os.getenv("VOLTWISE_REST_RATE_LIMIT_PER_MINUTE", "120")
            ),
            rest_mutation_rate_limit_per_minute=int(
                os.getenv("VOLTWISE_REST_MUTATION_RATE_LIMIT_PER_MINUTE", "30")
            ),
        )


def _environment_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")

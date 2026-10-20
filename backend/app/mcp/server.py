from contextvars import ContextVar, Token

from mcp.server.mcpserver import Context, MCPServer

from app.application import VoltWiseApplication, get_application
from app.models import (
    ActionSuggestions,
    BillForecast,
    DeviceControlResult,
    DiagnosticWorkflowResult,
    LoadImpactResult,
    PeriodComparisonResult,
    TariffStatus,
    UsageChangeExplanation,
    VerificationResult,
)


application = get_application()
_request_application: ContextVar[VoltWiseApplication | None] = ContextVar(
    "voltwise_mcp_application", default=None
)

# Compatibility aliases retained for existing tests and local integrations.
connector = application.connector
service = application.verification_service
diagnostic_service = application.diagnostic_service
energy_repository = application.energy_repository
energy_service = application.energy_service
tariff_service = application.tariff_service

mcp = MCPServer("VoltWise")


def _current_application(context: Context | None = None):
    current = _request_application.get() or application
    if context is not None and context.protocol_version is not None:
        current.refresh_persisted_demo_state()
    return current


def bind_application(current: VoltWiseApplication) -> Token:
    """Bind one application container to the current MCP request context."""

    return _request_application.set(current)


def reset_application_binding(token: Token) -> None:
    _request_application.reset(token)


@mcp.tool()
def power_control_device(
    device: str, command: str = "TURN_ON", context: Context | None = None
) -> DeviceControlResult:
    """Control a simulated household device (light, fan, TV, AC, dishwasher)."""
    return _current_application(context).control_device(device, command)


@mcp.tool()
def power_turn_on_and_verify(
    device: str, context: Context | None = None
) -> VerificationResult:
    """Turn on a simulated device and verify its direct electrical response."""
    return _current_application(context).turn_on_and_verify(device)


@mcp.tool()
def power_run_diagnostic(
    device: str, context: Context | None = None
) -> DiagnosticWorkflowResult:
    """Verify, diagnose, safely retry when permitted, and re-verify a device."""
    return _current_application(context).run_diagnostic(device)


@mcp.tool()
def power_compare_periods(context: Context | None = None) -> PeriodComparisonResult:
    """Compare current-cycle energy with the equivalent previous-cycle period."""
    return _current_application(context).compare_periods()


@mcp.tool()
def power_explain_usage_change(
    context: Context | None = None,
) -> UsageChangeExplanation:
    """Rank observed contributors and preserve unattributed household usage."""
    return _current_application(context).explain_usage_change()


@mcp.tool()
def power_get_tariff_status(context: Context | None = None) -> TariffStatus:
    """Return current and projected position under the illustrative demo tariff."""
    return _current_application(context).get_tariff_status()


@mcp.tool()
def power_forecast_bill(context: Context | None = None) -> BillForecast:
    """Estimate current and projected energy charges, not a complete utility bill."""
    return _current_application(context).forecast_bill()


@mcp.tool()
def power_estimate_load_impact(
    device: str, context: Context | None = None
) -> LoadImpactResult:
    """Estimate a configured appliance operation's energy and incremental charge."""
    return _current_application(context).estimate_load_impact(device)


@mcp.tool()
def power_suggest_actions(
    target_kwh: float | None = None, context: Context | None = None
) -> ActionSuggestions:
    """Return evidence-based actions and optional target-consumption guidance."""
    return _current_application(context).suggest_actions(target_kwh)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

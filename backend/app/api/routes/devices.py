from fastapi import APIRouter, Depends

from app.api.dependencies import get_voltwise
from app.application import VoltWiseApplication
from app.models import DeviceView, DiagnosticWorkflowResult, VerificationResult


router = APIRouter(tags=["devices"])


@router.get("/devices", response_model=list[DeviceView], summary="List simulated devices")
def list_devices(
    application: VoltWiseApplication = Depends(get_voltwise),
) -> tuple[DeviceView, ...]:
    return application.list_devices()


@router.get(
    "/devices/{device_id}",
    response_model=DeviceView,
    summary="Get simulated device details",
)
def get_device(
    device_id: str, application: VoltWiseApplication = Depends(get_voltwise)
) -> DeviceView:
    return application.get_device(device_id)


@router.post(
    "/devices/{device_id}/turn-on-and-verify",
    response_model=VerificationResult,
    summary="Turn on and verify physical electrical response",
)
def turn_on_and_verify(
    device_id: str, application: VoltWiseApplication = Depends(get_voltwise)
) -> VerificationResult:
    return application.turn_on_and_verify(device_id)


@router.post(
    "/devices/{device_id}/diagnose",
    response_model=DiagnosticWorkflowResult,
    summary="Run safe diagnostic and recovery workflow",
)
def diagnose(
    device_id: str, application: VoltWiseApplication = Depends(get_voltwise)
) -> DiagnosticWorkflowResult:
    return application.run_diagnostic(device_id)

from fastapi import APIRouter, Depends

from app.api.dependencies import get_voltwise
from app.api.schemas import DeviceFaultRequest, EnergyScenarioRequest
from app.application import VoltWiseApplication
from app.models import DemoState


router = APIRouter(tags=["demo"])


@router.get("/demo/state", response_model=DemoState, summary="Current demo state")
def demo_state(
    application: VoltWiseApplication = Depends(get_voltwise),
) -> DemoState:
    return application.demo_state()


@router.post("/demo/reset", response_model=DemoState, summary="Reset canonical demo")
def reset_demo(
    application: VoltWiseApplication = Depends(get_voltwise),
) -> DemoState:
    return application.reset_demo()


@router.post(
    "/demo/energy-scenario",
    response_model=DemoState,
    summary="Switch deterministic energy scenario",
)
def set_energy_scenario(
    request: EnergyScenarioRequest,
    application: VoltWiseApplication = Depends(get_voltwise),
) -> DemoState:
    return application.set_energy_scenario(request.scenario)


@router.post(
    "/demo/device-fault",
    response_model=DemoState,
    summary="Inject deterministic simulated device fault",
)
def set_device_fault(
    request: DeviceFaultRequest,
    application: VoltWiseApplication = Depends(get_voltwise),
) -> DemoState:
    return application.set_device_fault(request.device, request.fault)

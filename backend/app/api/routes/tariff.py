from fastapi import APIRouter, Depends

from app.api.dependencies import get_voltwise
from app.api.schemas import TargetRequest
from app.application import VoltWiseApplication
from app.models import (
    ActionSuggestions,
    BillForecast,
    LoadImpactResult,
    TariffStatus,
)


router = APIRouter(tags=["tariff"])


@router.get(
    "/tariff/status",
    response_model=TariffStatus,
    summary="Current and projected tariff position",
)
def tariff_status(
    application: VoltWiseApplication = Depends(get_voltwise),
) -> TariffStatus:
    return application.get_tariff_status()


@router.get(
    "/tariff/forecast",
    response_model=BillForecast,
    summary="Estimated current and projected energy charge",
)
def tariff_forecast(
    application: VoltWiseApplication = Depends(get_voltwise),
) -> BillForecast:
    return application.forecast_bill()


@router.get(
    "/tariff/load-impact/{device_id}",
    response_model=LoadImpactResult,
    summary="Estimated appliance-operation tariff impact",
)
def load_impact(
    device_id: str, application: VoltWiseApplication = Depends(get_voltwise)
) -> LoadImpactResult:
    return application.estimate_load_impact(device_id)


@router.post(
    "/tariff/recommendations",
    response_model=ActionSuggestions,
    summary="Evidence-based consumption recommendations",
)
def recommendations(
    request: TargetRequest,
    application: VoltWiseApplication = Depends(get_voltwise),
) -> ActionSuggestions:
    return application.suggest_actions(request.target_kwh)

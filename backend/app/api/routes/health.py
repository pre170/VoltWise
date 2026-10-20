from fastapi import APIRouter, Depends

from app.api.dependencies import get_voltwise
from app.api.schemas import HealthResponse
from app.application import VoltWiseApplication


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Service health")
def health(
    application: VoltWiseApplication = Depends(get_voltwise),
) -> HealthResponse:
    return HealthResponse(
        status="ok", service="voltwise", mode=application.settings.mode.value.lower()
    )

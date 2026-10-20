from fastapi import APIRouter, Depends

from app.api.dependencies import get_voltwise
from app.application import VoltWiseApplication
from app.models import HouseholdOverview


router = APIRouter(tags=["household"])


@router.get(
    "/household/overview",
    response_model=HouseholdOverview,
    summary="Current household dashboard snapshot",
)
def household_overview(
    application: VoltWiseApplication = Depends(get_voltwise),
) -> HouseholdOverview:
    return application.household_overview()

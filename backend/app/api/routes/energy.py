from fastapi import APIRouter, Depends

from app.api.dependencies import get_voltwise
from app.application import VoltWiseApplication
from app.models import PeriodComparisonResult, UsageChangeExplanation


router = APIRouter(tags=["energy"])


@router.get(
    "/energy/comparison",
    response_model=PeriodComparisonResult,
    summary="Compare equivalent billing-cycle periods",
)
def comparison(
    application: VoltWiseApplication = Depends(get_voltwise),
) -> PeriodComparisonResult:
    return application.compare_periods()


@router.get(
    "/energy/explanation",
    response_model=UsageChangeExplanation,
    summary="Explain observed household usage increase",
)
def explanation(
    application: VoltWiseApplication = Depends(get_voltwise),
) -> UsageChangeExplanation:
    return application.explain_usage_change()

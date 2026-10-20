from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_voltwise
from app.application import VoltWiseApplication
from app.models import ApplicationEvent


router = APIRouter(tags=["events"])


@router.get("/events", response_model=list[ApplicationEvent], summary="Recent audit events")
def recent_events(
    limit: int = Query(default=50, ge=1, le=200),
    application: VoltWiseApplication = Depends(get_voltwise),
):
    return application.recent_events(limit)

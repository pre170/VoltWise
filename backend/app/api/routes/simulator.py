from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_simulator_gateway
from app.api.schemas import SimulatorChatRequest
from app.models import MCPTrace, SimulatorChatResponse
from app.services.simulator_gateway import SimulatorGateway


router = APIRouter(prefix="/sim", tags=["simulator"])


@router.post(
    "/chat",
    response_model=SimulatorChatResponse,
    summary="Route a simulated conversation through real MCP",
)
async def chat(
    request: SimulatorChatRequest,
    gateway: SimulatorGateway = Depends(get_simulator_gateway),
) -> SimulatorChatResponse:
    return await gateway.chat(request.message)


@router.get(
    "/traces",
    response_model=list[MCPTrace],
    summary="Recent real MCP gateway traces",
)
def recent_traces(
    limit: int = Query(default=30, ge=1, le=200),
    gateway: SimulatorGateway = Depends(get_simulator_gateway),
):
    return gateway.recent_traces(limit)

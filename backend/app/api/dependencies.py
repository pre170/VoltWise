from fastapi import Request

from app.application import VoltWiseApplication
from app.services.simulator_gateway import SimulatorGateway


def get_voltwise(request: Request) -> VoltWiseApplication:
    return request.app.state.voltwise


def get_simulator_gateway(request: Request) -> SimulatorGateway:
    return request.app.state.simulator_gateway

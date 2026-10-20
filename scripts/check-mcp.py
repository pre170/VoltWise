"""Fail-fast readiness probe using the same official MCP client as the gateway."""

from __future__ import annotations

import asyncio
import os
import sys

import httpx2
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


EXPECTED_TOOLS = {
    "power_turn_on_and_verify",
    "power_run_diagnostic",
    "power_compare_periods",
    "power_explain_usage_change",
    "power_get_tariff_status",
    "power_forecast_bill",
    "power_estimate_load_impact",
    "power_suggest_actions",
}


async def check(url: str) -> None:
    token = os.getenv("VOLTWISE_MCP_BEARER_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    async with httpx2.AsyncClient(headers=headers, timeout=5.0) as http_client:
        async with streamable_http_client(url, http_client=http_client) as streams:
            async with ClientSession(*streams, read_timeout_seconds=5.0) as session:
                initialized = await session.initialize()
                available = {tool.name for tool in (await session.list_tools()).tools}
    missing = EXPECTED_TOOLS - available
    if missing:
        raise RuntimeError(f"MCP registry is missing {len(missing)} required tool(s)")
    print(
        "[VoltWise] MCP ready: official client initialized "
        f"protocol={initialized.protocol_version}, "
        f"required_tools={len(EXPECTED_TOOLS)}, discovered_tools={len(available)}"
    )


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001/mcp"
    try:
        asyncio.run(check(url))
    except Exception as exc:
        print(
            f"[VoltWise] MCP readiness check failed ({type(exc).__name__}). "
            "Review .voltwise-run/mcp.err.log.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

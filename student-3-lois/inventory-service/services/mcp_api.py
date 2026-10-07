import os

import requests

MCP_SERVICE_URL = os.getenv("MCP_SERVICE_URL", "http://host.docker.internal:5004")
MCP_ENABLED = os.getenv("MCP_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")

try:
    MCP_SERVICE_TIMEOUT_SECONDS = int(os.getenv("MCP_SERVICE_TIMEOUT_SECONDS", "30"))
except ValueError:
    MCP_SERVICE_TIMEOUT_SECONDS = 30


def mcp_mode_is_enabled(req) -> bool:
    if not MCP_ENABLED:
        return False
    mode_header = req.headers.get("X-MCP-Mode", "on").strip().lower()
    return mode_header in ("1", "true", "yes", "on")


def mcp_disabled_response():
    return "<p>MCP Mode is disabled.</p>", 403


def call_mcp_tool(tool_name: str, payload: dict):
    response = requests.post(
        f"{MCP_SERVICE_URL}/tool/{tool_name}",
        json=payload,
        timeout=MCP_SERVICE_TIMEOUT_SECONDS,
    )
    try:
        data = response.json()
    except ValueError:
        response.raise_for_status()
        return {}
    if response.status_code >= 400:
        raise requests.HTTPError(
            f"MCP service call to '{tool_name}' failed with status {response.status_code}: {data}",
            response=response,
        )
    return data

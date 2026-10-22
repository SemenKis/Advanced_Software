import os

import requests

MULTI_AGENT_SERVER_URL = os.getenv("MULTI_AGENT_SERVER_URL", "http://host.docker.internal:5005")

TRUTHY = ("1", "true", "yes", "on")

try:
    MULTI_AGENT_TIMEOUT_SECONDS = int(os.getenv("MULTI_AGENT_TIMEOUT_SECONDS", "240"))
except ValueError:
    MULTI_AGENT_TIMEOUT_SECONDS = 240

QUICK_TIMEOUT_SECONDS = 10


def multi_agent_mode_is_enabled(req) -> bool:
    if os.getenv("MULTI_AGENT_ENABLED", "true").strip().lower() not in TRUTHY:
        return False

    return req.headers.get("X-Multi-Agent-Mode", "on").strip().lower() in TRUTHY


def call_multi_agent_server(method: str, path: str, payload=None, timeout=MULTI_AGENT_TIMEOUT_SECONDS):
    response = requests.request(
        method,
        f"{MULTI_AGENT_SERVER_URL}{path}",
        json=payload,
        timeout=timeout,
    )
    try:
        data = response.json()
    except ValueError:
        data = {"status": "error", "error": response.text}
    return data, response.status_code
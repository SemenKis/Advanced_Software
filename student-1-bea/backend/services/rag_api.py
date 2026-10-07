import os

import requests

RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://host.docker.internal:5003")

TRUTHY = ("1", "true", "yes", "on")

try:
    RAG_SERVICE_TIMEOUT_SECONDS = int(os.getenv("RAG_SERVICE_TIMEOUT_SECONDS", "180"))
except ValueError:
    RAG_SERVICE_TIMEOUT_SECONDS = 180


def rag_mode_is_enabled(req) -> bool:
    if os.getenv("RAG_ENABLED", "true").strip().lower() not in TRUTHY:
        return False

    return req.headers.get("X-RAG-Mode", "on").strip().lower() in TRUTHY


def call_rag_service(path: str, payload: dict):

    response = requests.post(
        f"{RAG_SERVICE_URL}{path}",
        json=payload,
        timeout=RAG_SERVICE_TIMEOUT_SECONDS,
    )
    try:
        data = response.json()
    except ValueError:
        data = {"status": "error", "error": response.text}
    return data, response.status_code
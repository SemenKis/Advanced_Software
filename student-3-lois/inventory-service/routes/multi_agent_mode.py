
import os

import requests
from flask import Blueprint, jsonify, request

from services.database_api import get_products

multi_agent_bp = Blueprint("multi_agent_mode", __name__)

MULTI_AGENT_SERVICE_URL = os.getenv(
    "MULTI_AGENT_SERVICE_URL",
    "http://host.docker.internal:5006"
)


@multi_agent_bp.get("/api/multi-agent/inventory")
def inventory_snapshot():
    """Expose a read-only snapshot of products to the inventory multi-agent server."""
    try:
        return jsonify({"products": get_products()}), 200
    except Exception as exc:
        return jsonify({
            "error": "Could not fetch inventory data.",
            "detail": str(exc),
        }), 503


@multi_agent_bp.post("/api/multi-agent/workflow")
def run_multi_agent_workflow():
    """Forward a user request to the locally running inventory multi-agent server."""
    data = request.get_json(silent=True) or {}
    user_request = data.get("request")

    if not isinstance(user_request, str) or not user_request.strip():
        return jsonify({
            "error": "A non-empty 'request' field is required."
        }), 400

    try:
        response = requests.post(
            f"{MULTI_AGENT_SERVICE_URL.rstrip('/')}/workflow",
            json={"request": user_request},
            timeout=120,
        )

        return (
            response.text,
            response.status_code,
            {"Content-Type": response.headers.get(
                "Content-Type", "application/json"
            )},
        )

    except requests.RequestException as exc:
        return jsonify({
            "error": "Could not connect to the multi-agent server.",
            "detail": str(exc),
        }), 502

"""
MULTI_AGENT_SERVICE_URL = os.getenv("MULTI_AGENT_SERVICE_URL", "http://localhost:5004")

try:
    MULTI_AGENT_SERVICE_TIMEOUT_SECONDS = int(os.getenv("MULTI_AGENT_SERVICE_TIMEOUT_SECONDS", "60"))
except ValueError:
    MULTI_AGENT_SERVICE_TIMEOUT_SECONDS = 60


def multi_agent_mode_is_enabled(req) -> bool:
    enabled = os.getenv("MULTI_AGENT_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")
    if not enabled:
        return False

    mode_header = req.headers.get("X-Multi-Agent-Mode", "on").strip().lower()
    return mode_header in ("1", "true", "yes", "on")


def multi_agent_disabled_response():
    return {"status": "error", "error": "Multi-Agent mode is disabled."}, 403


@multi_agent_bp.post("/multi-agent/workflow")
def multi_agent_workflow():
    if not multi_agent_mode_is_enabled(request):
        return multi_agent_disabled_response()

    data = request.get_json(silent=True) or {}
    user_request = data.get("user_request", "").strip()

    if not user_request:
        return {"status": "error", "error": "user_request is required"}, 400

    try:
        response = requests.post(
            f"{MULTI_AGENT_SERVICE_URL}/workflow",
            json={"user_request": user_request},
            timeout=MULTI_AGENT_SERVICE_TIMEOUT_SECONDS,
        )
        return response.json(), response.status_code
    except requests.RequestException as exc:
        return {"status": "error", "error": str(exc)}, 503


@multi_agent_bp.get("/multi-agent/workflow/status")
def multi_agent_workflow_status():
    if not multi_agent_mode_is_enabled(request):
        return multi_agent_disabled_response()

    try:
        response = requests.get(
            f"{MULTI_AGENT_SERVICE_URL}/workflow/status",
            timeout=MULTI_AGENT_SERVICE_TIMEOUT_SECONDS,
        )
        return response.json(), response.status_code
    except requests.RequestException as exc:
        return {"status": "error", "error": str(exc)}, 503
"""
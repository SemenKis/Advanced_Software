from flask import Blueprint, jsonify, request
import requests

from services.multi_agent_api import (
    QUICK_TIMEOUT_SECONDS,
    call_multi_agent_server,
    multi_agent_mode_is_enabled,
)


multi_agent_bp = Blueprint("multi_agent_mode", __name__)

# Tells the shared multi-agent server to use the order agents, not the warehouse ones
DOMAIN = "orders"

ALLOWED_DECISIONS = ("Accept", "Partially Accept", "Reject")
MAX_REQUEST_LENGTH = 1000
MAX_NOTE_LENGTH = 500


def _disabled():
    return jsonify({"status": "error", "error": "Multi-Agent Mode is disabled."}), 403


def _forward(method: str, path: str, payload=None, timeout=None):
    """Call the multi-agent server and translate the outcome into an HTTP response."""
    kwargs = {"timeout": timeout} if timeout else {}
    try:
        data, status_code = call_multi_agent_server(method, path, payload, **kwargs)
    except requests.RequestException as exc:
        return jsonify({
            "status": "error",
            "error": "Could not reach the Multi-Agent server. Check that it is running.",
            "details": str(exc),
        }), 503

    # A failure inside the multi-agent server is an upstream error, not ours
    if status_code >= 500:
        return jsonify(data), 502
    return jsonify(data), status_code


@multi_agent_bp.post("/multi-agent/workflow")
def multi_agent_workflow():
    if not multi_agent_mode_is_enabled(request):
        return _disabled()

    data = request.get_json(silent=True) or {}
    user_request = str(data.get("request", "")).strip()

    if not user_request:
        return jsonify({"status": "error", "error": "request is required"}), 400
    if len(user_request) > MAX_REQUEST_LENGTH:
        return jsonify({
            "status": "error",
            "error": f"request must be {MAX_REQUEST_LENGTH} characters or fewer",
        }), 400

    # The server's field is "request", not "user_request"
    return _forward("POST", "/workflow", {"request": user_request, "domain": DOMAIN})


@multi_agent_bp.get("/multi-agent/workflow/status")
def multi_agent_workflow_status():
    if not multi_agent_mode_is_enabled(request):
        return _disabled()
    return _forward("GET", f"/workflow/status?domain={DOMAIN}", timeout=QUICK_TIMEOUT_SECONDS)


@multi_agent_bp.post("/multi-agent/workflow/decision")
def multi_agent_workflow_decision():
    if not multi_agent_mode_is_enabled(request):
        return _disabled()

    data = request.get_json(silent=True) or {}
    workflow_id = str(data.get("workflow_id", "")).strip()
    decision = str(data.get("decision", "")).strip()
    note = str(data.get("note", "")).strip()

    if not workflow_id:
        return jsonify({"status": "error", "error": "workflow_id is required"}), 400
    if decision not in ALLOWED_DECISIONS:
        return jsonify({
            "status": "error",
            "error": "decision must be one of: " + ", ".join(ALLOWED_DECISIONS),
        }), 400
    if len(note) > MAX_NOTE_LENGTH:
        return jsonify({
            "status": "error",
            "error": f"note must be {MAX_NOTE_LENGTH} characters or fewer",
        }), 400

    return _forward(
        "POST",
        "/workflow/decision",
        {"workflow_id": workflow_id, "decision": decision, "note": note, "domain": DOMAIN},
        timeout=QUICK_TIMEOUT_SECONDS,
    )
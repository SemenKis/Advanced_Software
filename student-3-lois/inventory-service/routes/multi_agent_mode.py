from flask import Blueprint, jsonify, request

from services.multi_agent_api import (
    MAX_NOTE_CHARS,
    MAX_REQUEST_CHARS,
    MultiAgentError,
    health,
    multi_agent_mode_is_enabled,
    record_decision,
    run_workflow,
    workflow_status,
)

multi_agent_bp = Blueprint("multi_agent_mode", __name__)


def _disabled_response():
    return jsonify({"error": "Multi-Agent mode is disabled."}), 403


def _error_response(exc: MultiAgentError):
    return jsonify({"error": exc.message}), exc.status_code


@multi_agent_bp.get("/api/multi-agent/health")
def multi_agent_health():
    try:
        return jsonify(health()), 200
    except MultiAgentError as exc:
        return _error_response(exc)


@multi_agent_bp.post("/api/multi-agent/workflow")
def multi_agent_workflow():
    """Forward an inventory request to the shared multi-agent server."""
    if not multi_agent_mode_is_enabled(request):
        return _disabled_response()

    data = request.get_json(silent=True) or {}
    user_request = data.get("request")
    if not isinstance(user_request, str) or not user_request.strip():
        return jsonify({"error": "A non-empty 'request' field is required."}), 400
    user_request = user_request.strip()
    if len(user_request) > MAX_REQUEST_CHARS:
        return jsonify({"error": f"'request' must be {MAX_REQUEST_CHARS} characters or fewer."}), 400

    try:
        return jsonify(run_workflow(user_request)), 200
    except MultiAgentError as exc:
        return _error_response(exc)


@multi_agent_bp.post("/api/multi-agent/decision")
def multi_agent_decision():
    """Record the human decision for an inventory workflow."""
    if not multi_agent_mode_is_enabled(request):
        return _disabled_response()

    data = request.get_json(silent=True) or {}
    workflow_id = data.get("workflow_id")
    decision = data.get("decision")
    note = data.get("note", "")

    workflow_id = workflow_id.strip() if isinstance(workflow_id, str) else ""
    decision = decision.strip() if isinstance(decision, str) else ""
    note = note.strip() if isinstance(note, str) else ""

    if not workflow_id:
        return jsonify({"error": "'workflow_id' is required."}), 400
    if not decision:
        return jsonify({"error": "'decision' is required."}), 400
    if len(note) > MAX_NOTE_CHARS:
        return jsonify({"error": f"'note' must be {MAX_NOTE_CHARS} characters or fewer."}), 400

    try:
        return jsonify(record_decision(workflow_id, decision, note)), 200
    except MultiAgentError as exc:
        return _error_response(exc)


@multi_agent_bp.get("/api/multi-agent/status")
def multi_agent_status():
    if not multi_agent_mode_is_enabled(request):
        return _disabled_response()
    try:
        return jsonify(workflow_status()), 200
    except MultiAgentError as exc:
        return _error_response(exc)

import os

from flask import Blueprint, jsonify, request
import requests

from services.mcp_client import call_tool


mcp_bp = Blueprint("mcp_mode", __name__)

TRUTHY = ("1", "true", "yes", "on")


def mcp_mode_is_enabled(req) -> bool:

    enabled = os.getenv("MCP_ENABLED", "true").strip().lower() in TRUTHY
    if not enabled:
        return False

    mode_header = req.headers.get("X-MCP-Mode", "on").strip().lower()
    return mode_header in TRUTHY


@mcp_bp.post("/mcp/check-order-status")
def mcp_check_order_status():
    if not mcp_mode_is_enabled(request):
        return jsonify({"error": "MCP Mode is disabled."}), 403

    data = request.get_json(silent=True) or {}
    order_id = str(data.get("order_id", "")).strip()

    if order_id and not order_id.isdigit():
        return jsonify({"error": "order_id must be a number."}), 400

    arguments = {"order_id": order_id} if order_id else {}

    try:
        payload, status_code = call_tool("check_order_status", arguments)
    except requests.RequestException as exc:
        return jsonify({
            "error": "Could not reach the MCP server. Check that it is running.",
            "details": str(exc),
        }), 503

    if status_code == 200 and payload.get("status") == "error":
        return jsonify(payload), 502

    return jsonify(payload), status_code
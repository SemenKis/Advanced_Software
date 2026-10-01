from flask import Blueprint, jsonify, request
import requests

from services.rag_api import call_rag_service, rag_mode_is_enabled


rag_bp = Blueprint("rag_mode", __name__)

CALLER = "student-1"
DEFAULT_K = 5
MAX_K = 20


def _forward(path: str, payload: dict):
    """Call the RAG server and translate the outcome into an HTTP response."""
    try:
        data, status_code = call_rag_service(path, payload)
    except requests.RequestException as exc:
        return jsonify({
            "status": "error",
            "error": "Could not reach the RAG server. Check that it is running.",
            "details": str(exc),
        }), 503

    # A failure inside the RAG server is an upstream error, not ours
    if status_code >= 500:
        return jsonify(data), 502
    return jsonify(data), status_code


def _read_query_and_k():
    """Returns (query, k, error_response). error_response is None when valid."""
    data = request.get_json(silent=True) or {}

    query = str(data.get("query", "")).strip()
    if not query:
        return None, None, (jsonify({"status": "error", "error": "query is required"}), 400)

    try:
        k = int(data.get("k", DEFAULT_K))
    except (TypeError, ValueError):
        return None, None, (jsonify({"status": "error", "error": "k must be a number"}), 400)
    if not 1 <= k <= MAX_K:
        return None, None, (jsonify({"status": "error", "error": f"k must be between 1 and {MAX_K}"}), 400)

    return query, k, None


def _disabled():
    return jsonify({"status": "error", "error": "RAG Mode is disabled."}), 403


@rag_bp.post("/rag/refresh")
def rag_refresh():
    if not rag_mode_is_enabled(request):
        return _disabled()
    return _forward("/refresh", {"caller": CALLER})


@rag_bp.post("/rag/retrieve")
def rag_retrieve():
    if not rag_mode_is_enabled(request):
        return _disabled()
    query, k, error = _read_query_and_k()
    if error:
        return error
    return _forward("/retrieve", {"query": query, "k": k, "caller": CALLER})


@rag_bp.post("/rag/answer")
def rag_answer():
    if not rag_mode_is_enabled(request):
        return _disabled()
    query, k, error = _read_query_and_k()
    if error:
        return error
    return _forward("/answer", {"query": query, "k": k, "caller": CALLER})
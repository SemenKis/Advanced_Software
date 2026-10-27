import os

from flask import Flask, jsonify, request

from coordinator import record_decision, run_workflow, workflow_status
from domains import DEFAULT_DOMAIN, DOMAINS

app = Flask(__name__)


def _read_domain(raw, default=DEFAULT_DOMAIN):
    """Returns a valid domain name, or None if the caller sent an unknown one."""
    if raw is None or str(raw).strip() == "":
        return default
    domain = str(raw).strip().lower()
    return domain if domain in DOMAINS else None


def _unknown_domain():
    allowed = ", ".join(DOMAINS)
    return jsonify({"error": f"Unknown domain. Allowed values: {allowed}."}), 400


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "multi-agent-server"}), 200


@app.post("/workflow")
def workflow():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400
    user_request = payload.get("request")
    if not isinstance(user_request, str):
        user_request = ""
    user_request = user_request.strip()
    if not user_request:
        return jsonify({"error": "Field 'request' is required."}), 400
    domain = _read_domain(payload.get("domain"))
    if domain is None:
        return _unknown_domain()
    return jsonify(run_workflow(user_request, domain)), 200


@app.get("/workflow/status")
def status():
    # Callers that send no domain get the warehouse view, so another domain's
    # workflows never show up in a warehouse caller's history
    domain = _read_domain(request.args.get("domain"))
    if domain is None:
        return _unknown_domain()
    return jsonify(workflow_status(domain)), 200


@app.post("/workflow/decision")
def decision():
    payload = request.get_json(silent=True) or {}
    domain = _read_domain(payload.get("domain"))
    if domain is None:
        return _unknown_domain()
    ok, message = record_decision(
        (payload.get("workflow_id") or "").strip(),
        (payload.get("decision") or "").strip(),
        (payload.get("note") or "").strip(),
        domain,
    )
    return jsonify({"message": message}), (200 if ok else 400)


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(
        host="0.0.0.0",  # noqa: S104 - Docker backends reach this host service via host.docker.internal
        port=int(os.getenv("PORT", "5005")),
        debug=debug_mode,
    )
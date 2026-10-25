import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from coordinator import record_decision, run_workflow, workflow_status
from domains import DEFAULT_DOMAIN, DOMAINS

app = Flask(__name__)
CORS(app) 


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
    if len(user_request) > 1000:
        return jsonify({"error": "Field 'request' must be 1000 characters or fewer."}), 400
    domain = payload.get("domain", DEFAULT_DOMAIN)
    if not isinstance(domain, str) or domain not in DOMAINS:
        return jsonify({
            "error": "Field 'domain' must be one of: " + ", ".join(DOMAINS),
        }), 400
    return jsonify(run_workflow(user_request, domain)), 200


@app.get("/workflow/status")
def status():
    domain = request.args.get("domain")
    if domain and domain not in DOMAINS:
        return jsonify({
            "error": "Query parameter 'domain' must be one of: " + ", ".join(DOMAINS),
        }), 400
    return jsonify(workflow_status(domain)), 200


@app.post("/workflow/decision")
def decision():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400
    workflow_id = payload.get("workflow_id")
    decision_value = payload.get("decision")
    note = payload.get("note", "")
    domain = payload.get("domain")
    workflow_id = workflow_id.strip() if isinstance(workflow_id, str) else ""
    decision_value = decision_value.strip() if isinstance(decision_value, str) else ""
    note = note.strip() if isinstance(note, str) else ""
    if domain is not None and (not isinstance(domain, str) or domain not in DOMAINS):
        return jsonify({
            "error": "Field 'domain' must be one of: " + ", ".join(DOMAINS),
        }), 400
    if len(note) > 500:
        return jsonify({"error": "Field 'note' must be 500 characters or fewer."}), 400
    ok, message = record_decision(
        workflow_id,
        decision_value,
        note,
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

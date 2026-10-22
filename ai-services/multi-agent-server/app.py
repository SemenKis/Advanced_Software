import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from coordinator import record_decision, run_workflow, workflow_status

app = Flask(__name__)
CORS(app) 


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "multi-agent-server"}), 200


@app.post("/workflow")
def workflow():
    payload = request.get_json(silent=True) or {}
    user_request = (payload.get("request") or "").strip()
    if not user_request:
        return jsonify({"error": "Field 'request' is required."}), 400
    return jsonify(run_workflow(user_request)), 200


@app.get("/workflow/status")
def status():
    return jsonify(workflow_status()), 200


@app.post("/workflow/decision")
def decision():
    payload = request.get_json(silent=True) or {}
    ok, message = record_decision(
        (payload.get("workflow_id") or "").strip(),
        (payload.get("decision") or "").strip(),
        (payload.get("note") or "").strip(),
    )
    return jsonify({"message": message}), (200 if ok else 400)


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(
        host="0.0.0.0",  # noqa: S104 - Docker backends reach this host service via host.docker.internal
        port=int(os.getenv("PORT", "5005")),
        debug=debug_mode,
    )

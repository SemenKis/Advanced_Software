from flask import Flask, jsonify, request
import requests
import os
from ai_agent import run_prioritisation_loop


app = Flask(__name__)
DB_SERVICE_URL = os.environ.get("DB_SERVICE_URL", "http://database:5002")

RESOURCES = ["storage-locations", "packing-lists", "shipping-tasks"]

@app.route("/health")
def health():
    return {"status": "ok", "service": "student2-backend"}


@app.route("/api/<resource>", methods=["GET", "POST"])
def collection(resource):
    if resource not in RESOURCES:
        return jsonify({"error": f"Resource '{resource}' not found"}), 404

    url = f"{DB_SERVICE_URL}/api/{resource}"

    if request.method == "GET":
        r = requests.get(url)
    else:
        r = requests.post(url, json=request.get_json(force=True))
    return (r.text, r.status_code, {"Content-Type": "application/json"}) 


@app.route("/api/<resource>/<int:item_id>", methods=["GET", "PUT", "DELETE"])
def item(resource, item_id):
    if resource not in RESOURCES:
        return jsonify({"error": f"Resource '{resource}' not found"}), 404

    url = f"{DB_SERVICE_URL}/api/{resource}/{item_id}"

    if request.method == "GET":
        r = requests.get(url)
    elif request.method == "PUT":
        r = requests.put(url, json=request.get_json(force=True))
    else:
        r = requests.delete(url)
    if r.status_code == 204:
        return "", 204
    return (r.text, r.status_code, {"Content-Type": "application/json"})


@app.route("/api/ai/prioritise-shipping-tasks", methods=["POST"])
def prioritise_shipping_tasks():
    result = run_prioritisation_loop(DB_SERVICE_URL)
    return jsonify(result)





MCP_SERVER_URL = os.environ.get('MCP_SERVER_URL', 'http://host.docker.internal:5004')
RAG_SERVER_URL = os.environ.get('RAG_SERVER_URL', 'http://host.docker.internal:5003')
MCP_ENABLED = os.environ.get('MCP_ENABLED', 'false').lower() in ('1', 'true', 'yes')
RAG_ENABLED = os.environ.get('RAG_ENABLED', 'false').lower() in ('1', 'true', 'yes')


@app.route('/mcp/check-storage-capacity', methods=['POST'])
def mcp_check_storage_capacity():
    if not MCP_ENABLED:
        return jsonify({'status': 'error', 'error': 'MCP mode is disabled'}), 403

    zone_name = request.form.get('zone_name', '').strip()
    try:
        resp = requests.post(
            f'{MCP_SERVER_URL}/tool/check_storage_capacity',
            json={'zone_name': zone_name},
            timeout=10,
        )
        resp.raise_for_status()
        return jsonify(resp.json()), 200
    except requests.exceptions.RequestException as exc:
        return jsonify({'status': 'error', 'error': f'MCP server unreachable: {exc}'}), 503


@app.route('/rag/answer', methods=['POST'])
def rag_answer():
    if not RAG_ENABLED:
        return jsonify({'status': 'error', 'error': 'RAG mode is disabled'}), 403

    query = request.form.get('query', '').strip()
    if not query:
        return jsonify({'status': 'error', 'error': 'query is required'}), 400

    try:
        resp = requests.post(
            f'{RAG_SERVER_URL}/answer',
            json={'query': query, 'k': 5, 'caller': 'warehouse-management'},
            timeout=60,
        )
        resp.raise_for_status()
        return jsonify(resp.json()), 200
    except requests.exceptions.RequestException as exc:
        return jsonify({'status': 'error', 'error': f'RAG server unreachable: {exc}'}), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

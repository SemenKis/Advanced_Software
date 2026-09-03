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



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

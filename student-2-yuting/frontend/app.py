from flask import Flask, render_template, request, redirect
import requests
import os

app = Flask(__name__)
BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:5001")
RESOURCE_CONFIG = {
    "storage": {
        "api": "storage-locations",
        "fields": ["zone_name", "aisle", "shelf", "bin_code", "capacity", "current_load", "status"],
        "int_fields": ["capacity", "current_load"],
        "rows_template": "storage_rows.html",
        "page_template": "storage.html",
    },
    "packing-lists": {
        "api": "packing-lists",
        "fields": ["order_id", "items_json", "status"],
        "int_fields": ["order_id"],
        "rows_template": "_packing_rows.html",
        "page_template": "packing_lists.html",
    },
    "shipping-tasks": {
        "api": "shipping-tasks",
        "fields": ["order_id", "packing_list_id", "task_type", "assigned_to", "priority", "status", "bottleneck_risk"],
        "int_fields": ["order_id", "packing_list_id", "priority"],
        "rows_template": "_shipping_rows.html",
        "page_template": "shipping_tasks.html",
    },
}

def fetch_items(cfg):
    return requests.get(f"{BACKEND_URL}/api/{cfg['api']}", timeout=10).json()

def build_payload(cfg, form):
    payload = {}
    for f in cfg["fields"]:
        if f in form:
            val = form[f]
            payload[f] = int(val) if (f in cfg["int_fields"] and val != "") else val
    return payload



@app.route("/")
def home():
    return redirect("/storage")


@app.route("/<resource>")
def resource_page(resource):
    cfg = RESOURCE_CONFIG.get(resource)
    if not cfg:
        return "Not found", 404
    return render_template(cfg["page_template"])


@app.route("/<resource>/table")
def resource_table(resource):
    cfg = RESOURCE_CONFIG.get(resource)
    if not cfg:
        return "Not found", 404
    return render_template(cfg["rows_template"], items=fetch_items(cfg))




@app.route("/<resource>/add", methods=["POST"])
def resource_add(resource):
    cfg = RESOURCE_CONFIG.get(resource)
    if not cfg: 
        return "Not found", 404
    requests.post(f"{BACKEND_URL}/api/{cfg['api']}", json=build_payload(cfg, request.form), timeout=10)
    return render_template(cfg["rows_template"], items=fetch_items(cfg))




@app.route("/<resource>/<int:item_id>/update", methods=["POST"])
def resource_update(resource, item_id):
    cfg = RESOURCE_CONFIG.get(resource)
    if not cfg:
        return "Not found", 404
    requests.put(f"{BACKEND_URL}/api/{cfg['api']}/{item_id}", json=build_payload(cfg, request.form), timeout=10)
    return render_template(cfg["rows_template"], items=fetch_items(cfg))



@app.route("/<resource>/<int:item_id>/delete", methods=["DELETE"])
def resource_delete(resource, item_id):
    cfg = RESOURCE_CONFIG.get(resource)
    if not cfg:
        return "Not found", 404
    requests.delete(f"{BACKEND_URL}/api/{cfg['api']}/{item_id}", timeout=10)
    return render_template(cfg["rows_template"], items=fetch_items(cfg))


@app.route("/shipping-tasks/prioritise", methods=["POST"])
def shipping_prioritise():
    requests.post(f"{BACKEND_URL}/api/ai/prioritise-shipping-tasks", timeout=120)
    cfg = RESOURCE_CONFIG["shipping-tasks"]
    return render_template(cfg["rows_template"], items=fetch_items(cfg))




@app.route("/mcp-rag")
def mcp_rag_page():
    return render_template("mcp_rag.html")




@app.route("/mcp/check-storage-capacity", methods=["POST"])
def mcp_check_storage_capacity():
    zone_name = request.form.get("zone_name", "")
    resp = requests.post(f"{BACKEND_URL}/mcp/check-storage-capacity", data={"zone_name": zone_name}, timeout=15)
    return resp.text, resp.status_code, {"Content-Type": "application/json"}


@app.route("/rag/answer", methods=["POST"])
def rag_answer_forward():
    query = request.form.get("query", "")
    resp = requests.post(f"{BACKEND_URL}/rag/answer", data={"query": query}, timeout=120)
    return resp.text, resp.status_code, {"Content-Type": "application/json"}


def _forward_multi_agent(method, path, payload=None, timeout=220):
    try:
        resp = requests.request(method, f"{BACKEND_URL}{path}", json=payload, timeout=timeout)
        return resp.text, resp.status_code, {"Content-Type": "application/json"}
    except requests.exceptions.RequestException as exc:
        return {"status": "error", "error": f"Backend unreachable: {exc}"}, 503


@app.route("/multi-agent")
def multi_agent_page():
    return render_template("multi_agent.html")


@app.route("/multi-agent/workflow", methods=["POST"])
def multi_agent_workflow_forward():
    data = request.get_json(silent=True) or request.form
    return _forward_multi_agent("POST", "/multi-agent/workflow", {"request": data.get("request", "")})


@app.route("/multi-agent/workflow/status", methods=["GET"])
def multi_agent_status_forward():
    return _forward_multi_agent("GET", "/multi-agent/workflow/status", timeout=10)


@app.route("/multi-agent/workflow/decision", methods=["POST"])
def multi_agent_decision_forward():
    data = request.get_json(silent=True) or request.form
    return _forward_multi_agent("POST", "/multi-agent/workflow/decision", {
        "workflow_id": data.get("workflow_id", ""),
        "decision": data.get("decision", ""),
        "note": data.get("note", ""),
    }, timeout=10)


if __name__ =="__main__":
    app.run(host="0.0.0.0", port=5000)

    
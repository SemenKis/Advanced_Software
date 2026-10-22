from flask import Flask, jsonify, render_template, request, redirect, url_for
import requests
import os

app = Flask(__name__)
BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:5001")
URL_PREFIX = os.environ.get("URL_PREFIX", "").rstrip("/")
TEAM_HOME_URL = os.environ.get("TEAM_HOME_URL", "http://localhost:8080")


class PrefixMiddleware:
    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        if self.prefix and (
            environ["PATH_INFO"] == self.prefix
            or environ["PATH_INFO"].startswith(f"{self.prefix}/")
        ):
            environ["SCRIPT_NAME"] = f"{environ.get('SCRIPT_NAME', '')}{self.prefix}"
            environ["PATH_INFO"] = environ["PATH_INFO"][len(self.prefix):] or "/"
        return self.app(environ, start_response)


if URL_PREFIX:
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, URL_PREFIX)


@app.context_processor
def inject_navigation_config():
    return {"team_home_url": TEAM_HOME_URL}
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
    return requests.get(f"{BACKEND_URL}/api/{cfg['api']}").json()

def build_payload(cfg, form):
    payload = {}
    for f in cfg["fields"]:
        if f in form:
            val = form[f]
            payload[f] = int(val) if (f in cfg["int_fields"] and val != "") else val
    return payload



@app.route("/")
def home():
    return redirect(url_for("resource_page", resource="storage"))


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "warehouse-frontend"})


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
    requests.post(f"{BACKEND_URL}/api/{cfg['api']}", json=build_payload(cfg, request.form))
    return render_template(cfg["rows_template"], items=fetch_items(cfg))




@app.route("/<resource>/<int:item_id>/update", methods=["POST"])
def resource_update(resource, item_id):
    cfg = RESOURCE_CONFIG.get(resource)
    if not cfg:
        return "Not found", 404
    requests.put(f"{BACKEND_URL}/api/{cfg['api']}/{item_id}", json=build_payload(cfg, request.form))
    return render_template(cfg["rows_template"], items=fetch_items(cfg))



@app.route("/<resource>/<int:item_id>/delete", methods=["DELETE"])
def resource_delete(resource, item_id):
    cfg = RESOURCE_CONFIG.get(resource)
    if not cfg:
        return "Not found", 404
    requests.delete(f"{BACKEND_URL}/api/{cfg['api']}/{item_id}")
    return render_template(cfg["rows_template"], items=fetch_items(cfg))


@app.route("/shipping-tasks/prioritise", methods=["POST"])
def shipping_prioritise():
    requests.post(f"{BACKEND_URL}/api/ai/prioritise-shipping-tasks")
    cfg = RESOURCE_CONFIG["shipping-tasks"]
    return render_template(cfg["rows_template"], items=fetch_items(cfg))




@app.route("/mcp-rag")
def mcp_rag_page():
    return render_template("mcp_rag.html")




@app.route("/mcp/check-storage-capacity", methods=["POST"])
def mcp_check_storage_capacity():
    zone_name = request.form.get("zone_name", "")
    resp = requests.post(f"{BACKEND_URL}/mcp/check-storage-capacity", data={"zone_name": zone_name})
    return resp.text, resp.status_code, {"Content-Type": "application/json"}


@app.route("/rag/answer", methods=["POST"])
def rag_answer_forward():
    query = request.form.get("query", "")
    resp = requests.post(f"{BACKEND_URL}/rag/answer", data={"query": query})
    return resp.text, resp.status_code, {"Content-Type": "application/json"}


if __name__ =="__main__":
    app.run(host="0.0.0.0", port=5000)

    
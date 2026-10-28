import importlib.util
import os
import sys
import threading
from pathlib import Path

import pytest
from flask import Flask
from werkzeug.serving import make_server

SERVICE_DIR = Path(__file__).resolve().parents[1] / "inventory-service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from routes.multi_agent_mode import multi_agent_bp  # noqa: E402
from services import multi_agent_api as api  # noqa: E402


@pytest.fixture()
def client():
    app = Flask(__name__)
    app.register_blueprint(multi_agent_bp)
    return app.test_client()


class FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


# ---------- client: always targets the shared server with domain=inventory ----------

def test_run_workflow_sends_inventory_domain(monkeypatch):
    sent = {}

    def fake_request(method, url, timeout=None, **kwargs):
        sent.update(method=method, url=url, json=kwargs.get("json"))
        return FakeResponse(200, {"workflow_id": "w1"})

    monkeypatch.setattr(api.requests, "request", fake_request)
    assert api.run_workflow("low stock?") == {"workflow_id": "w1"}
    assert sent["method"] == "POST"
    assert sent["url"].endswith("/workflow")
    assert sent["json"] == {"request": "low stock?", "domain": "inventory"}


def test_record_decision_sends_inventory_domain(monkeypatch):
    sent = {}
    monkeypatch.setattr(
        api.requests, "request",
        lambda method, url, timeout=None, **kw: sent.update(url=url, json=kw["json"]) or FakeResponse(200, {"message": "ok"}),
    )
    api.record_decision("w1", "Accept", "")
    assert sent["url"].endswith("/workflow/decision")
    assert sent["json"]["domain"] == "inventory"


def test_workflow_status_filters_to_inventory(monkeypatch):
    sent = {}
    monkeypatch.setattr(
        api.requests, "request",
        lambda method, url, timeout=None, **kw: sent.update(params=kw.get("params")) or FakeResponse(200, {}),
    )
    api.workflow_status()
    assert sent["params"] == {"domain": "inventory"}


def test_unreachable_server_raises_502(monkeypatch):
    def down(*a, **k):
        raise api.requests.ConnectionError("refused")

    monkeypatch.setattr(api.requests, "request", down)
    with pytest.raises(api.MultiAgentError) as exc:
        api.run_workflow("x")
    assert exc.value.status_code == 502


def test_server_error_message_is_passed_through(monkeypatch):
    monkeypatch.setattr(
        api.requests, "request",
        lambda *a, **k: FakeResponse(400, {"error": "A correction note is required for the Correct decision."}),
    )
    with pytest.raises(api.MultiAgentError) as exc:
        api.record_decision("w1", "Correct", "")
    assert exc.value.status_code == 400
    assert "correction note" in exc.value.message


# ---------- routes ----------

def test_workflow_route_validates_input(client):
    assert client.post("/api/multi-agent/workflow", json={}).status_code == 400
    assert client.post("/api/multi-agent/workflow", json={"request": "   "}).status_code == 400
    assert client.post("/api/multi-agent/workflow", json={"request": "x" * 1001}).status_code == 400


def test_workflow_route_forwards_and_returns_json(client, monkeypatch):
    import routes.multi_agent_mode as routes

    monkeypatch.setattr(routes, "run_workflow", lambda r: {"workflow_id": "w9", "domain": "inventory", "echo": r})
    resp = client.post("/api/multi-agent/workflow", json={"request": "  hello  "})
    assert resp.status_code == 200
    assert resp.get_json()["echo"] == "hello"


def test_route_returns_upstream_error_status(client, monkeypatch):
    import routes.multi_agent_mode as routes

    def fail(_):
        raise api.MultiAgentError("shared server down", 502)

    monkeypatch.setattr(routes, "run_workflow", fail)
    resp = client.post("/api/multi-agent/workflow", json={"request": "hi"})
    assert resp.status_code == 502
    assert resp.get_json()["error"] == "shared server down"


def test_mode_header_off_disables_routes(client):
    off = {"X-Multi-Agent-Mode": "off"}
    assert client.post("/api/multi-agent/workflow", json={"request": "hi"}, headers=off).status_code == 403
    assert client.post("/api/multi-agent/decision", json={"workflow_id": "a", "decision": "Accept"}, headers=off).status_code == 403
    assert client.get("/api/multi-agent/status", headers=off).status_code == 403


def test_decision_route_validates_input(client):
    assert client.post("/api/multi-agent/decision", json={"decision": "Accept"}).status_code == 400
    assert client.post("/api/multi-agent/decision", json={"workflow_id": "a"}).status_code == 400
    assert client.post("/api/multi-agent/decision", json={"workflow_id": "a", "decision": "Accept", "note": "n" * 501}).status_code == 400


# ---------- end to end: inventory-service -> real shared server -> inventory agents ----------

def _find_shared_server():
    candidates = [os.getenv("SHARED_SERVER_DIR"),
                  SERVICE_DIR.parent / "multi-agent-server",
                  SERVICE_DIR.parents[1] / "ai-services" / "multi-agent-server"]
    for c in candidates:
        if c and (Path(c) / "app.py").exists() and (Path(c) / "agents" / "inventory_worker_agent.py").exists():
            return Path(c)
    return None


@pytest.mark.skipif(_find_shared_server() is None, reason="shared multi-agent server source not found")
def test_end_to_end_against_real_shared_server(tmp_path, monkeypatch, client):
    server_dir = _find_shared_server()
    # The shared server uses top-level modules named `agents`, `coordinator`, `domains`.
    monkeypatch.syspath_prepend(str(server_dir))
    for name in [m for m in sys.modules if m in ("agents", "coordinator", "domains") or m.startswith("agents.")]:
        monkeypatch.delitem(sys.modules, name)

    import coordinator
    from agents import inventory_planner_agent, inventory_reviewer_agent, inventory_worker_agent as worker

    monkeypatch.setattr(coordinator, "HISTORY_PATH", tmp_path / "h.jsonl")
    monkeypatch.setattr(coordinator, "AUDIT_PATH", tmp_path / "a.jsonl")
    monkeypatch.setattr(worker, "fetch_products", lambda: [
        {"product_id": 2, "name": "Pallet Jacks", "brand": "LoadMaster", "category_name": "Loading Equipment",
         "supplier_name": "Global Machinery Ltd.", "price": 139.49, "quantity": 8, "reorder_level": 15},
        {"product_id": 1, "name": "Barcode Scanners", "brand": "ClickTech", "category_name": "Organisation Tools",
         "supplier_name": "TrackTools Co.", "price": 35.99, "quantity": 120, "reorder_level": 20},
    ])
    for mod in (worker, inventory_planner_agent, inventory_reviewer_agent):
        monkeypatch.setattr(mod, "call_model", lambda *a, **k: "Verdict: Approve")

    spec = importlib.util.spec_from_file_location("e2e_shared_app", server_dir / "app.py")
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)

    server = make_server("127.0.0.1", 0, shared.app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setattr(api, "MULTI_AGENT_SERVER_URL", f"http://127.0.0.1:{server.server_port}")

        wf = client.post("/api/multi-agent/workflow", json={"request": "Which products are low on stock?"})
        assert wf.status_code == 200, wf.get_data(as_text=True)
        body = wf.get_json()
        assert body["domain"] == "inventory"
        products = [e for e in body["worker"]["evidence"] if e["kind"] == "product"]
        assert [p["product_id"] for p in products] == [2]

        bad = client.post("/api/multi-agent/decision",
                          json={"workflow_id": body["workflow_id"], "decision": "Correct"})
        assert bad.status_code == 400
        assert "correction note" in bad.get_json()["error"].lower()

        good = client.post("/api/multi-agent/decision",
                           json={"workflow_id": body["workflow_id"], "decision": "Accept"})
        assert good.status_code == 200

        status = client.get("/api/multi-agent/status").get_json()
        assert status["workflow_count"] == 1
        assert status["latest_workflow"]["human_decision"]["decision"] == "Accept"
    finally:
        server.shutdown()

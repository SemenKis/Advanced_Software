import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "student-4-sam" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

ROUTES_SPEC = importlib.util.spec_from_file_location(
    "student4_multi_agent_test_routes", BACKEND / "htmx_routes.py"
)
htmx_routes = importlib.util.module_from_spec(ROUTES_SPEC)
sys.modules["htmx_routes"] = htmx_routes
ROUTES_SPEC.loader.exec_module(htmx_routes)

APP_SPEC = importlib.util.spec_from_file_location(
    "student4_multi_agent_test_app", BACKEND / "app.py"
)
app_module = importlib.util.module_from_spec(APP_SPEC)
APP_SPEC.loader.exec_module(app_module)
app = app_module.app


def test_transportation_workflow_uses_shared_transportation_domain(monkeypatch):
    calls = []

    def fake_server(method, path, payload=None, timeout=240):
        calls.append((method, path, payload))
        return {
            "domain": "transportation",
            "workflow_id": "workflow-123",
            "planner": {"status": "completed", "output": "Check the shipment."},
            "worker": {
                "status": "completed",
                "output": "Delay is recorded.",
                "evidence": [{"id": 1, "status": "DELAYED"}],
            },
            "reviewer": {"status": "completed", "output": "Evidence supports the response."},
        }, 200

    monkeypatch.setattr(htmx_routes, "_multi_agent_server_response", fake_server)
    response = app.test_client().post(
        "/htmx/multi-agent/workflow",
        data={"request": "Review delayed shipments"},
    )

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Planner" in page and "Worker" in page and "Reviewer" in page
    assert "workflow-123" in page
    assert 'value="Correct"' in page
    assert calls[0][2] == {
        "request": "Review delayed shipments",
        "domain": "transportation",
    }


def test_transportation_correction_requires_note(monkeypatch):
    called = False

    def fake_server(*args, **kwargs):
        nonlocal called
        called = True
        return {"message": "Decision recorded."}, 200

    monkeypatch.setattr(htmx_routes, "_multi_agent_server_response", fake_server)
    response = app.test_client().post(
        "/htmx/multi-agent/decision",
        data={"workflow_id": "workflow-123", "decision": "Correct", "note": ""},
    )

    assert response.status_code == 400
    assert "correction" in response.get_data(as_text=True).lower()
    assert not called


def test_transportation_human_decision_is_forwarded(monkeypatch):
    calls = []

    def fake_server(method, path, payload=None, timeout=240):
        calls.append((method, path, payload))
        return {"message": "Decision recorded."}, 200

    monkeypatch.setattr(htmx_routes, "_multi_agent_server_response", fake_server)
    response = app.test_client().post(
        "/htmx/multi-agent/decision",
        data={
            "workflow_id": "workflow-123",
            "decision": "Correct",
            "note": "Recheck the arrival estimate.",
        },
    )

    assert response.status_code == 200
    assert "Correct" in response.get_data(as_text=True)
    assert calls[0][2]["domain"] == "transportation"

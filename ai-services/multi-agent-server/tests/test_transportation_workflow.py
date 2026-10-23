import sys
import importlib.util
import threading
import json
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

import coordinator
from agents import transportation_worker_agent as worker

APP_SPEC = importlib.util.spec_from_file_location(
    "shared_multi_agent_test_app", SERVER_ROOT / "app.py"
)
app_module = importlib.util.module_from_spec(APP_SPEC)
APP_SPEC.loader.exec_module(app_module)
app = app_module.app


def test_planner_flows_to_worker_and_reviewer_failure_is_recorded(tmp_path, monkeypatch):
    monkeypatch.setattr(coordinator, "HISTORY_PATH", tmp_path / "history.jsonl")
    monkeypatch.setattr(coordinator, "AUDIT_PATH", tmp_path / "audit.jsonl")
    plan = {"status": "completed", "output": "Inspect shipment 3"}

    def work(request, received_plan):
        assert received_plan == plan
        return {"status": "completed", "output": "Checked", "evidence": [{"id": 3}]}

    def review(request, received_plan, worker_result):
        assert received_plan == plan
        assert worker_result["evidence"] == [{"id": 3}]
        raise ConnectionError("Reviewer unavailable")

    monkeypatch.setitem(coordinator.DOMAINS, "transportation", {
        "plan": lambda request: plan, "work": work, "review": review,
        "worker_uses_plan": True,
    })
    result = coordinator.run_workflow("Review shipment 3", "transportation")
    assert result["worker"]["output"] == "Checked"
    assert result["reviewer"]["status"] == "error"
    assert result["human_decision"]["status"] == "pending"
    assert coordinator.workflow_status("transportation")["workflow_count"] == 1


def test_reviewer_timeout_does_not_block_workflow(tmp_path, monkeypatch):
    monkeypatch.setattr(coordinator, "HISTORY_PATH", tmp_path / "history.jsonl")
    monkeypatch.setattr(coordinator, "AUDIT_PATH", tmp_path / "audit.jsonl")
    monkeypatch.setattr(coordinator, "STEP_TIMEOUT", 0.05)
    release = threading.Event()

    def review(*args):
        release.wait(2)
        return {"status": "completed", "output": "Late result"}

    monkeypatch.setitem(coordinator.DOMAINS, "transportation", {
        "plan": lambda request: {"status": "completed", "output": "Plan"},
        "work": lambda request: {"status": "completed", "output": "Work"},
        "review": review,
    })
    try:
        result = coordinator.run_workflow("Review shipments", "transportation")
        assert result["reviewer"]["status"] == "timeout"
        assert not release.is_set()
    finally:
        release.set()


def test_transportation_domain_runs_transport_agents_and_persists_correction(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(coordinator, "HISTORY_PATH", tmp_path / "history.jsonl")
    monkeypatch.setattr(coordinator, "AUDIT_PATH", tmp_path / "audit.jsonl")
    monkeypatch.setitem(
        coordinator.DOMAINS,
        "transportation",
        {
            "plan": lambda request: {
                "status": "completed", "agent": "planner", "output": request,
            },
            "work": lambda request: {
                "status": "completed", "agent": "worker", "output": "Evidence checked.",
                "evidence": [{"id": 3}],
            },
            "review": lambda request, plan, result: {
                "status": "completed", "agent": "reviewer", "output": "Needs review.",
            },
        },
    )

    client = app.test_client()
    response = client.post(
        "/workflow",
        json={"request": "Review shipment 3", "domain": "transportation"},
    )

    assert response.status_code == 200
    workflow = response.get_json()
    assert workflow["domain"] == "transportation"
    assert workflow["worker"]["evidence"] == [{"id": 3}]
    assert workflow["human_decision"]["status"] == "pending"
    assert workflow["human_decision"]["allowed_values"] == [
        "Accept", "Partially Accept", "Correct", "Reject",
    ]

    missing_note = client.post(
        "/workflow/decision",
        json={
            "workflow_id": workflow["workflow_id"],
            "decision": "Correct",
            "domain": "transportation",
        },
    )
    assert missing_note.status_code == 400

    decision = client.post(
        "/workflow/decision",
        json={
            "workflow_id": workflow["workflow_id"],
            "decision": "Correct",
            "note": "Use the latest delay value.",
            "domain": "transportation",
        },
    )
    assert decision.status_code == 200

    status = client.get("/workflow/status?domain=transportation").get_json()
    saved = status["latest_workflow"]["human_decision"]
    assert saved["status"] == "decided"
    assert saved["decision"] == "Correct"
    assert saved["note"] == "Use the latest delay value."

    duplicate = client.post(
        "/workflow/decision",
        json={
            "workflow_id": workflow["workflow_id"],
            "decision": "Accept",
            "domain": "transportation",
        },
    )
    assert duplicate.status_code == 400


def test_transportation_api_rejects_unknown_domain():
    response = app.test_client().post(
        "/workflow",
        json={"request": "Review shipments", "domain": "unknown"},
    )
    assert response.status_code == 400


def test_worker_receives_plan_and_reviewer_receives_evidence(monkeypatch):
    from agents import transportation_reviewer_agent as reviewer

    prompts = []

    def model(model, system_prompt, user_prompt, **kwargs):
        prompts.append(user_prompt)
        return "Review required"

    monkeypatch.setattr(worker, "fetch_shipments", lambda: [{"id": 3, "status": "DELAYED"}])
    monkeypatch.setattr(worker, "call_model", model)
    monkeypatch.setattr(reviewer, "call_model", model)
    plan = {"status": "completed", "output": "Check recorded arrival time"}
    result = worker.generate_output("Review shipment 3", plan)
    reviewer.review_output("Review shipment 3", plan, result)
    assert plan["output"] in prompts[0]
    assert plan["output"] in prompts[1]
    assert '"id": 3' in prompts[1]
    assert result["output"] in prompts[1]


def test_shared_review_uses_only_transportation_history(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "transportation_review_loop", SERVER_ROOT.parents[1] / "agentic-review" / "review_loop.py"
    )
    loop = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loop)
    monkeypatch.setattr(loop, "REPO_ROOT", tmp_path)
    server_dir = tmp_path / "ai-services" / "multi-agent-server"
    server_dir.mkdir(parents=True)
    rows = [
        {"domain": "transportation", "workflow_id": "transport-proof"},
        {"domain": "orders", "workflow_id": "unrelated-order-proof"},
    ]
    (server_dir / "workflow_history.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows), encoding="utf-8"
    )
    evidence = loop.collect_multi_agent_evidence("student-4-sam")
    assert "transport-proof" in evidence
    assert "unrelated-order-proof" not in evidence
    assert "Total workflows recorded: 1" in evidence


def test_transportation_worker_filters_evidence_and_avoids_model_for_no_match(
    monkeypatch,
):
    shipments = [
        {
            "id": 1,
            "origin": "Sydney",
            "destination": "Melbourne",
            "status": "DELAYED",
            "delay_minutes": 25,
        },
        {
            "id": 2,
            "origin": "Brisbane",
            "destination": "Perth",
            "status": "IN_TRANSIT",
            "delay_minutes": 0,
        },
    ]
    monkeypatch.setattr(worker, "fetch_shipments", lambda: shipments)
    monkeypatch.setattr(
        worker, "call_model",
        lambda *args, **kwargs: "Shipment 1 is delayed by 25 minutes.",
    )

    result = worker.generate_output("Review shipment 1")
    assert result["filters"]["shipment_id"] == 1
    assert result["evidence_count"] == 1
    assert result["evidence"][0]["id"] == 1

    def unexpected_model_call(*args, **kwargs):
        raise AssertionError("A model call is not needed when there are no matches")

    monkeypatch.setattr(worker, "call_model", unexpected_model_call)
    no_match = worker.generate_output("Review shipment 99")
    assert no_match["status"] == "completed"
    assert no_match["evidence"] == []
    assert "No shipments match" in no_match["output"]

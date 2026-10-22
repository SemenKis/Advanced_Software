import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from agents.planner_agent import plan_workflow
from agents.reviewer_agent import review_output
from agents.worker_agent import generate_output

APP_DIR = Path(__file__).resolve().parent
HISTORY_PATH = APP_DIR / "workflow_history.jsonl"
AUDIT_PATH = APP_DIR / "coordination_audit.jsonl"
STEP_TIMEOUT = float(os.getenv("AGENT_STEP_TIMEOUT_SECONDS", "30"))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _append(path, record):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _audit(workflow_id, event, detail=""):
    _append(AUDIT_PATH, {"workflow_id": workflow_id, "timestamp": _now(), "event": event, "detail": detail})


def _timeout_result(agent):
    return {"status": "timeout", "agent": agent, "output": f"{agent} timed out.", "evidence": []}


def run_workflow(user_request):
    workflow_id = str(uuid.uuid4())
    started = time.time()
    _audit(workflow_id, "workflow_started", user_request)

    executor = ThreadPoolExecutor(max_workers=2)
    planner_future = executor.submit(plan_workflow, user_request)
    worker_future = executor.submit(generate_output, user_request)

    try:
        planner_result = planner_future.result(timeout=STEP_TIMEOUT)
    except Exception:
        planner_result = _timeout_result("planner")
    _audit(workflow_id, "planner_done", planner_result["status"])

    try:
        worker_result = worker_future.result(timeout=STEP_TIMEOUT)
    except Exception:
        worker_result = _timeout_result("worker")
    _audit(workflow_id, "worker_done", worker_result["status"])
    executor.shutdown(wait=False)

    reviewer_result = review_output(user_request, planner_result, worker_result)
    _audit(workflow_id, "reviewer_done", reviewer_result["status"])

    result = {
        "workflow_id": workflow_id,
        "timestamp": _now(),
        "duration_ms": int((time.time() - started) * 1000),
        "user_request": user_request,
        "participating_agents": ["planner", "worker", "reviewer"],
        "planner": planner_result,
        "worker": worker_result,
        "reviewer": reviewer_result,
        "human_decision": {
            "required": True,
            "status": "pending",
            "allowed_values": ["Accept", "Partially Accept", "Reject"],
        },
    }
    _append(HISTORY_PATH, result)
    _audit(workflow_id, "workflow_completed", "human decision pending")
    return result


def workflow_status():
    workflows = []
    if HISTORY_PATH.exists():
        lines = HISTORY_PATH.read_text(encoding="utf-8").strip().splitlines()
        workflows = [json.loads(line) for line in lines if line.strip()]
    audit_count = 0
    if AUDIT_PATH.exists():
        audit_count = len(AUDIT_PATH.read_text(encoding="utf-8").strip().splitlines())
    return {
        "workflow_count": len(workflows),
        "audit_event_count": audit_count,
        "latest_workflow": workflows[-1] if workflows else None,
    }


ALLOWED_DECISIONS = ["Accept", "Partially Accept", "Reject"]


def record_decision(workflow_id, decision, note=""):
    if not workflow_id:
        return False, "Field 'workflow_id' is required."
    if decision not in ALLOWED_DECISIONS:
        return False, "Decision must be one of: " + ", ".join(ALLOWED_DECISIONS)
    _audit(workflow_id, "human_decision", json.dumps({"decision": decision, "note": note}))
    return True, "Decision recorded."

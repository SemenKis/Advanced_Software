import json
import os
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime, timezone
from pathlib import Path

from domains import DEFAULT_DOMAIN, DOMAINS

APP_DIR = Path(__file__).resolve().parent
HISTORY_PATH = APP_DIR / "workflow_history.jsonl"
AUDIT_PATH = APP_DIR / "coordination_audit.jsonl"
STEP_TIMEOUT = float(os.getenv("AGENT_STEP_TIMEOUT_SECONDS", "30"))
HISTORY_LOCK = threading.RLock()
ALLOWED_DECISIONS = ["Accept", "Partially Accept", "Correct", "Reject"]


def _now():
    return datetime.now(timezone.utc).isoformat()


def _append(path, record):
    with HISTORY_LOCK:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")


def _audit(workflow_id, event, detail="", domain=None):
    record = {
        "workflow_id": workflow_id,
        "timestamp": _now(),
        "event": event,
        "detail": detail,
    }
    if domain:
        record["domain"] = domain
    _append(AUDIT_PATH, record)


def _timeout_result(agent):
    return {"status": "timeout", "agent": agent, "output": f"{agent} timed out.", "evidence": []}


def _run_agent(role, function, *args):
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(function, *args)
    try:
        result = future.result(timeout=STEP_TIMEOUT)
        if not isinstance(result, dict) or not {"status", "output"} <= result.keys():
            raise ValueError("Invalid agent response")
        return result
    except TimeoutError:
        return _timeout_result(role)
    except Exception as exc:
        return {
            "status": "error", "agent": role, "evidence": [],
            "output": f"{role} failed ({type(exc).__name__}). Manual review required.",
        }
    finally:
        # Running model calls retain their own HTTP timeout; do not block this request.
        executor.shutdown(wait=False, cancel_futures=True)


def run_workflow(user_request, domain=DEFAULT_DOMAIN):
    if domain not in DOMAINS:
        raise ValueError(f"Unsupported workflow domain: {domain}")
    agents = DOMAINS[domain]
    workflow_id = str(uuid.uuid4())
    started = time.time()
    _audit(workflow_id, "workflow_started", user_request, domain)

    planner_result = _run_agent("planner", agents["plan"], user_request)
    _audit(workflow_id, "planner_done", planner_result["status"], domain)

    # Existing domains retain their one-argument Worker contract.
    worker_args = (user_request, planner_result) if agents.get("worker_uses_plan") else (user_request,)
    worker_result = _run_agent("worker", agents["work"], *worker_args)
    _audit(workflow_id, "worker_done", worker_result["status"], domain)
    reviewer_result = _run_agent(
        "reviewer", agents["review"], user_request, planner_result, worker_result
    )
    _audit(workflow_id, "reviewer_done", reviewer_result["status"], domain)

    result = {
        "workflow_id": workflow_id,
        "domain": domain,
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
            "allowed_values": ALLOWED_DECISIONS,
        },
    }
    _append(HISTORY_PATH, result)
    _audit(workflow_id, "workflow_completed", "human decision pending", domain)
    return result


def _read_workflows():
    if HISTORY_PATH.exists():
        lines = HISTORY_PATH.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]
    return []


def workflow_status(domain=None):
    with HISTORY_LOCK:
        workflows = _read_workflows()
        if domain:
            workflows = [
                workflow for workflow in workflows
                if workflow.get("domain", DEFAULT_DOMAIN) == domain
            ]
        audit_count = 0
        if AUDIT_PATH.exists():
            audit_records = [
                json.loads(line)
                for line in AUDIT_PATH.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            audit_count = sum(
                1 for record in audit_records
                if not domain or record.get("domain", DEFAULT_DOMAIN) == domain
            )
    return {
        "domain": domain,
        "workflow_count": len(workflows),
        "audit_event_count": audit_count,
        "latest_workflow": workflows[-1] if workflows else None,
    }


def record_decision(workflow_id, decision, note="", domain=None):
    if not workflow_id:
        return False, "Field 'workflow_id' is required."
    if decision not in ALLOWED_DECISIONS:
        return False, "Decision must be one of: " + ", ".join(ALLOWED_DECISIONS)
    note = note.strip() if isinstance(note, str) else ""
    if decision == "Correct" and not note:
        return False, "A correction note is required for the Correct decision."

    with HISTORY_LOCK:
        workflows = _read_workflows()
        workflow = next(
            (item for item in workflows if item.get("workflow_id") == workflow_id),
            None,
        )
        if workflow is None:
            return False, "Workflow not found."
        workflow_domain = workflow.get("domain", DEFAULT_DOMAIN)
        if domain and workflow_domain != domain:
            return False, f"Workflow belongs to domain '{workflow_domain}'."

        human_decision = workflow.get("human_decision", {})
        if human_decision.get("status") != "pending":
            return False, "A human decision has already been recorded."

        human_decision.update({
            "status": "decided",
            "decision": decision,
            "note": note,
            "decided_at": _now(),
        })
        workflow["human_decision"] = human_decision

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=HISTORY_PATH.parent,
                prefix="workflow_history.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                for item in workflows:
                    temp_file.write(json.dumps(item) + "\n")
            temp_path.replace(HISTORY_PATH)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()

        _audit(
            workflow_id,
            "human_decision",
            json.dumps({"decision": decision, "note": note}),
            workflow_domain,
        )
    return True, "Decision recorded."
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


def _read_jsonl(path):
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _domain_of(record):
    # Records written before domains existed belong to the warehouse
    return record.get("domain", DEFAULT_DOMAIN)


def _audit(workflow_id, event, detail="", domain=DEFAULT_DOMAIN):
    _append(
        AUDIT_PATH,
        {"workflow_id": workflow_id, "domain": domain, "timestamp": _now(), "event": event, "detail": detail},
    )


def _timeout_result(agent):
    return {"status": "timeout", "agent": agent, "output": f"{agent} timed out.", "evidence": []}


def run_workflow(user_request, domain=DEFAULT_DOMAIN):
    if domain not in DOMAINS:
        raise ValueError(f"Unknown domain: {domain}")
    agents = DOMAINS[domain]

    workflow_id = str(uuid.uuid4())
    started = time.time()
    _audit(workflow_id, "workflow_started", user_request, domain)

    executor = ThreadPoolExecutor(max_workers=2)
    planner_future = executor.submit(agents["plan"], user_request)
    worker_future = executor.submit(agents["work"], user_request)

    try:
        planner_result = planner_future.result(timeout=STEP_TIMEOUT)
    except Exception:
        planner_result = _timeout_result("planner")
    _audit(workflow_id, "planner_done", planner_result["status"], domain)

    try:
        worker_result = worker_future.result(timeout=STEP_TIMEOUT)
    except Exception:
        worker_result = _timeout_result("worker")
    _audit(workflow_id, "worker_done", worker_result["status"], domain)
    executor.shutdown(wait=False)

    reviewer_result = agents["review"](user_request, planner_result, worker_result)
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


def workflow_status(domain=None):
    """With a domain, counts and the latest workflow cover only that domain."""
    workflows = _read_jsonl(HISTORY_PATH)
    audit = _read_jsonl(AUDIT_PATH)
    if domain:
        workflows = [w for w in workflows if _domain_of(w) == domain]
        audit = [a for a in audit if _domain_of(a) == domain]
    return {
        "domain": domain,
        "workflow_count": len(workflows),
        "audit_event_count": len(audit),
        "latest_workflow": workflows[-1] if workflows else None,
    }


ALLOWED_DECISIONS = ["Accept", "Partially Accept", "Reject"]


def record_decision(workflow_id, decision, note="", domain=DEFAULT_DOMAIN):
    if not workflow_id:
        return False, "Field 'workflow_id' is required."
    if decision not in ALLOWED_DECISIONS:
        return False, "Decision must be one of: " + ", ".join(ALLOWED_DECISIONS)
    _audit(workflow_id, "human_decision", json.dumps({"decision": decision, "note": note}), domain)
    return True, "Decision recorded."

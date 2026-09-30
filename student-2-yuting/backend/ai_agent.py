from curses import raw

import requests
import os
import json
import re
from datetime import datetime


OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:0.5b")
LOG_PATH = os.environ.get("LOG_PATH", "agent_loop_log.json1")

SYSTEM_PROMPT = (
    "You are an AI warehouse management assistant. You will be given a list of "
    "pending shipping tasks and the current load of storage zones. "
    "Respond with ONLY valid JSON: a list of objects like " 
    '{"task_id": <int>, "priority": <int 1-10, 10=highest>, "reason": "<short string>“}. '
    "Prioritise tasks linked to zones whose current_load is close to capacity, "
    "to avoid bottlenecks."
)


def _log(step, payload):
    entry = {"timestamp": datetime.utcnow().isoformat(), "step": step, "data": payload}
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[AGENT LOG] {step}: {json.dumps(payload)[:300]}")
    return entry



def plan(db_service_url):
    tasks = requests.get(f"{db_service_url}/api/shipping-tasks").json()
    locations = requests.get(f"{db_service_url}/api/storage-locations").json()
    pending = [t for t in tasks if t["status"] in ("pending", "in_progress")]
    context = {"pending_tasks": pending, "storage_locations": locations}
    _log("PLAN", {"pending_tasks_count": len(pending), "location_count": len(locations)})
    return context


def act(context):
    prompt = (
        f"{SYSTEM_PROMPT}\n\nPending tasks:\n"
        f"{json.dumps(context['pending_tasks'])}\n\n"
        f"Storage zone loads:\n{json.dumps(context['storage_locations'])}\n\n"
        "JSON:"
    )
    raw = ""
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=60,
        )
        raw = resp.json().get("response", "")
    except Exception as e:
        _log("ACT_ERROR", {"error": str(e)})
    _log("ACT", {"model": OLLAMA_MODEL, "raw_response": raw[:500]})
    return raw



def observe(raw_response, context):
    valid_ids = {t["id"] for t in context["pending_tasks"]}
    parsed=[]
    try:
        match = re.search(r"\[.*\]", raw_response, re.DOTALL)
        candidate = json.loads(match.group(0)) if match else json.loads(raw_response)
        for entry in candidate:
            if entry.get("task_id") in valid_ids and 1 <= int(entry.get("priority", 0)) <= 10:
                parsed.append(entry)
    except Exception as e:
        _log("OBSERVE_PARSE_FAILED", {"error": str(e)})
    _log("OBSERVE", {"parsed_count": len(parsed), "expected_count": len(valid_ids)})
    return parsed



def adapt(parsed, context, db_service_url):
    if not parsed:
        _log("ADAPT_FALLBACK", {"reason": "LLM output unusable - using rule-based fallback"})
        loads = {
            loc["id"]: loc["current_load"] / max(loc["capacity"],1)
            for loc in context["storage_locations"]
        }
        for t in context["pending_tasks"]:
            score = loads.get(t.get("packing_list_id"), 0.5)
            priority = min(10, max(1, round(score * 10)))
            parsed.append({"task_id": t["id"], "priority": priority, "reason": "Rule-based fallback based on storage load"})

    updates = []
    for entry in parsed:
        r = requests.put(
            f"{db_service_url}/api/shipping-tasks/{entry['task_id']}",
            json={"priority": entry["priority"]},
        )
        updates.append({"task_id": entry["task_id"], "status_code": r.status_code})
    _log("ADAPT", {"updates": updates})
    return updates


def run_prioritisation_loop(db_service_url):
    context = plan(db_service_url)
    raw = act(context)
    parsed = observe(raw, context)
    updates = adapt(parsed, context, db_service_url)
    return {
        "plan": {"pending_tasks": len(context["pending_tasks"])},
        "act_raw": raw[:500],
        "observe_parsed": parsed,
        "adapt_updates": updates,

    }
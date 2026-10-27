import os
import re
from pathlib import Path

import requests

from agents.llm import call_model

APP_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = APP_DIR / "prompts" / "transportation_worker_prompt.txt"
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
TRANSPORTATION_API_URL = os.getenv(
    "TRANSPORTATION_API_URL", "http://localhost:5004/api/shipments"
)
MAX_SHIPMENT_ROWS = 20
SHIPMENT_ID_PATTERN = re.compile(
    r"\bshipment(?:\s+id)?[\s#:-]*(\d+)\b", re.IGNORECASE
)
SHIPMENT_FIELDS = (
    "id",
    "origin",
    "destination",
    "status",
    "driver",
    "vehicle",
    "departure_date",
    "estimated_arrival",
    "delay_minutes",
)


def extract_shipment_id(user_request):
    match = SHIPMENT_ID_PATTERN.search(user_request)
    return int(match.group(1)) if match else None


def fetch_shipments():
    response = requests.get(TRANSPORTATION_API_URL, timeout=5)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Transportation API did not return a list of shipments")
    if any(not isinstance(row, dict) for row in data):
        raise ValueError("Transportation API returned an invalid shipment record")
    return data


def find_statuses(user_request, shipments):
    known = {str(row.get("status") or "").strip().lower() for row in shipments} - {""}
    text = user_request.lower()
    return [status for status in sorted(known) if re.search(rf"\b{re.escape(status)}\b", text)]


def filter_shipments(shipments, shipment_id=None, statuses=None):
    selected = shipments
    if shipment_id is not None:
        selected = [row for row in selected if row.get("id") == shipment_id]
    if statuses:
        selected = [
            row for row in selected
            if str(row.get("status") or "").strip().lower() in statuses
        ]
    return selected


def build_evidence(shipments):
    return [
        {"kind": "shipment", **{field: shipment.get(field) for field in SHIPMENT_FIELDS}}
        for shipment in shipments[:MAX_SHIPMENT_ROWS]
    ]


def format_evidence(evidence, hidden_rows=0):
    lines = [
        (
            f"Shipment {row['id']}: {row['origin']} to {row['destination']}; "
            f"status {row['status']}; delay {row['delay_minutes']} minutes; "
            f"driver {row['driver'] or 'not recorded'}; "
            f"vehicle {row['vehicle'] or 'not recorded'}; "
            f"departure {row['departure_date'] or 'not recorded'}; "
            f"estimated arrival {row['estimated_arrival'] or 'not recorded'}"
        )
        for row in evidence
    ]
    if hidden_rows:
        lines.append(f"{hidden_rows} additional matching shipments are not listed.")
    return "\n".join(lines) or "No matching shipment records."


def generate_output(user_request, planner_result=None):
    shipment_id = extract_shipment_id(user_request)
    try:
        shipments = fetch_shipments()
        statuses = find_statuses(user_request, shipments)
        selected = filter_shipments(shipments, shipment_id, statuses)
    except (requests.RequestException, ValueError) as exc:
        return {
            "status": f"error ({type(exc).__name__})",
            "agent": "worker",
            "model": MODEL,
            "filters": {"shipment_id": shipment_id, "statuses": []},
            "evidence_count": 0,
            "evidence": [],
            "output": "Could not read shipment data from the Transportation API.",
            "human_approval_required": True,
        }

    evidence = build_evidence(selected)
    hidden_rows = max(len(selected) - len(evidence), 0)
    filters = {"shipment_id": shipment_id, "statuses": statuses}
    if not selected:
        return {
            "status": "completed",
            "agent": "worker",
            "model": "n/a (no model call)",
            "filters": filters,
            "evidence_count": 0,
            "evidence": [],
            "output": "No shipments match the requested ID or status.",
            "human_approval_required": True,
        }

    evidence_text = format_evidence(evidence, hidden_rows)
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    user_prompt = (
        f"Request: {user_request}\n"
        f"Planner guidance: {(planner_result or {}).get('output', 'Use the shipment evidence.')}\n"
        f"Filters applied: shipment ID {shipment_id or 'all'}, "
        f"statuses {', '.join(statuses) or 'all'}\n\n"
        f"Shipment evidence:\n{evidence_text}\n\n"
        f"Matching shipment count: {len(selected)}"
    )
    try:
        output = call_model(MODEL, system_prompt, user_prompt, max_tokens=220)
        status = "completed"
    except Exception as exc:
        output = "Model unavailable. Evidence summary:\n" + evidence_text
        status = f"fallback ({type(exc).__name__})"

    return {
        "status": status,
        "agent": "worker",
        "model": MODEL,
        "filters": filters,
        "evidence_count": len(evidence),
        "evidence": evidence,
        "hidden_rows": hidden_rows,
        "output": output,
        "human_approval_required": True,
    }

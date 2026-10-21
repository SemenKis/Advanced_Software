import os
import re
from pathlib import Path

import requests

from agents.llm import call_model

APP_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = APP_DIR / "prompts" / "worker_prompt.txt"
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
WAREHOUSE_API_URL = os.getenv(
    "WAREHOUSE_API_URL", "http://localhost:5020/api/storage-locations"
)


def extract_zone(user_request):
    match = re.search(r"\bzone[\s-]+([A-Za-z])\b", user_request, re.IGNORECASE)
    return f"Zone-{match.group(1).upper()}" if match else None


def fetch_locations():
    response = requests.get(WAREHOUSE_API_URL, timeout=5)
    response.raise_for_status()
    return response.json()


def build_evidence(locations, zone=None):
    zones = {}
    for row in locations:
        name = row.get("zone_name", "Unknown")
        if zone and name != zone:
            continue
        item = zones.setdefault(name, {"zone": name, "bins": 0, "capacity": 0, "current_load": 0})
        item["bins"] += 1
        item["capacity"] += row.get("capacity", 0)
        item["current_load"] += row.get("current_load", 0)
    for item in zones.values():
        cap = item["capacity"]
        item["utilisation_pct"] = round(item["current_load"] / cap * 100, 1) if cap else 0
        item["near_capacity"] = item["utilisation_pct"] >= 80
    return sorted(zones.values(), key=lambda z: z["utilisation_pct"], reverse=True)


def format_evidence(evidence):
    return "\n".join(
        f"{e['zone']}: {e['bins']} bins, load {e['current_load']}/{e['capacity']} ({e['utilisation_pct']}%) - {'NEAR CAPACITY' if e['near_capacity'] else 'normal'}"
        for e in evidence
    )


def generate_output(user_request):
    zone = extract_zone(user_request)
    try:
        evidence = build_evidence(fetch_locations(), zone)
    except Exception as exc:
        return {
            "status": f"error ({type(exc).__name__})",
            "agent": "worker",
            "model": MODEL,
            "zone": zone,
            "evidence_count": 0,
            "evidence": [],
            "output": "Could not read warehouse data from the Warehouse API.",
            "human_approval_required": True,
        }

    evidence_text = format_evidence(evidence)
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    near = [e["zone"] for e in evidence if e["near_capacity"]]
    user_prompt = f"Request: {user_request}\n\nEvidence:\n{evidence_text}\n\nZones near capacity (80% or more): {', '.join(near) or 'none'}"
    try:
        output = call_model(MODEL, system_prompt, user_prompt, max_tokens=180)
        status = "completed"
    except Exception as exc:
        output = "Model unavailable. Evidence summary:\n" + evidence_text
        status = f"fallback ({type(exc).__name__})"

    return {
        "status": status,
        "agent": "worker",
        "model": MODEL,
        "zone": zone,
        "evidence_count": len(evidence),
        "evidence": evidence,
        "output": output,
        "human_approval_required": True,
    }

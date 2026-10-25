import json
import os
from pathlib import Path

from agents.llm import call_model

APP_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = APP_DIR / "prompts" / "transportation_reviewer_prompt.txt"
MODEL = os.getenv("OLLAMA_REVIEW_MODEL", "llama3.1:8b")


def review_output(user_request, planner_result, worker_result):
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    user_prompt = (
        f"User request:\n{user_request}\n\n"
        f"Planner steps:\n{planner_result.get('output', '')}\n\n"
        f"Shipment evidence:\n{json.dumps(worker_result.get('evidence', []))}\n\n"
        f"Worker analysis:\n{worker_result.get('output', '')}"
    )
    try:
        output = call_model(MODEL, system_prompt, user_prompt, max_tokens=180)
        status = "completed"
    except Exception as exc:
        output = (
            "Reviewer unavailable. Manual review required. "
            "Verify every recommendation against the shipment evidence."
        )
        status = f"fallback ({type(exc).__name__})"
    return {
        "status": status,
        "agent": "reviewer",
        "model": MODEL,
        "output": output,
    }

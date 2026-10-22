import os
from pathlib import Path

from agents.llm import call_model

APP_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = APP_DIR / "prompts" / "order_planner_prompt.txt"
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

FALLBACK_PLAN = (
    "1. Fetch the current orders. "
    "2. Filter by order id or status if the request names one. "
    "3. Summarise the matching orders by status and total amount, then recommend an action."
)


def plan_workflow(user_request):
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    try:
        output = call_model(MODEL, system_prompt, user_request, max_tokens=180)
        status = "completed"
    except Exception as exc:
        output = FALLBACK_PLAN
        status = f"fallback ({type(exc).__name__})"
    return {
        "status": status,
        "agent": "planner",
        "model": MODEL,
        "output": output,
    }
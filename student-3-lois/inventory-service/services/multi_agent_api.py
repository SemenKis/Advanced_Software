import os

import requests

MULTI_AGENT_SERVER_URL = os.getenv(
    "MULTI_AGENT_SERVER_URL", "http://host.docker.internal:5005"
).rstrip("/")
MULTI_AGENT_DOMAIN = "inventory"
MULTI_AGENT_ENABLED = os.getenv("MULTI_AGENT_ENABLED", "true").strip().lower() in (
    "1", "true", "yes", "on",
)

try:
    # Planner, Worker and Reviewer each get up to AGENT_STEP_TIMEOUT_SECONDS on
    # the shared server, so the HTTP timeout has to cover all three.
    MULTI_AGENT_TIMEOUT_SECONDS = int(os.getenv("MULTI_AGENT_TIMEOUT_SECONDS", "150"))
except ValueError:
    MULTI_AGENT_TIMEOUT_SECONDS = 150

MAX_REQUEST_CHARS = 1000  # limit enforced by the shared server
MAX_NOTE_CHARS = 500      # limit enforced by the shared server


class MultiAgentError(Exception):
    """Raised when the shared server is unreachable or rejects a request."""

    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def multi_agent_mode_is_enabled(req) -> bool:
    if not MULTI_AGENT_ENABLED:
        return False
    return req.headers.get("X-Multi-Agent-Mode", "on").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _call(method, path, **kwargs):
    url = f"{MULTI_AGENT_SERVER_URL}{path}"
    try:
        response = requests.request(
            method, url, timeout=MULTI_AGENT_TIMEOUT_SECONDS, **kwargs
        )
    except requests.RequestException as exc:
        raise MultiAgentError(
            f"Could not reach the shared multi-agent server at {MULTI_AGENT_SERVER_URL}: {exc}",
            502,
        ) from exc

    try:
        data = response.json()
    except ValueError:
        data = {}

    if response.status_code >= 400:
        message = data.get("error") or data.get("message") or f"Request failed ({response.status_code})"
        raise MultiAgentError(message, response.status_code)
    return data


def health():
    return _call("GET", "/health")


def run_workflow(user_request: str):
    """Run the inventory Planner -> Worker -> Reviewer workflow."""
    return _call(
        "POST",
        "/workflow",
        json={"request": user_request, "domain": MULTI_AGENT_DOMAIN},
    )


def record_decision(workflow_id: str, decision: str, note: str = ""):
    """Record the human decision for a workflow (Accept / Partially Accept / Correct / Reject)."""
    return _call(
        "POST",
        "/workflow/decision",
        json={
            "workflow_id": workflow_id,
            "decision": decision,
            "note": note,
            "domain": MULTI_AGENT_DOMAIN,
        },
    )


def workflow_status():
    """History summary for the inventory domain only."""
    return _call("GET", "/workflow/status", params={"domain": MULTI_AGENT_DOMAIN})
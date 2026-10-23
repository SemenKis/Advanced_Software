import importlib.util
import json
import os
from html import escape
from pathlib import Path

import requests
from flask import Blueprint, request

from database import get_connection
from agentic_loop import analyse_shipment


htmx_transportation = Blueprint(
    "htmx_transportation",
    __name__
)

MULTI_AGENT_SERVER_URL = os.getenv(
    "MULTI_AGENT_SERVER_URL", "http://127.0.0.1:5005"
).rstrip("/")
MULTI_AGENT_ENABLED = os.getenv(
    "MULTI_AGENT_ENABLED", "true"
).strip().lower() in {"1", "true", "yes", "on"}
MULTI_AGENT_ALLOWED_DECISIONS = {"Accept", "Correct", "Reject"}
MAX_MULTI_AGENT_REQUEST_LENGTH = 1000
MAX_MULTI_AGENT_NOTE_LENGTH = 500


VALID_STATUSES = {
    "PLANNED",
    "READY_FOR_DISPATCH",
    "IN_TRANSIT",
    "DELAYED",
    "DELIVERED",
    "CANCELLED"
}


def _multi_agent_status_html(status, detail):
    return f"""
    <div class="status-card">
        <span class="label">Multi-Agent Server</span>
        <strong>{escape(status)}</strong>
        <p>{escape(detail)}</p>
    </div>
    """


def _multi_agent_server_response(method, path, payload=None, timeout=240):
    response = requests.request(
        method,
        f"{MULTI_AGENT_SERVER_URL}{path}",
        json=payload,
        timeout=timeout,
    )
    try:
        result = response.json()
    except ValueError:
        result = {"error": response.text or "Multi-Agent server returned invalid JSON."}
    if not isinstance(result, dict):
        result = {"error": "Multi-Agent server returned an unexpected response format."}
    return result, response.status_code


def _render_multi_agent_workflow(result):
    workflow_id = str(result.get("workflow_id", ""))
    agent_html = ""
    for role in ("planner", "worker", "reviewer"):
        agent = result.get(role) or {}
        agent_html += (
            f"<h4>{escape(role.title())} - {escape(str(agent.get('status', 'unknown')))}</h4>"
            f"<pre>{escape(str(agent.get('output', 'No output returned.')))}</pre>"
        )
        evidence = agent.get("evidence")
        if role == "worker" and evidence:
            agent_html += (
                "<details><summary>Shipment evidence</summary><pre>"
                + escape(json.dumps(evidence, indent=2, default=str))
                + "</pre></details>"
            )

    return f"""
    <section class="agent-results">
        <p><strong>Workflow:</strong> {escape(workflow_id)}</p>
        {agent_html}
        <h4>Human review required</h4>
        <p>Recommendations do not change shipment records. Review and record
        your approval, correction, or rejection.</p>
        <form
            hx-post="http://localhost:5004/htmx/multi-agent/decision"
            hx-target="#multi-agent-result"
            hx-swap="innerHTML">
            <input type="hidden" name="workflow_id" value="{escape(workflow_id)}">
            <label for="multi-agent-note">Correction or reason</label>
            <textarea id="multi-agent-note" name="note" maxlength="{MAX_MULTI_AGENT_NOTE_LENGTH}"
                placeholder="Required when selecting Correct"></textarea>
            <div class="agent-decision-buttons">
                <button type="submit" name="decision" value="Accept">Approve</button>
                <button type="submit" name="decision" value="Correct">Correct</button>
                <button type="submit" name="decision" value="Reject">Reject</button>
            </div>
        </form>
    </section>
    """


@htmx_transportation.get("/htmx/multi-agent/status")
def get_multi_agent_status():
    if not MULTI_AGENT_ENABLED:
        return _multi_agent_status_html("Disabled", "Multi-Agent mode is disabled.")
    try:
        payload, status_code = _multi_agent_server_response(
            "GET", "/health", timeout=5
        )
    except requests.RequestException:
        return _multi_agent_status_html(
            "Unavailable",
            "Start the shared Multi-Agent Server locally on port 5005.",
        )
    if status_code == 200 and payload.get("status") == "ok":
        return _multi_agent_status_html("Ready", "Transportation Planner, Worker, and Reviewer are available.")
    return _multi_agent_status_html(
        "Unavailable", "The Multi-Agent Server returned an unexpected health response."
    ), 502


@htmx_transportation.post("/htmx/multi-agent/workflow")
def run_multi_agent_workflow():
    if not MULTI_AGENT_ENABLED:
        return "<p>Multi-Agent mode is disabled.</p>", 403
    data = request.get_json(silent=True) or request.form
    if not hasattr(data, "get"):
        return "<p>Request body must be a JSON object or form.</p>", 400
    user_request = data.get("request", "")
    if not isinstance(user_request, str) or not user_request.strip():
        return "<p>A request is required.</p>", 400
    user_request = user_request.strip()
    if len(user_request) > MAX_MULTI_AGENT_REQUEST_LENGTH:
        return (
            f"<p>Request must be {MAX_MULTI_AGENT_REQUEST_LENGTH} characters or fewer.</p>",
            400,
        )

    try:
        result, status_code = _multi_agent_server_response(
            "POST",
            "/workflow",
            {"request": user_request, "domain": "transportation"},
        )
    except requests.RequestException:
        return (
            "<p>Could not reach the shared Multi-Agent Server. "
            "Start it locally on port 5005 and try again.</p>",
            503,
        )
    if status_code >= 500:
        return "<p>The shared Multi-Agent Server failed to complete the workflow.</p>", 502
    if status_code >= 400:
        return f"<p>{escape(str(result.get('error', 'Workflow request was rejected.')))}</p>", status_code
    if result.get("domain") != "transportation":
        return "<p>The Multi-Agent Server returned a workflow for the wrong domain.</p>", 502
    if not result.get("workflow_id"):
        return "<p>The Multi-Agent Server returned a workflow without an ID.</p>", 502
    return _render_multi_agent_workflow(result)


@htmx_transportation.post("/htmx/multi-agent/decision")
def record_multi_agent_decision():
    if not MULTI_AGENT_ENABLED:
        return "<p>Multi-Agent mode is disabled.</p>", 403
    workflow_id = request.form.get("workflow_id", "").strip()
    decision = request.form.get("decision", "").strip()
    note = request.form.get("note", "").strip()
    if not workflow_id:
        return "<p>Workflow ID is required.</p>", 400
    if decision not in MULTI_AGENT_ALLOWED_DECISIONS:
        return "<p>Select Approve, Correct, or Reject.</p>", 400
    if decision == "Correct" and not note:
        return "<p>Enter a correction before selecting Correct.</p>", 400
    if len(note) > MAX_MULTI_AGENT_NOTE_LENGTH:
        return (
            f"<p>Correction or reason must be {MAX_MULTI_AGENT_NOTE_LENGTH} characters or fewer.</p>",
            400,
        )

    try:
        result, status_code = _multi_agent_server_response(
            "POST",
            "/workflow/decision",
            {
                "workflow_id": workflow_id,
                "decision": decision,
                "note": note,
                "domain": "transportation",
            },
            timeout=10,
        )
    except requests.RequestException:
        return "<p>Could not reach the shared Multi-Agent Server to record the decision.</p>", 503
    if status_code >= 400:
        return f"<p>{escape(str(result.get('message') or result.get('error') or 'Decision was rejected.'))}</p>", status_code
    return (
        f"<p>Human decision recorded: <strong>{escape(decision)}</strong>"
        + (f" - {escape(note)}" if note else "")
        + "</p>"
    )


def _mcp_status_html(label: str, status: str, detail: str):
    return f"""
    <div class="status-card">
        <span class="label">{escape(label)}</span>
        <strong>{escape(status)}</strong>
        <p>{escape(detail)}</p>
    </div>
    """


def _load_mcp_tools_module():
    env_path = os.getenv("MCP_TOOLS_PATH")
    candidates = []

    if env_path:
        candidates.append(Path(env_path).expanduser())

    repo_root = Path(__file__).resolve().parents[2]
    candidates.extend([
        repo_root / "mcp-server" / "tools.py",
        Path("/workspace/mcp-server/tools.py"),
        Path("/app/mcp-server/tools.py"),
    ])

    for tools_path in candidates:
        if tools_path.exists():
            spec = importlib.util.spec_from_file_location("student4_mcp_tools", str(tools_path))
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load MCP tools from {tools_path}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

    raise FileNotFoundError(
        "MCP tools not found. Set MCP_TOOLS_PATH to the root mcp-server/tools.py file. "
        f"Checked: {', '.join(str(p) for p in candidates)}"
    )


def _get_mcp_status():
    try:
        tools = _load_mcp_tools_module()
        result = tools.get_shipment_count()
        if isinstance(result, dict) and "shipment_count" in result:
            return "Connected", "Transportation tools are available for shipment lookup and operational checks."

        return "Disconnected", "MCP tool call returned no shipment data."
    except Exception as exc:
        return "Disconnected", f"MCP check failed: {exc}"


def _get_rag_status():
    try:
        response = requests.get("http://localhost:5003/health", timeout=5)
        if response.status_code == 200:
            payload = response.json()
            if payload.get("status") == "ok":
                return "Ready", "Operational context and shipment intelligence are available for AI-assisted analysis."
        return "Unavailable", "RAG server responded unexpectedly."
    except Exception as exc:
        return "Unavailable", f"RAG check failed: {exc}"


def render_shipments():
    connection = get_connection()

    shipments = connection.execute(
        """
        SELECT *
        FROM shipments
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    html = """
    <table border="1" cellpadding="8">
        <thead>
            <tr>
                <th>ID</th>
                <th>Origin</th>
                <th>Destination</th>
                <th>Status</th>
                <th>Driver</th>
                <th>Vehicle</th>
                <th>Delay</th>
                <th>Actions</th>
            </tr>
        </thead>

        <tbody>
    """

    for shipment in shipments:
        shipment_id = shipment["id"]

        html += f"""
        <tr id="shipment-{shipment_id}">
            <td>{shipment_id}</td>

            <td>
                {escape(shipment["origin"])}
            </td>

            <td>
                {escape(shipment["destination"])}
            </td>

            <td>
                {escape(shipment["status"])}
            </td>

            <td>
                {escape(shipment["driver"] or "")}
            </td>

            <td>
                {escape(shipment["vehicle"] or "")}
            </td>

            <td>
                {shipment["delay_minutes"]} min
            </td>

            <td>

                <button
                    hx-get="http://localhost:5004/htmx/shipments/{shipment_id}/edit"
                    hx-target="#shipment-{shipment_id}"
                    hx-swap="outerHTML">
                    Edit
                </button>

                <button
                    hx-delete="http://localhost:5004/htmx/shipments/{shipment_id}"
                    hx-target="#shipment-table"
                    hx-swap="innerHTML"
                    hx-confirm="Delete this shipment?">
                    Delete
                </button>

                <button
                    hx-post="http://localhost:5004/htmx/shipments/{shipment_id}/analyse"
                    hx-target="#ai-result"
                    hx-swap="innerHTML">
                    Analyse with Qwen
                </button>

            </td>
        </tr>
        """

    html += """
        </tbody>
    </table>
    """

    return html


@htmx_transportation.get(
    "/htmx/mcp-status"
)
def get_mcp_status():
    status, detail = _get_mcp_status()
    return _mcp_status_html("MCP status", status, detail)


@htmx_transportation.get(
    "/htmx/rag-status"
)
def get_rag_status():
    status, detail = _get_rag_status()
    return _mcp_status_html("RAG status", status, detail)


@htmx_transportation.post(
    "/htmx/mcp/check-shipment"
)
def run_mcp_tool():
    raw_shipment_id = request.form.get("shipment_id", "").strip()

    try:
        tools = _load_mcp_tools_module()

        if raw_shipment_id == "":
            payload = tools.get_shipment_count()
            return f"<pre>{escape(json.dumps(payload, indent=2, default=str))}</pre>"

        try:
            shipment_id = int(raw_shipment_id)
        except ValueError:
            return "<pre>Shipment ID must be a number.</pre>", 400

        try:
            payload = tools.get_shipment_status(shipment_id)
        except requests.exceptions.HTTPError as exc:
            if "404" in str(exc):
                return "<pre>Shipment not found.</pre>", 404
            return f"<pre>{escape(str(exc))}</pre>", 502

    except Exception as exc:
        return f"<pre>{escape(str(exc))}</pre>", 500

    return f"<pre>{escape(json.dumps(payload, indent=2, default=str))}</pre>"


@htmx_transportation.post(
    "/htmx/rag/answer"
)
def ask_rag_question():
    query = request.form.get("query", "").strip()
    if not query:
        return "<pre>Query is required.</pre>", 400

    try:
        response = requests.post(
            "http://localhost:5003/answer",
            json={"query": query, "k": 5, "caller": "student"},
            timeout=10
        )
        payload = response.json() if response.content else {"status": "empty"}
    except Exception as exc:
        return f"<pre>{escape(str(exc))}</pre>", 502

    if payload.get("status") != "success":
        error_text = payload.get("error") or payload.get("answer") or "RAG request failed."
        return f"<pre>{escape(error_text)}</pre>", 400 if response.status_code >= 400 else 200

    answer = payload.get("answer") or "No answer available."
    citations = payload.get("citations") or []
    confidence = payload.get("confidence_category") or "Unknown"

    evidence_html = ""
    if citations:
        evidence_html = """
        <details>
            <summary>Evidence ({count})</summary>
            <pre>{json}</pre>
        </details>
        """.format(
            count=len(citations),
            json=escape(json.dumps(citations, indent=2, default=str))
        )

    return f"""
    <div class="tool-result">
        <h4>Answer</h4>
        <p>{escape(answer)}</p>
        <div class="meta">Confidence: {escape(str(confidence))}</div>
        {evidence_html}
    </div>
    """, 200


@htmx_transportation.get(
    "/htmx/shipments"
)
def get_shipments():
    return render_shipments()


@htmx_transportation.post(
    "/htmx/shipments"
)
def create_shipment():
    origin = request.form.get(
        "origin",
        ""
    ).strip()

    destination = request.form.get(
        "destination",
        ""
    ).strip()

    status = request.form.get(
        "status",
        "PLANNED"
    ).upper()

    driver = request.form.get(
        "driver",
        ""
    ).strip()

    vehicle = request.form.get(
        "vehicle",
        ""
    ).strip()

    try:
        delay_minutes = int(
            request.form.get(
                "delay_minutes",
                0
            )
        )
    except ValueError:
        delay_minutes = 0

    if not origin or not destination:
        return (
            "<p>Origin and destination are required.</p>",
            400
        )

    if status not in VALID_STATUSES:
        return (
            "<p>Invalid status.</p>",
            400
        )

    connection = get_connection()

    connection.execute(
        """
        INSERT INTO shipments (
            origin,
            destination,
            status,
            driver,
            vehicle,
            delay_minutes
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            origin,
            destination,
            status,
            driver,
            vehicle,
            delay_minutes
        )
    )

    connection.commit()
    connection.close()

    return render_shipments()


@htmx_transportation.get(
    "/htmx/shipments/<int:shipment_id>/edit"
)
def edit_shipment(shipment_id):
    connection = get_connection()

    shipment = connection.execute(
        """
        SELECT *
        FROM shipments
        WHERE id = ?
        """,
        (shipment_id,)
    ).fetchone()

    connection.close()

    if shipment is None:
        return (
            "<tr><td>Shipment not found</td></tr>",
            404
        )

    return f"""
    <tr id="shipment-{shipment_id}">

        <td>
            {shipment_id}
        </td>

        <td>
            <input
                name="origin"
                value="{escape(shipment['origin'])}">
        </td>

        <td>
            <input
                name="destination"
                value="{escape(shipment['destination'])}">
        </td>

        <td>
            <select name="status">

                <option
                    value="PLANNED"
                    {"selected" if shipment["status"] == "PLANNED" else ""}>
                    PLANNED
                </option>

                <option
                    value="READY_FOR_DISPATCH"
                    {"selected" if shipment["status"] == "READY_FOR_DISPATCH" else ""}>
                    READY_FOR_DISPATCH
                </option>

                <option
                    value="IN_TRANSIT"
                    {"selected" if shipment["status"] == "IN_TRANSIT" else ""}>
                    IN_TRANSIT
                </option>

                <option
                    value="DELAYED"
                    {"selected" if shipment["status"] == "DELAYED" else ""}>
                    DELAYED
                </option>

                <option
                    value="DELIVERED"
                    {"selected" if shipment["status"] == "DELIVERED" else ""}>
                    DELIVERED
                </option>

                <option
                    value="CANCELLED"
                    {"selected" if shipment["status"] == "CANCELLED" else ""}>
                    CANCELLED
                </option>

            </select>
        </td>

        <td>
            <input
                name="driver"
                value="{escape(shipment["driver"] or "")}">
        </td>

        <td>
            <input
                name="vehicle"
                value="{escape(shipment["vehicle"] or "")}">
        </td>

        <td>
            <input
                type="number"
                name="delay_minutes"
                min="0"
                value="{shipment["delay_minutes"]}">
        </td>

        <td>

            <button
                hx-put="http://localhost:5004/htmx/shipments/{shipment_id}"
                hx-include="#shipment-{shipment_id} input, #shipment-{shipment_id} select"
                hx-target="#shipment-table"
                hx-swap="innerHTML">
                Save
            </button>

            <button
                hx-get="http://localhost:5004/htmx/shipments"
                hx-target="#shipment-table"
                hx-swap="innerHTML">
                Cancel
            </button>

        </td>

    </tr>
    """


@htmx_transportation.put(
    "/htmx/shipments/<int:shipment_id>"
)
def update_shipment(shipment_id):
    origin = request.form.get(
        "origin",
        ""
    ).strip()

    destination = request.form.get(
        "destination",
        ""
    ).strip()

    status = request.form.get(
        "status",
        "PLANNED"
    ).upper()

    driver = request.form.get(
        "driver",
        ""
    ).strip()

    vehicle = request.form.get(
        "vehicle",
        ""
    ).strip()

    try:
        delay_minutes = int(
            request.form.get(
                "delay_minutes",
                0
            )
        )
    except ValueError:
        delay_minutes = 0

    connection = get_connection()

    existing = connection.execute(
        """
        SELECT id
        FROM shipments
        WHERE id = ?
        """,
        (shipment_id,)
    ).fetchone()

    if existing is None:
        connection.close()

        return (
            "<p>Shipment not found.</p>",
            404
        )

    connection.execute(
        """
        UPDATE shipments
        SET
            origin = ?,
            destination = ?,
            status = ?,
            driver = ?,
            vehicle = ?,
            delay_minutes = ?
        WHERE id = ?
        """,
        (
            origin,
            destination,
            status,
            driver,
            vehicle,
            delay_minutes,
            shipment_id
        )
    )

    connection.commit()
    connection.close()

    return render_shipments()


@htmx_transportation.delete(
    "/htmx/shipments/<int:shipment_id>"
)
def delete_shipment(shipment_id):
    connection = get_connection()

    connection.execute(
        """
        DELETE FROM shipments
        WHERE id = ?
        """,
        (shipment_id,)
    )

    connection.commit()
    connection.close()

    return render_shipments()


@htmx_transportation.post(
    "/htmx/shipments/<int:shipment_id>/analyse"
)
def analyse_transportation(shipment_id):
    try:
        result = analyse_shipment(
            shipment_id
        )

    except RuntimeError as error:
        return (
            f"<p>AI service unavailable: {escape(str(error))}</p>",
            503
        )

    if result is None:
        return (
            "<p>Shipment not found.</p>",
            404
        )

    observation = result["observe"]

    return f"""
    <div>

        <h3>PLAN</h3>
        <p>
            {escape(result["plan"])}
        </p>

        <h3>ACT</h3>
        <p>
            {escape(result["act"])}
        </p>

        <h3>OBSERVE</h3>

        <p>
            Shipment:
            {observation["shipment_id"]}
        </p>

        <p>
            Route:
            {escape(observation["origin"])}
            →
            {escape(observation["destination"])}
        </p>

        <p>
            Status:
            {escape(observation["status"])}
        </p>

        <p>
            Delay:
            {observation["delay_minutes"]} minutes
        </p>

        <h3>ADAPT — QWEN</h3>

        <pre>{escape(result["adapt"])}</pre>

    </div>
    """
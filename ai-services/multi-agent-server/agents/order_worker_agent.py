import os
import re
from pathlib import Path

import requests

from agents.llm import call_model

APP_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = APP_DIR / "prompts" / "order_worker_prompt.txt"
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

# The order-database container publishes its port 5002 on host port 5012.
# This server runs on the host, so it reads the order data through that port.
ORDER_API_URL = os.getenv("ORDER_API_URL", "http://localhost:5012/orders")

ORDER_FIELDS = (
    "order_id",
    "order_name",
    "order_address",
    "order_status",
    "product_name",
    "quantity",
    "total_amount",
)

# Keeps the evidence small enough for the 0.5b model and the reviewer prompt.
MAX_ORDER_ROWS = 15

ORDER_ID_PATTERN = re.compile(r"\border(?:\s+id)?[\s#:-]*(\d+)\b", re.IGNORECASE)


def extract_order_id(user_request):
    match = ORDER_ID_PATTERN.search(user_request)
    return int(match.group(1)) if match else None


def find_statuses(user_request, orders):
    """Statuses are read from the data, so new statuses work without code changes."""
    known = {str(o.get("order_status") or "").strip().lower() for o in orders} - {""}
    text = user_request.lower()
    return [s for s in sorted(known) if re.search(rf"\b{re.escape(s)}\b", text)]


def fetch_orders():
    response = requests.get(ORDER_API_URL, timeout=5)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Order API did not return a list of orders")
    return data


def filter_orders(orders, order_id=None, statuses=None):
    selected = orders
    if order_id is not None:
        selected = [o for o in selected if o.get("order_id") == order_id]
    if statuses:
        selected = [
            o for o in selected
            if str(o.get("order_status") or "").strip().lower() in statuses
        ]
    return selected


def build_evidence(selected):
    """Returns (evidence, hidden_rows). Totals cover every selected order."""
    summary = {}
    for order in selected:
        status = str(order.get("order_status") or "unknown").strip().lower()
        item = summary.setdefault(
            status,
            {"kind": "status_summary", "order_status": status, "order_count": 0, "total_amount": 0.0},
        )
        item["order_count"] += 1
        item["total_amount"] += float(order.get("total_amount") or 0)

    for item in summary.values():
        item["total_amount"] = round(item["total_amount"], 2)

    summary_rows = sorted(summary.values(), key=lambda r: (-r["order_count"], r["order_status"]))
    order_rows = [
        {"kind": "order", **{field: order.get(field) for field in ORDER_FIELDS}}
        for order in selected[:MAX_ORDER_ROWS]
    ]
    return summary_rows + order_rows, max(len(selected) - MAX_ORDER_ROWS, 0)


def _money(value):
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def format_evidence(evidence, hidden_rows=0):
    lines = []
    for row in evidence:
        if row.get("kind") == "status_summary":
            lines.append(
                f"Status {row['order_status']}: {row['order_count']} orders, "
                f"total amount {_money(row['total_amount'])}"
            )
        else:
            lines.append(
                f"Order {row['order_id']}: {row['order_name']}, {row['order_address']}, "
                f"status {row['order_status']}, {row['product_name']} x{row['quantity']}, "
                f"amount {_money(row['total_amount'])}"
            )
    if hidden_rows:
        lines.append(f"({hidden_rows} more matching orders are not listed)")
    return "\n".join(lines)


def describe_filters(order_id, statuses):
    parts = []
    if order_id is not None:
        parts.append(f"order id {order_id}")
    if statuses:
        parts.append("status " + " or ".join(statuses))
    return ", ".join(parts) or "none (all orders)"


def generate_output(user_request):
    order_id = extract_order_id(user_request)
    statuses = []
    try:
        orders = fetch_orders()
        statuses = find_statuses(user_request, orders)
        selected = filter_orders(orders, order_id, statuses)
        evidence, hidden_rows = build_evidence(selected)
    except Exception as exc:
        return {
            "status": f"error ({type(exc).__name__})",
            "agent": "worker",
            "model": MODEL,
            "filters": {"order_id": order_id, "statuses": statuses},
            "evidence_count": 0,
            "evidence": [],
            "output": "Could not read order data from the Order API.",
            "human_approval_required": True,
        }

    filters = {"order_id": order_id, "statuses": statuses}

    if not selected:
        # Nothing to summarise, so skip the model rather than let it guess.
        return {
            "status": "completed",
            "agent": "worker",
            "model": "n/a (no model call)",
            "filters": filters,
            "evidence_count": 0,
            "evidence": [],
            "output": f"No orders match this request (filters: {describe_filters(order_id, statuses)}).",
            "human_approval_required": True,
        }

    evidence_text = format_evidence(evidence, hidden_rows)
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    user_prompt = (
        f"Request: {user_request}\n\n"
        f"Filters applied: {describe_filters(order_id, statuses)}\n\n"
        f"Evidence:\n{evidence_text}\n\n"
        f"Matching orders: {len(selected)}"
    )
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
        "filters": filters,
        "evidence_count": len(evidence),
        "evidence": evidence,
        "output": output,
        "human_approval_required": True,
    }
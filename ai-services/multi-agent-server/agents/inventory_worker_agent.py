import os
import re
from pathlib import Path

import requests

from agents.llm import call_model

APP_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = APP_DIR / "prompts" / "inventory_worker_prompt.txt"
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

# The inventory database container publishes its port 5002 on host port 5002.
# This shared server runs on the host, so it reads inventory data through that
# port. Read-only: only GET requests are ever made.
INVENTORY_API_URL = os.getenv("INVENTORY_API_URL", "http://localhost:5002/products")

PRODUCT_FIELDS = (
    "product_id",
    "name",
    "brand",
    "category_name",
    "supplier_name",
    "price",
    "quantity",
    "reorder_level",
)

# Keeps the evidence small enough for the 0.5b model and the reviewer prompt.
MAX_PRODUCT_ROWS = 20

PRODUCT_ID_PATTERN = re.compile(r"\bproduct(?:\s+id)?[\s#:-]*(\d+)\b", re.IGNORECASE)
LOW_STOCK_PATTERN = re.compile(
    r"\b("
    r"low(?:\s+(?:on|in))?[\s-]*(?:stock|inventory)"  # low stock / low on stock / low in stock
    r"|(?:stock|inventory)\s+(?:is\s+|levels?\s+(?:are\s+)?)?low"  # stock is low / stock levels low
    r"|(?:below|under|at)\s+(?:the\s+)?reorder"  # below reorder level
    r"|reorder\w*|restock\w*|shortage\w*|running\s+low|running\s+out"
    r"|out\s+of\s+stock"
    r")\b",
    re.IGNORECASE,
)


def extract_product_id(user_request):
    match = PRODUCT_ID_PATTERN.search(user_request)
    return int(match.group(1)) if match else None


def wants_low_stock(user_request):
    return bool(LOW_STOCK_PATTERN.search(user_request))


def fetch_products():
    response = requests.get(INVENTORY_API_URL, timeout=5)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Inventory API did not return a list of products")
    if any(not isinstance(row, dict) for row in data):
        raise ValueError("Inventory API returned an invalid product record")
    return data


def find_names(user_request, products, field):
    """Categories/suppliers are read from the data, so new ones work without code changes."""
    known = {str(p.get(field) or "").strip() for p in products} - {""}
    text = user_request.lower()
    return sorted(
        n.lower() for n in known
        if re.search(rf"(?<!\w){re.escape(n.lower())}(?!\w)", text)
    )


def is_low(product):
    try:
        return int(product.get("quantity") or 0) <= int(product.get("reorder_level") or 0)
    except (TypeError, ValueError):
        return False


def filter_products(products, product_id=None, categories=None, suppliers=None, low_only=False):
    selected = products
    if product_id is not None:
        selected = [p for p in selected if p.get("product_id") == product_id]
    if categories:
        selected = [
            p for p in selected
            if str(p.get("category_name") or "").strip().lower() in categories
        ]
    if suppliers:
        selected = [
            p for p in selected
            if str(p.get("supplier_name") or "").strip().lower() in suppliers
        ]
    if low_only:
        selected = [p for p in selected if is_low(p)]
    return selected


def build_evidence(selected):
    """Returns (evidence, hidden_rows). The summary covers every selected product."""
    low = [p for p in selected if is_low(p)]
    stock_value = sum(
        float(p.get("price") or 0) * int(p.get("quantity") or 0) for p in selected
    )
    summary = {
        "kind": "stock_summary",
        "product_count": len(selected),
        "low_stock_count": len(low),
        "total_units": sum(int(p.get("quantity") or 0) for p in selected),
        "total_stock_value": round(stock_value, 2),
    }
    # Low-stock products first so they survive the row cap.
    ordered = sorted(selected, key=lambda p: (not is_low(p), p.get("name") or ""))
    rows = [
        {
            "kind": "product",
            **{field: p.get(field) for field in PRODUCT_FIELDS},
            "low_stock": is_low(p),
        }
        for p in ordered[:MAX_PRODUCT_ROWS]
    ]
    return [summary] + rows, max(len(selected) - MAX_PRODUCT_ROWS, 0)


def _money(value):
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def format_evidence(evidence, hidden_rows=0):
    lines = []
    for row in evidence:
        if row.get("kind") == "stock_summary":
            lines.append(
                f"Summary: {row['product_count']} products, {row['low_stock_count']} low on stock, "
                f"{row['total_units']} units, total stock value {_money(row['total_stock_value'])}"
            )
        else:
            flag = "LOW STOCK" if row.get("low_stock") else "OK"
            lines.append(
                f"Product {row['product_id']}: {row['name']} ({row['brand'] or 'no brand'}), "
                f"category {row['category_name']}, supplier {row['supplier_name']}, "
                f"price {_money(row['price'])}, quantity {row['quantity']}, "
                f"reorder level {row['reorder_level']} - {flag}"
            )
    if hidden_rows:
        lines.append(f"({hidden_rows} more matching products are not listed)")
    return "\n".join(lines)


def describe_filters(product_id, categories, suppliers, low_only):
    parts = []
    if product_id is not None:
        parts.append(f"product id {product_id}")
    if categories:
        parts.append("category " + " or ".join(categories))
    if suppliers:
        parts.append("supplier " + " or ".join(suppliers))
    if low_only:
        parts.append("low stock only")
    return ", ".join(parts) or "none (all products)"


def generate_output(user_request, planner_result=None):
    product_id = extract_product_id(user_request)
    low_only = wants_low_stock(user_request)
    categories, suppliers = [], []
    try:
        products = fetch_products()
        categories = find_names(user_request, products, "category_name")
        suppliers = find_names(user_request, products, "supplier_name")
        selected = filter_products(products, product_id, categories, suppliers, low_only)
        evidence, hidden_rows = build_evidence(selected)
    except (requests.RequestException, ValueError) as exc:
        return {
            "status": f"error ({type(exc).__name__})",
            "agent": "worker",
            "model": MODEL,
            "filters": {"product_id": product_id, "categories": categories,
                        "suppliers": suppliers, "low_stock_only": low_only},
            "evidence_count": 0,
            "evidence": [],
            "output": "Could not read product data from the Inventory API.",
            "human_approval_required": True,
        }

    filters = {"product_id": product_id, "categories": categories,
               "suppliers": suppliers, "low_stock_only": low_only}

    if not selected:
        # Nothing to summarise, so skip the model rather than let it guess.
        return {
            "status": "completed",
            "agent": "worker",
            "model": "n/a (no model call)",
            "filters": filters,
            "evidence_count": 0,
            "evidence": [],
            "output": "No products match this request (filters: "
                      f"{describe_filters(product_id, categories, suppliers, low_only)}).",
            "human_approval_required": True,
        }

    evidence_text = format_evidence(evidence, hidden_rows)
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    user_prompt = (
        f"Request: {user_request}\n"
        f"Planner guidance: {(planner_result or {}).get('output', 'Use the inventory evidence.')}\n"
        f"Filters applied: {describe_filters(product_id, categories, suppliers, low_only)}\n\n"
        f"Evidence:\n{evidence_text}\n\n"
        f"Matching products: {len(selected)}"
    )
    try:
        output = call_model(MODEL, system_prompt, user_prompt, max_tokens=200)
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
import os
from pathlib import Path

import requests

from agents.llm import call_model

APP_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = APP_DIR / "prompts" / "worker_prompt.txt"
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
INVENTORY_API_URL = os.getenv(
    "INVENTORY_API_URL", "http://localhost:5001/api/multi-agent/inventory"
)


def fetch_products():
    response = requests.get(INVENTORY_API_URL, timeout=10)
    response.raise_for_status()
    payload = response.json()
    return payload.get("products", payload) if isinstance(payload, dict) else payload


def build_evidence(products):
    evidence = []
    for product in products:
        quantity = int(product.get("quantity", 0))
        reorder_level = int(product.get("reorder_level", 0))
        evidence.append({
            "product_id": product.get("product_id"),
            "name": product.get("name", "Unknown product"),
            "category": product.get("category_name", "Unknown"),
            "supplier": product.get("supplier_name", "Unknown"),
            "quantity": quantity,
            "reorder_level": reorder_level,
            "price": product.get("price"),
            "low_stock": quantity <= reorder_level,
            "reorder_shortfall": max(reorder_level - quantity, 0),
        })
    return sorted(evidence, key=lambda item: (not item["low_stock"], item["quantity"]))


def format_evidence(evidence):
    if not evidence:
        return "No products were returned by the inventory service."
    return "\n".join(
        f"{item['name']} (ID {item['product_id']}): quantity={item['quantity']}, "
        f"reorder_level={item['reorder_level']}, category={item['category']}, "
        f"supplier={item['supplier']}, status={'LOW STOCK' if item['low_stock'] else 'normal'}"
        for item in evidence
    )


def generate_output(user_request):
    try:
        evidence = build_evidence(fetch_products())
    except Exception as exc:
        return {
            "status": f"error ({type(exc).__name__})",
            "agent": "worker",
            "model": MODEL,
            "evidence_count": 0,
            "evidence": [],
            "output": "Could not read inventory data from the Inventory API.",
            "human_approval_required": True,
        }

    evidence_text = format_evidence(evidence)
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    low_stock = [item["name"] for item in evidence if item["low_stock"]]
    user_prompt = (
        f"Request: {user_request}\n\nInventory evidence:\n{evidence_text}\n\n"
        f"Products at or below reorder level: {', '.join(low_stock) or 'none'}"
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
        "evidence_count": len(evidence),
        "evidence": evidence,
        "output": output,
        "human_approval_required": True,
    }

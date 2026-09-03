import requests
from flask import Blueprint, request

from services.database_api import get_low_stock_products, get_products
from services.llm_client import OLLAMA_MODEL, create_chat_completion
from services.prompt_loader import load_prompt

ai_mode_bp = Blueprint("ai_mode", __name__)


@ai_mode_bp.post("/ask")
def ask_local_agent():
    """Simple AI-mode: Frontend -> Backend/API -> Ollama -> LLM, no grounding."""
    question = request.form.get("question", "").strip()
    if not question:
        return "<p>Question is required.</p>", 400
    try:
        answer = create_chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a concise inventory management assistant. "
                        "Answer in one short paragraph unless asked otherwise."
                    ),
                },
                {"role": "user", "content": question},
            ],
            max_tokens=200,
            temperature=0.2,
            model=OLLAMA_MODEL,
        )
        return f"<p>{answer}</p>", 200
    except Exception as exc:
        return (
            "<p>Local AI agent request failed. "
            "Check that Ollama is running and the model is installed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@ai_mode_bp.post("/ask-with-context")
def ask_with_context():
    """
    Grounded AI-mode.
    Plan: the question needs current product data as context.
    Act: fetch live products from the database-service.
    Observe: inject that evidence into the prompt.
    Adapt: the LLM answers using only that real evidence.
    """
    question = request.form.get("question", "").strip()
    if not question:
        return "<p>Question is required.</p>", 400
    try:
        # Act - gather live evidence
        products = get_products()
        evidence_lines = [
            f"- {p['name']} (brand: {p.get('brand') or 'n/a'}, category: {p['category_name']}, "
            f"supplier: {p['supplier_name']}, price: ${p['price']:.2f}, qty: {p['quantity']}, "
            f"reorder level: {p['reorder_level']})"
            for p in products
        ]
        evidence = "\n".join(evidence_lines) if evidence_lines else "No products in inventory."

        system_prompt = load_prompt("system_prompt.txt")
        task_prompt = load_prompt("task_prompt.txt")

        final_prompt = f"""{task_prompt}

Inventory Evidence:
{evidence}

User Question:
{question}
"""
        answer = create_chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": final_prompt},
            ],
            max_tokens=300,
            temperature=0.2,
        )
        return f"<p>{answer}</p>", 200
    except requests.RequestException as exc:
        return f"<p>Could not fetch inventory evidence.</p><pre>{exc}</pre>", 503
    except Exception as exc:
        return f"<p>Context-aware request failed.</p><pre>{exc}</pre>", 503


@ai_mode_bp.post("/recommend")
def recommend():
    """
    AI product recommendation, grounded in real stock/reorder-level/supplier data.
    Plan -> Act -> Observe -> Adapt applied specifically to reorder decisions.
    """
    try:
        # Act - gather evidence: low stock first, fall back to full snapshot
        low_stock = get_low_stock_products()
        products = low_stock if low_stock else get_products()

        evidence_lines = [
            f"- {p['name']}: qty={p['quantity']}, reorder_level={p['reorder_level']}, "
            f"supplier={p['supplier_name']}, category={p['category_name']}"
            for p in products
        ]
        evidence = "\n".join(evidence_lines) if evidence_lines else "No products in inventory."

        system_prompt = load_prompt("system_prompt.txt")
        recommend_prompt = load_prompt("recommend_prompt.txt")

        final_prompt = f"""{recommend_prompt}

Inventory Evidence:
{evidence}
"""
        answer = create_chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": final_prompt},
            ],
            max_tokens=250,
            temperature=0.2,
        )
        return f"<pre>{answer}</pre>", 200
    except requests.RequestException as exc:
        return f"<p>Could not fetch inventory evidence.</p><pre>{exc}</pre>", 503
    except Exception as exc:
        return f"<p>Recommendation request failed.</p><pre>{exc}</pre>", 503

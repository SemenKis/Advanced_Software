import os
from datetime import datetime, timezone

import requests

DATABASE_SERVICE_URL = os.getenv("INVENTORY_DATABASE_SERVICE_URL", "http://localhost:5002")
SOURCE_PREFIX = "inventory"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_chunks() -> list[dict]:
    chunks: list[dict] = []
    try:
        products = requests.get(f"{DATABASE_SERVICE_URL}/products", timeout=10).json()
        low_stock = requests.get(f"{DATABASE_SERVICE_URL}/products/low-stock", timeout=10).json()
    except Exception as exc:
        return [{
            "chunk_id": f"{SOURCE_PREFIX}_unreachable",
            "source_id": f"{SOURCE_PREFIX}-database-service",
            "authority_tier": "tier_1",
            "text": f"Inventory database unreachable: {exc}",
            "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "reachable": False},
            "indexed_at": _now_iso(),
        }]

    chunks.append({
        "chunk_id": f"{SOURCE_PREFIX}_product_count",
        "source_id": f"{SOURCE_PREFIX}-database-service:/products",
        "authority_tier": "tier_1",
        "text": f"Total product count in inventory is {len(products)}.",
        "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "metric": "count"},
        "indexed_at": _now_iso(),
    })

    for p in products:
        chunks.append({
            "chunk_id": f"{SOURCE_PREFIX}_product_{p.get('product_id')}",
            "source_id": f"{SOURCE_PREFIX}-database-service:/products",
            "authority_tier": "tier_1",
            "text": (
                f"Inventory product record: name={p.get('name', 'unknown')}, brand={p.get('brand') or 'n/a'}, "
                f"category={p.get('category_name', 'unknown')}, supplier={p.get('supplier_name', 'unknown')}, "
                f"price={p.get('price', 'n/a')}, quantity={p.get('quantity', 'n/a')}, "
                f"reorder_level={p.get('reorder_level', 'n/a')}."
            ),
            "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "table": "products"},
            "indexed_at": _now_iso(),
        })

    if low_stock:
        summary = "; ".join(f"{p['name']} (qty {p['quantity']}, reorder level {p['reorder_level']})" for p in low_stock)
        text = f"Inventory products at or below their reorder level: {summary}."
    else:
        text = "No inventory products are currently at or below their reorder level."

    chunks.append({
        "chunk_id": f"{SOURCE_PREFIX}_low_stock_summary",
        "source_id": f"{SOURCE_PREFIX}-database-service:/products/low-stock",
        "authority_tier": "tier_1",
        "text": text,
        "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "metric": "low_stock"},
        "indexed_at": _now_iso(),
    })

    return chunks

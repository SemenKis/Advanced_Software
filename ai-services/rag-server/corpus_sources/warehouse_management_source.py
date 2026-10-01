import os
from datetime import datetime, timezone

import requests

DATABASE_SERVICE_URL = os.getenv("WAREHOUSE_DATABASE_SERVICE_URL", "http://localhost:5020")
SOURCE_PREFIX = "warehouse"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_chunks() -> list[dict]:
    """Called once per refresh_corpus() by the shared rag_pipeline.py.
    Must return a list of chunk dicts with the standard shape:
    chunk_id, source_id, authority_tier, text, metadata, indexed_at."""
    chunks: list[dict] = []
    try:
        locations = requests.get(f"{DATABASE_SERVICE_URL}/api/storage-locations", timeout=10).json()
        tasks = requests.get(f"{DATABASE_SERVICE_URL}/api/shipping-tasks", timeout=10).json()
    except Exception as exc:
        return [{
            "chunk_id": f"{SOURCE_PREFIX}_unreachable",
            "source_id": f"{SOURCE_PREFIX}-database-service",
            "authority_tier": "tier_1",
            "text": f"Warehouse database unreachable: {exc}",
            "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "reachable": False},
            "indexed_at": _now_iso(),
        }]

    chunks.append({
        "chunk_id": f"{SOURCE_PREFIX}_zone_count",
        "source_id": f"{SOURCE_PREFIX}-database-service:/api/storage-locations",
        "authority_tier": "tier_1",
        "text": f"Total storage zones in the warehouse is {len(locations)}.",
        "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "metric": "count"},
        "indexed_at": _now_iso(),
    })

    for loc in locations:
        capacity = loc.get("capacity", 0)
        load = loc.get("current_load", 0)
        utilization = round((load / capacity) * 100, 1) if capacity else 0
        chunks.append({
            "chunk_id": f"{SOURCE_PREFIX}_zone_{loc.get('id')}",
            "source_id": f"{SOURCE_PREFIX}-database-service:/api/storage-locations",
            "authority_tier": "tier_1",
            "text": (
                f"Storage zone record: zone_name={loc.get('zone_name', 'unknown')}, "
                f"aisle={loc.get('aisle', 'n/a')}, shelf={loc.get('shelf', 'n/a')}, "
                f"capacity={capacity}, current_load={load}, utilization={utilization}%, "
                f"status={loc.get('status', 'unknown')}."
            ),
            "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "table": "storage_locations"},
            "indexed_at": _now_iso(),
        })

    high_risk = [l for l in locations if l.get("capacity") and (l.get("current_load", 0) / l["capacity"]) >= 0.8]
    if high_risk:
        summary = "; ".join(f"{l['zone_name']} ({l['current_load']}/{l['capacity']})" for l in high_risk)
        text = f"Storage zones close to bottleneck (80%+ utilisation): {summary}."
    else:
        text = "No storage zones are currently close to bottleneck (80%+ utilisation)."

    chunks.append({
        "chunk_id": f"{SOURCE_PREFIX}_bottleneck_summary",
        "source_id": f"{SOURCE_PREFIX}-database-service:/api/storage-locations",
        "authority_tier": "tier_1",
        "text": text,
        "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "metric": "bottleneck_risk"},
        "indexed_at": _now_iso(),
    })

    pending_tasks = [t for t in tasks if t.get("status") == "pending"]
    chunks.append({
        "chunk_id": f"{SOURCE_PREFIX}_pending_tasks",
        "source_id": f"{SOURCE_PREFIX}-database-service:/api/shipping-tasks",
        "authority_tier": "tier_1",
        "text": f"There are {len(pending_tasks)} pending shipping tasks awaiting AI prioritisation or manual assignment.",
        "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "metric": "pending_tasks"},
        "indexed_at": _now_iso(),
    })

    return chunks

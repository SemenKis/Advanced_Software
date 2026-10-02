import os
from datetime import datetime, timezone

import requests

DATABASE_SERVICE_URL = os.getenv("TRANSPORT_DATABASE_SERVICE_URL", "http://localhost:5004")
SOURCE_PREFIX = "transport"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_chunks() -> list[dict]:
    """Called once per refresh_corpus() by the shared rag_pipeline.py."""
    chunks: list[dict] = []
    try:
        shipments = requests.get(f"{DATABASE_SERVICE_URL}/api/shipments", timeout=10).json()
    except Exception as exc:
        return [{
            "chunk_id": f"{SOURCE_PREFIX}_unreachable",
            "source_id": f"{SOURCE_PREFIX}-backend",
            "authority_tier": "tier_1",
            "text": f"Transportation database unreachable: {exc}",
            "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "reachable": False},
            "indexed_at": _now_iso(),
        }]

    if not isinstance(shipments, list):
        shipments = []

    chunks.append({
        "chunk_id": f"{SOURCE_PREFIX}_shipment_count",
        "source_id": f"{SOURCE_PREFIX}-backend:/api/shipments",
        "authority_tier": "tier_1",
        "text": f"Total shipments in transportation is {len(shipments)}.",
        "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "metric": "count"},
        "indexed_at": _now_iso(),
    })

    status_counts = {}
    for shipment in shipments:
        status = str(shipment.get("status", "UNKNOWN")).upper()
        status_counts[status] = status_counts.get(status, 0) + 1

    if status_counts:
        summary = "; ".join(f"{status}={count}" for status, count in sorted(status_counts.items()))
        summary_text = f"Shipment status breakdown: {summary}."
    else:
        summary_text = "No shipments are currently recorded in the transportation system."

    chunks.append({
        "chunk_id": f"{SOURCE_PREFIX}_status_summary",
        "source_id": f"{SOURCE_PREFIX}-backend:/api/shipments",
        "authority_tier": "tier_1",
        "text": summary_text,
        "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "metric": "status_breakdown"},
        "indexed_at": _now_iso(),
    })

    delayed = [
        shipment for shipment in shipments
        if str(shipment.get("status", "")).upper() == "DELAYED"
        or int(shipment.get("delay_minutes", 0) or 0) > 0
    ]
    if delayed:
        summary = "; ".join(
            f"{shipment.get('origin', 'unknown')}->{shipment.get('destination', 'unknown')} ({shipment.get('status', 'unknown')}, delay {shipment.get('delay_minutes', 0)} min)"
            for shipment in delayed
        )
        delay_text = f"Delayed shipments: {summary}."
    else:
        delay_text = "No shipment delays are currently recorded."

    chunks.append({
        "chunk_id": f"{SOURCE_PREFIX}_delay_summary",
        "source_id": f"{SOURCE_PREFIX}-backend:/api/shipments",
        "authority_tier": "tier_1",
        "text": delay_text,
        "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "metric": "delay_tracking"},
        "indexed_at": _now_iso(),
    })

    for shipment in shipments[:5]:
        chunks.append({
            "chunk_id": f"{SOURCE_PREFIX}_shipment_{shipment.get('id')}",
            "source_id": f"{SOURCE_PREFIX}-backend:/api/shipments",
            "authority_tier": "tier_1",
            "text": (
                f"Shipment record: id={shipment.get('id', 'unknown')}, "
                f"origin={shipment.get('origin', 'unknown')}, destination={shipment.get('destination', 'unknown')}, "
                f"status={shipment.get('status', 'unknown')}, driver={shipment.get('driver', 'n/a')}, "
                f"vehicle={shipment.get('vehicle', 'n/a')}, departure_date={shipment.get('departure_date', 'n/a')}, "
                f"estimated_arrival={shipment.get('estimated_arrival', 'n/a')}, delay_minutes={shipment.get('delay_minutes', 0)}."
            ),
            "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "table": "shipments"},
            "indexed_at": _now_iso(),
        })

    return chunks

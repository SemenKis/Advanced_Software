import os
from datetime import datetime, timezone

import requests

DATABASE_SERVICE_URL = os.getenv(
    "TRANSPORTATION_DATABASE_SERVICE_URL",
    os.getenv("DATABASE_SERVICE_URL", "http://localhost:5004"),
)
SOURCE_PREFIX = "transportation"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_chunks() -> list[dict]:
    """Build live transportation context from the shipping database."""
    chunks: list[dict] = []
    try:
        shipments = requests.get(f"{DATABASE_SERVICE_URL}/api/shipments", timeout=10).json()
    except Exception as exc:
        return [{
            "chunk_id": f"{SOURCE_PREFIX}_unreachable",
            "source_id": f"{SOURCE_PREFIX}-database-service",
            "authority_tier": "tier_1",
            "text": f"Transportation database unreachable: {exc}",
            "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "reachable": False},
            "indexed_at": _now_iso(),
        }]

    shipment_count = len(shipments)
    chunks.append({
        "chunk_id": f"{SOURCE_PREFIX}_shipment_count",
        "source_id": f"{SOURCE_PREFIX}-database-service:/api/shipments",
        "authority_tier": "tier_1",
        "text": f"Total shipment records in transportation management are {shipment_count}.",
        "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "metric": "count"},
        "indexed_at": _now_iso(),
    })

    status_counts = {}
    for shipment in shipments:
        status = str(shipment.get("status", "UNKNOWN")).upper()
        status_counts[status] = status_counts.get(status, 0) + 1
        chunks.append({
            "chunk_id": f"{SOURCE_PREFIX}_shipment_{shipment.get('id')}",
            "source_id": f"{SOURCE_PREFIX}-database-service:/api/shipments",
            "authority_tier": "tier_1",
            "text": (
                f"Shipment record: id={shipment.get('id')}, origin={shipment.get('origin', 'unknown')}, "
                f"destination={shipment.get('destination', 'unknown')}, status={status}, "
                f"driver={shipment.get('driver', 'unknown')}, vehicle={shipment.get('vehicle', 'unknown')}, "
                f"departure_date={shipment.get('departure_date', 'n/a')}, "
                f"estimated_arrival={shipment.get('estimated_arrival', 'n/a')}, "
                f"delay_minutes={shipment.get('delay_minutes', 0)}."
            ),
            "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "table": "shipments"},
            "indexed_at": _now_iso(),
        })

    status_summary = "; ".join(
        f"{status}={count}" for status, count in sorted(status_counts.items())
    ) or "No shipments found"
    chunks.append({
        "chunk_id": f"{SOURCE_PREFIX}_status_summary",
        "source_id": f"{SOURCE_PREFIX}-database-service:/api/shipments",
        "authority_tier": "tier_1",
        "text": f"Current shipment status summary: {status_summary}.",
        "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "metric": "status_summary"},
        "indexed_at": _now_iso(),
    })

    delayed = [
        shipment for shipment in shipments
        if str(shipment.get("status", "")).upper() == "DELAYED"
        or int(shipment.get("delay_minutes", 0) or 0) > 0
    ]
    if delayed:
        summary = "; ".join(
            f"shipment {shipment.get('id')} ({shipment.get('origin')} to {shipment.get('destination')}, delay {shipment.get('delay_minutes', 0)} min)"
            for shipment in delayed
        )
        text = f"Delayed shipments currently active: {summary}."
    else:
        text = "No shipments are currently delayed or running late."

    chunks.append({
        "chunk_id": f"{SOURCE_PREFIX}_delayed_shipments",
        "source_id": f"{SOURCE_PREFIX}-database-service:/api/shipments",
        "authority_tier": "tier_1",
        "text": text,
        "metadata": {"source_type": "database", "feature": SOURCE_PREFIX, "metric": "delay_risk"},
        "indexed_at": _now_iso(),
    })

    return chunks

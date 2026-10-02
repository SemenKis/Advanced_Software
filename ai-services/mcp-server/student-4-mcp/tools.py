import os

import requests

TRANSPORTATION_SERVICE_URL = os.getenv("TRANSPORTATION_SERVICE_URL", "http://localhost:5004")


def _get(path: str, params: dict | None = None):
    response = requests.get(f"{TRANSPORTATION_SERVICE_URL}{path}", params=params or {}, timeout=10)
    response.raise_for_status()
    return response.json()


def get_shipment_count() -> dict:
    shipments = _get("/api/shipments")
    return {"shipment_count": len(shipments)}


def get_shipment_status(shipment_id: str | int | None = None) -> dict | list:
    if shipment_id is None or str(shipment_id).strip() == "":
        return _get("/api/shipments")

    return _get(f"/api/shipments/{int(shipment_id)}")


def get_delayed_shipments() -> list:
    shipments = _get("/api/shipments")
    return [
        shipment
        for shipment in shipments
        if str(shipment.get("status", "")).upper() == "DELAYED"
        or int(shipment.get("delay_minutes", 0) or 0) > 0
    ]


if __name__ == "__main__":
    print(get_shipment_count())
    print(get_shipment_status())
    print(get_delayed_shipments())

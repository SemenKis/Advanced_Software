import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "student-4-sam" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app import app


def test_mcp_valid_shipment_id():
    client = app.test_client()
    response = client.post("/htmx/mcp/check-shipment", data={"shipment_id": "1"})
    assert response.status_code == 200
    assert "id" in response.get_data(as_text=True)


def test_mcp_invalid_shipment_id_is_not_server_error():
    client = app.test_client()
    response = client.post("/htmx/mcp/check-shipment", data={"shipment_id": "abc"})
    assert response.status_code == 400
    assert "Shipment ID must be a number" in response.get_data(as_text=True)


def test_mcp_missing_shipment_id_uses_count():
    client = app.test_client()
    response = client.post("/htmx/mcp/check-shipment", data={})
    assert response.status_code == 200
    assert "shipment_count" in response.get_data(as_text=True)

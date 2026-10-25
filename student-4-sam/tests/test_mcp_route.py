import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "student-4-sam" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app import app
import htmx_routes


@pytest.fixture(autouse=True)
def local_transportation_api(monkeypatch):
    """Exercise MCP tools against the Flask API without a running HTTP server."""
    tools = htmx_routes._load_mcp_tools_module()

    def transport_request(shipment_id=None):
        path = "/api/shipments"
        if shipment_id is not None:
            path += f"/{shipment_id}"
        response = app.test_client().get(path)
        assert response.status_code == 200
        return response.get_json()

    monkeypatch.setattr(tools, "_transportation_request", transport_request)
    monkeypatch.setattr(htmx_routes, "_load_mcp_tools_module", lambda: tools)


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

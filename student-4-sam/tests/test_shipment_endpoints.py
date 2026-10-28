"""Contract tests for two transportation endpoint functions, using a temporary DB."""
import importlib.util
from pathlib import Path
import sys

import pytest

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))


def load_module(name):
    spec = importlib.util.spec_from_file_location(f"transportation_contract_{name}", BACKEND / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def client(tmp_path, monkeypatch):
    from flask import Flask
    db = load_module("database")
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "shipments.db"))
    db.init_database(seed=False)
    routes = load_module("transportation")
    monkeypatch.setattr(routes, "get_connection", db.get_connection)
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(routes.transportation)
    return app.test_client()


def test_get_shipments_returns_persisted_records_in_descending_order(client):
    assert client.get("/api/shipments").get_json() == []
    first = client.post("/api/shipments", json={"origin": "Sydney", "destination": "Melbourne"}).get_json()
    second = client.post("/api/shipments", json={"origin": "Brisbane", "destination": "Perth"}).get_json()
    response = client.get("/api/shipments")
    assert response.status_code == 200
    assert response.is_json
    assert [row["id"] for row in response.get_json()] == [second["id"], first["id"]]
    assert response.get_json()[0]["destination"] == "Perth"


def test_create_shipment_persists_defaults_and_normalises_status(client):
    response = client.post("/api/shipments", json={"origin": "Sydney", "destination": "Melbourne"})
    assert response.status_code == 201
    shipment = response.get_json()
    assert shipment["id"] > 0
    assert shipment["origin"] == "Sydney"
    assert shipment["destination"] == "Melbourne"
    assert shipment["status"] == "PLANNED"
    assert shipment["delay_minutes"] == 0
    assert client.get(f"/api/shipments/{shipment['id']}").get_json() == shipment
    response = client.post("/api/shipments", json={"origin": "A", "destination": "B", "status": "in_transit"})
    assert response.status_code == 201
    assert response.get_json()["status"] == "IN_TRANSIT"


@pytest.mark.parametrize("payload,error", [
    ({}, "Request body is required"),
    ({"origin": "Sydney"}, "Origin and destination are required"),
    ({"origin": "Sydney", "destination": "Perth", "status": "UNKNOWN"}, "Invalid shipment status"),
])
def test_create_shipment_rejects_invalid_input_without_writing(client, payload, error):
    response = client.post("/api/shipments", json=payload)
    assert response.status_code == 400
    assert response.get_json() == {"error": error}
    assert client.get("/api/shipments").get_json() == []

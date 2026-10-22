import os

import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5021")


def test_health_endpoint():
    response = requests.get(f"{BACKEND_URL}/health", timeout=10)
    assert response.status_code == 200


def test_storage_locations_endpoint():
    response = requests.get(f"{BACKEND_URL}/api/storage-locations", timeout=10)
    assert response.status_code == 200
    locations = response.json()
    assert isinstance(locations, list)
    assert len(locations) > 0
    assert {"zone_name", "capacity", "current_load"} <= set(locations[0].keys())

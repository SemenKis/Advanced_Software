import os

import requests

# The order-database container publishes its port 5002 on host port 5012
# (see student-1-bea/docker-compose.yml). Override with DATABASE_SERVICE_URL.
DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://localhost:5012")

ORDER_FIELDS = {
    "order_id",
    "order_name",
    "order_address",
    "order_status",
    "product_name",
    "quantity",
    "total_amount",
}


def _get_orders():
    response = requests.get(f"{DATABASE_SERVICE_URL}/orders", timeout=5)
    assert response.status_code == 200
    return response.json()


def test_service_health():
    response = requests.get(f"{DATABASE_SERVICE_URL}/", timeout=5)
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_orders_exist():
    orders = _get_orders()
    assert isinstance(orders, list)
    assert len(orders) > 0


def test_order_has_expected_fields():
    orders = _get_orders()
    assert ORDER_FIELDS <= set(orders[0].keys())


def test_order_by_id():
    # Use an id that exists now, so the test still passes if order 1 was deleted
    order_id = _get_orders()[0]["order_id"]
    response = requests.get(f"{DATABASE_SERVICE_URL}/orders/{order_id}", timeout=5)
    assert response.status_code == 200
    assert response.json()["order_id"] == order_id


def test_order_not_found():
    response = requests.get(f"{DATABASE_SERVICE_URL}/orders/999999", timeout=5)
    assert response.status_code == 404
    assert "error" in response.json()
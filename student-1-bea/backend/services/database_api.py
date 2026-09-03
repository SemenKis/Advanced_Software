import os

import requests

DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://database-service:5002")

def get_orders():
    response = requests.get(f"{DATABASE_SERVICE_URL}/orders", timeout=5)
    response.raise_for_status()
    return response.json()

def get_order_by_id_response(order_id):
    return requests.get(f"{DATABASE_SERVICE_URL}/orders/{order_id}", timeout=5)

def create_order(order_name):
    response = requests.post(
        f"{DATABASE_SERVICE_URL}/orders",
        json={"order_name": order_name},
        timeout=5,
    )
    return response
import os

import requests

DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://database-service:5002")

def get_orders():
    response = requests.get(f"{DATABASE_SERVICE_URL}/orders", timeout=5)
    response.raise_for_status()
    return response.json()

def get_order_by_id_response(order_id):
    return requests.get(f"{DATABASE_SERVICE_URL}/orders/{order_id}", timeout=5)

def create_order(order_data):
    response = requests.post(
        f"{DATABASE_SERVICE_URL}/orders",
        json=order_data,
        timeout=5,
    )
    return response

def update_order(order_id, order_data):
    response = requests.put(
        f"{DATABASE_SERVICE_URL}/orders/{order_id}",
        json=order_data,
        timeout=5,
    )
    return response
 
def delete_order(order_id):
    response = requests.delete(
        f"{DATABASE_SERVICE_URL}/orders/{order_id}",
        timeout=5,
    )
    return response

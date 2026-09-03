import os

import requests

DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://database-service:5002")


def get_products(params=None):
    response = requests.get(f"{DATABASE_SERVICE_URL}/products", params=params or {}, timeout=5)
    response.raise_for_status()
    return response.json()


def get_low_stock_products():
    response = requests.get(f"{DATABASE_SERVICE_URL}/products/low-stock", timeout=5)
    response.raise_for_status()
    return response.json()


def get_product_response(product_id):
    return requests.get(f"{DATABASE_SERVICE_URL}/products/{product_id}", timeout=5)


def create_product(payload):
    return requests.post(f"{DATABASE_SERVICE_URL}/products", json=payload, timeout=5)


def update_product(product_id, payload):
    return requests.put(f"{DATABASE_SERVICE_URL}/products/{product_id}", json=payload, timeout=5)


def delete_product(product_id):
    return requests.delete(f"{DATABASE_SERVICE_URL}/products/{product_id}", timeout=5)


def get_categories():
    response = requests.get(f"{DATABASE_SERVICE_URL}/categories", timeout=5)
    response.raise_for_status()
    return response.json()


def get_suppliers():
    response = requests.get(f"{DATABASE_SERVICE_URL}/suppliers", timeout=5)
    response.raise_for_status()
    return response.json()


def get_stocktakes():
    response = requests.get(f"{DATABASE_SERVICE_URL}/stocktakes", timeout=5)
    response.raise_for_status()
    return response.json()


def create_stocktake(payload):
    return requests.post(f"{DATABASE_SERVICE_URL}/stocktakes", json=payload, timeout=5)

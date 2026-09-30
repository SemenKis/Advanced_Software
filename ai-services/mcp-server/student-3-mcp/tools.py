import os
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://localhost:5023")


def _get(path: str, params: dict | None = None):
    response = requests.get(f"{DATABASE_SERVICE_URL}{path}", params=params or {}, timeout=10)
    response.raise_for_status()
    return response.json()


def get_product_count() -> dict:
    products = _get("/products")
    return {"product_count": len(products)}


def get_products_by_category(category_name: str) -> dict | list:
    category_name = (category_name or "").strip()
    if not category_name:
        return {"error": "category_name is required"}

    products = _get("/products")
    matches = [p for p in products if p.get("category_name", "").lower() == category_name.lower()]
    return matches


def get_low_stock_report() -> list:
    return _get("/products/low-stock")


def get_supplier_lookup(supplier_name: str) -> dict | list:
    supplier_name = (supplier_name or "").strip()
    if not supplier_name:
        return {"error": "supplier_name is required"}

    products = _get("/products")
    matches = [p for p in products if p.get("supplier_name", "").lower() == supplier_name.lower()]
    if not matches:
        return {"error": f"No products found for supplier '{supplier_name}'"}
    return matches


if __name__ == "__main__":
    print(get_product_count())
    print(get_products_by_category("Cleaning Supplies"))
    print(get_low_stock_report())
    print(get_supplier_lookup("Protection Company"))

import os
 
import requests
 
DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://localhost:5002")
 
PRODUCT_FIELDS = {
    "product_id",
    "name",
    "brand",
    "price",
    "quantity",
    "reorder_level",
    "category_name",
    "supplier_name",
}
 
 
def _get_products():
    response = requests.get(f"{DATABASE_SERVICE_URL}/products", timeout=5)
    assert response.status_code == 200
    return response.json()
 
 
def test_service_health():
    response = requests.get(f"{DATABASE_SERVICE_URL}/", timeout=5)
    assert response.status_code == 200
    assert response.json()["status"] == "running"
 
 
def test_products_exist():
    products = _get_products()
    assert isinstance(products, list)
    assert len(products) > 0
 
 
def test_product_has_expected_fields():
    products = _get_products()
    assert PRODUCT_FIELDS <= set(products[0].keys())
 
 
def test_product_by_id():
    # Use an id that exists now, so the test still passes if product 1 was deleted
    product_id = _get_products()[0]["product_id"]
    response = requests.get(f"{DATABASE_SERVICE_URL}/products/{product_id}", timeout=5)
    assert response.status_code == 200
    assert response.json()["product_id"] == product_id
 
 
def test_product_not_found():
    response = requests.get(f"{DATABASE_SERVICE_URL}/products/999999", timeout=5)
    assert response.status_code == 404
    assert "error" in response.json()
 
 
def test_low_stock_products_are_at_or_below_reorder_level():
    response = requests.get(f"{DATABASE_SERVICE_URL}/products/low-stock", timeout=5)
    assert response.status_code == 200
    low_stock = response.json()
    assert isinstance(low_stock, list)
    for product in low_stock:
        assert product["quantity"] <= product["reorder_level"]
    # The endpoint promises lowest quantity first
    quantities = [p["quantity"] for p in low_stock]
    assert quantities == sorted(quantities)
 
 
def test_low_stock_matches_full_product_list():
    all_products = _get_products()
    expected_ids = {p["product_id"] for p in all_products if p["quantity"] <= p["reorder_level"]}
    response = requests.get(f"{DATABASE_SERVICE_URL}/products/low-stock", timeout=5)
    assert {p["product_id"] for p in response.json()} == expected_ids
 
 
def test_products_can_be_filtered_by_category():
    category_id = _get_products()[0]["category_id"]
    response = requests.get(
        f"{DATABASE_SERVICE_URL}/products", params={"category_id": category_id}, timeout=5
    )
    assert response.status_code == 200
    filtered = response.json()
    assert len(filtered) > 0
    assert all(p["category_id"] == category_id for p in filtered)
 
 
def test_categories_and_suppliers_exist():
    for path in ("categories", "suppliers"):
        response = requests.get(f"{DATABASE_SERVICE_URL}/{path}", timeout=5)
        assert response.status_code == 200
        assert len(response.json()) > 0
 

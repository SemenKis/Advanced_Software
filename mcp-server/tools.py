import os
import requests

STUDENT_SERVICES = {
    "warehouse": os.environ.get("WAREHOUSE_DB_URL", "http://localhost:5020"),
    "order": os.environ.get("ORDER_DB_URL", "http://localhost:5012"),
    "inventory": os.environ.get("INVENTORY_DB_URL", "http://localhost:5002"),
    "transportation": os.environ.get("TRANSPORT_DB_URL", "http://localhost:5032"),
}


def check_storage_capacity(zone_name: str = None):
    try:
        resp = requests.get(f"{STUDENT_SERVICES['warehouse']}/api/storage-locations", timeout=5)
        resp.raise_for_status()
        locations = resp.json()
    except Exception as e:
        return {"status": "error", "error": f"Could not reach warehouse database: {e}"}

    if zone_name:
        locations = [l for l in locations if l.get("zone_name", "").lower() == zone_name.lower()]
        if not locations:
            return {"status": "error", "error": f"Zone '{zone_name}' not found"}

    results = []
    for loc in locations:
        capacity = loc.get("capacity", 0)
        load = loc.get("current_load", 0)
        utilization = round((load / capacity) * 100, 1) if capacity else 0
        results.append({
            "zone_name": loc.get("zone_name"),
            "current_load": load,
            "capacity": capacity,
            "utilization_pct": utilization,
        })

    return {"status": "success", "results": results}


def check_order_status(order_id: str = None):
    try:
        url = f"{STUDENT_SERVICES['order']}/orders"

        if order_id:
            url += f"/{order_id}"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return {"status": "success", "results": resp.json()}
    except Exception as e:
        return {"status": "error", "error": f"Could not reach order database: {e}"}

def inventory_product_count():
    try:
        resp = requests.get(f"{STUDENT_SERVICES['inventory']}/products", timeout=5)
        resp.raise_for_status()
        products = resp.json()
    except Exception as e:
        return {"status": "error", "error": f"Could not reach inventory database: {e}"}
    return {"status": "success", "results": {"product_count": len(products)}}


def inventory_products_by_category(category_name: str = None):
    if not category_name:
        return {"status": "error", "error": "category_name is required"}
    try:
        resp = requests.get(f"{STUDENT_SERVICES['inventory']}/products", timeout=5)
        resp.raise_for_status()
        products = resp.json()
    except Exception as e:
        return {"status": "error", "error": f"Could not reach inventory database: {e}"}

    matches = [p for p in products if p.get("category_name", "").lower() == category_name.lower()]
    return {"status": "success", "results": matches}


def inventory_low_stock_report():
    try:
        resp = requests.get(f"{STUDENT_SERVICES['inventory']}/products/low-stock", timeout=5)
        resp.raise_for_status()
        return {"status": "success", "results": resp.json()}
    except Exception as e:
        return {"status": "error", "error": f"Could not reach inventory database: {e}"}


def inventory_supplier_lookup(supplier_name: str = None):
    if not supplier_name:
        return {"status": "error", "error": "supplier_name is required"}
    try:
        resp = requests.get(f"{STUDENT_SERVICES['inventory']}/products", timeout=5)
        resp.raise_for_status()
        products = resp.json()
    except Exception as e:
        return {"status": "error", "error": f"Could not reach inventory database: {e}"}

    matches = [p for p in products if p.get("supplier_name", "").lower() == supplier_name.lower()]
    if not matches:
        return {"status": "error", "error": f"No products found for supplier '{supplier_name}'"}
    return {"status": "success", "results": matches}


def check_shipment_status(shipment_id: str = None):
    try:
        url = f"{STUDENT_SERVICES['transportation']}/api/shipments"
        if shipment_id:
            url += f"/{shipment_id}"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return {"status": "success", "results": resp.json()}
    except Exception as e:
        return {"status": "error", "error": f"Could not reach transportation database: {e}"}

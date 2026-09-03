from flask import Blueprint, request
import requests

from services.database_api import (
    create_product,
    create_stocktake,
    delete_product,
    get_categories,
    get_low_stock_products,
    get_product_response,
    get_products,
    get_stocktakes,
    get_suppliers,
    update_product,
)
from views.html_formatters import (
    format_categories_options,
    format_product_html,
    format_products_html,
    format_stocktakes_html,
    format_suppliers_options,
)

normal_ui = Blueprint("inventory", __name__)


@normal_ui.get("/")
def health():
    return "<p>inventory-service running</p>", 200

# READ

@normal_ui.get("/products")
def list_products():
    params = {}
    if request.args.get("search"):
        params["search"] = request.args.get("search").strip()
    if request.args.get("category_id"):
        params["category_id"] = request.args.get("category_id")
    if request.args.get("supplier_id"):
        params["supplier_id"] = request.args.get("supplier_id")
    if request.args.get("sort_by"):
        params["sort_by"] = request.args.get("sort_by")
    if request.args.get("sort_dir"):
        params["sort_dir"] = request.args.get("sort_dir")

    try:
        products = get_products(params)
        return format_products_html(products), 200
    except requests.RequestException as exc:
        return f"<p>Failed to retrieve products.</p><pre>{exc}</pre>", 503


@normal_ui.get("/products/low-stock")
def list_low_stock():
    try:
        products = get_low_stock_products()
        if not products:
            return "<p>All products are above their reorder level.</p>", 200
        return format_products_html(products), 200
    except requests.RequestException as exc:
        return f"<p>Failed to retrieve low-stock products.</p><pre>{exc}</pre>", 503


@normal_ui.get("/products/<int:product_id>")
def get_single_product(product_id):
    try:
        response = get_product_response(product_id)
        if response.status_code == 404:
            return "<p>Product not found.</p>", 404
        response.raise_for_status()
        return format_product_html(response.json()), 200
    except requests.RequestException as exc:
        return f"<p>Failed to retrieve product.</p><pre>{exc}</pre>", 503

# CREATE

@normal_ui.post("/products")
def add_product():
    form = request.form
    required = ["name", "category_id", "supplier_id", "price"]
    missing = [f for f in required if not form.get(f)]
    if missing:
        return f"<p>Missing required fields: {', '.join(missing)}</p>", 400

    payload = {
        "name": form.get("name"),
        "brand": form.get("brand", ""),
        "description": form.get("description", ""),
        "category_id": int(form.get("category_id")),
        "supplier_id": int(form.get("supplier_id")),
        "price": float(form.get("price")),
        "quantity": int(form.get("quantity", 0) or 0),
        "reorder_level": int(form.get("reorder_level", 10) or 10),
    }
    try:
        response = create_product(payload)
        response.raise_for_status()
        data = response.json()
        return f"<p>Product added successfully (ID {data['product_id']}).</p>", 201
    except requests.RequestException as exc:
        return f"<p>Failed to add product.</p><pre>{exc}</pre>", 503

# UPDATE

@normal_ui.put("/products/<int:product_id>")
def edit_product(product_id):
    form = request.form
    payload = {}
    for field in ["name", "brand", "description"]:
        if form.get(field) is not None:
            payload[field] = form.get(field)
    for field in ["category_id", "supplier_id", "quantity", "reorder_level"]:
        if form.get(field):
            payload[field] = int(form.get(field))
    if form.get("price"):
        payload["price"] = float(form.get("price"))

    try:
        response = update_product(product_id, payload)
        if response.status_code == 404:
            return "<p>Product not found.</p>", 404
        response.raise_for_status()
        return "<p>Product updated successfully.</p>", 200
    except requests.RequestException as exc:
        return f"<p>Failed to update product.</p><pre>{exc}</pre>", 503

# DELETE

@normal_ui.delete("/products/<int:product_id>")
def remove_product(product_id):
    try:
        response = delete_product(product_id)
        if response.status_code == 404:
            return "<p>Product not found.</p>", 404
        response.raise_for_status()
        return "<p>Product discontinued (deleted) successfully.</p>", 200
    except requests.RequestException as exc:
        return f"<p>Failed to delete product.</p><pre>{exc}</pre>", 503

# CATEGORIES/SUPPLIERS OPTIONS

@normal_ui.get("/categories/options")
def category_options():
    try:
        categories = get_categories()
        return format_categories_options(categories), 200
    except requests.RequestException as exc:
        return f"<p>Failed to load categories.</p><pre>{exc}</pre>", 503


@normal_ui.get("/suppliers/options")
def supplier_options():
    try:
        suppliers = get_suppliers()
        return format_suppliers_options(suppliers), 200
    except requests.RequestException as exc:
        return f"<p>Failed to load suppliers.</p><pre>{exc}</pre>", 503

# STOCKTAKES

@normal_ui.get("/stocktakes")
def list_stocktakes():
    try:
        stocktakes = get_stocktakes()
        return format_stocktakes_html(stocktakes), 200
    except requests.RequestException as exc:
        return f"<p>Failed to retrieve stocktake activity.</p><pre>{exc}</pre>", 503


@normal_ui.post("/stocktakes")
def add_stocktake():
    form = request.form
    product_id = form.get("product_id")
    member_name = form.get("member_name", "").strip()
    counted_quantity = form.get("counted_quantity")

    if not product_id or not member_name or counted_quantity is None or counted_quantity == "":
        return "<p>Product, member name and counted quantity are required.</p>", 400

    payload = {
        "product_id": int(product_id),
        "member_name": member_name,
        "counted_quantity": int(counted_quantity),
    }
    try:
        response = create_stocktake(payload)
        if response.status_code == 404:
            return "<p>Product not found.</p>", 404
        response.raise_for_status()
        return "<p>Stocktake recorded successfully.</p>", 201
    except requests.RequestException as exc:
        return f"<p>Failed to record stocktake.</p><pre>{exc}</pre>", 503

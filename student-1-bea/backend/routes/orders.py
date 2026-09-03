from flask import Blueprint, jsonify, request
import requests

from services.database_api import (
    get_order_by_id_response, 
    get_orders, 
    create_order,
    update_order,
    delete_order,
)
from views.html_formatters import format_order_html, format_orders_html, format_order_ref, with_order_ref


orders_bp = Blueprint("orders", __name__)

# TODO:
# routes:  order/id,
# DONE: order/list, order/create, order/id/details, order/update, order/delete

@orders_bp.post("/orders")
def create_order_route():
    data = request.get_json()

    order_name = data.get("order_name", "").strip()
    order_address = data.get("order_address", "").strip()
    product_name = data.get("product_name", "").strip()
    quantity = data.get("quantity", 1)
    total_amount = data.get("total_amount")
    order_status = data.get("order_status", "pending").strip() or "pending"

    if not order_name:
        return jsonify({"error": "Order name is required"}), 400
    if not order_address:
        return jsonify({"error": "Order address is required"}), 400
    if not product_name:
        return jsonify({"error": "Product name is required"}), 400
    if total_amount is None:
        return jsonify({"error": "Total amount is required"}), 400

    response = create_order({
        "order_name": order_name,
        "order_address": order_address,
        "order_status": order_status,
        "product_name": product_name,
        "quantity": quantity,
        "total_amount": total_amount,
    })
    return jsonify(with_order_ref(response.json())), response.status_code

@orders_bp.get("/orders")
def get_orders_route():
    orders = get_orders()
    return jsonify([with_order_ref(order) for order in orders])


@orders_bp.put("/orders/<int:order_id>")
def update_order_route(order_id):
    data = request.get_json()
 
    order_name = data.get("order_name", "").strip()
    order_address = data.get("order_address", "").strip()
    product_name = data.get("product_name", "").strip()
    quantity = data.get("quantity", 1)
    total_amount = data.get("total_amount")
    order_status = data.get("order_status", "pending").strip() or "pending"
 
    if not order_name:
        return jsonify({"error": "Order name is required"}), 400
    if not order_address:
        return jsonify({"error": "Order address is required"}), 400
    if not product_name:
        return jsonify({"error": "Product name is required"}), 400
    if total_amount is None:
        return jsonify({"error": "Total amount is required"}), 400
 
    response = update_order(order_id, {
        "order_name": order_name,
        "order_address": order_address,
        "order_status": order_status,
        "product_name": product_name,
        "quantity": quantity,
        "total_amount": total_amount,
    })
    return jsonify(response.json()), response.status_code
 
 
@orders_bp.delete("/orders/<int:order_id>")
def delete_order_route(order_id):
    response = delete_order(order_id)
    return jsonify(response.json()), response.status_code

from flask import Blueprint, request, jsonify
import requests 

from services.database_api import get_order_by_id_response, get_orders, create_order
# , get_orders_by_subject_response
from views.html_formatters import format_order_html, format_orders_html


orders_bp = Blueprint("orders", __name__)

# TODO:
# routes: order/list, order/id, order/id/details, order/create, order/update, order/delete, 


# routes/orders.py
@orders_bp.post("/orders")
def create_order_route():
    order_name = request.get_json().get("order_name", "").strip()
    if not order_name:
        return jsonify({"error": "Order name is required"}), 400

    response = create_order(order_name)
    return jsonify(response.json()), response.status_code

@orders_bp.get("/orders")
def get_orders_route():
    orders = get_orders()
    return jsonify(orders)

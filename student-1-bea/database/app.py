from flask import Flask, jsonify, request
import sqlite3

app = Flask(__name__)

DATABASE_NAME = "/app/data/order.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def health():
    return jsonify({"service": "database-service", "status": "running"})

@app.post("/orders")
def create_order():
    data = request.get_json()
    order_name = data.get("order_name", "")
    order_address = data.get("order_address", "")
    order_status = data.get("order_status", "pending") or "pending"
    product_name = data.get("product_name", "")
    quantity = data.get("quantity", 1)
    total_amount = data.get("total_amount")

    if not order_name:
        return jsonify({"error": "order_name required"}), 400
    if not order_address:
        return jsonify({"error": "order_address required"}), 400
    if not product_name:
        return jsonify({"error": "product_name required"}), 400
    if total_amount is None:
        return jsonify({"error": "total_amount required"}), 400

    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO orders (
            order_name, order_address, order_status,
            product_name, quantity, total_amount
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (order_name, order_address, order_status, product_name, quantity, total_amount),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({
        "order_id": new_id,
        "order_name": order_name,
        "order_address": order_address,
        "order_status": order_status,
        "product_name": product_name,
        "quantity": quantity,
        "total_amount": total_amount,
    }), 201

@app.get("/orders")
def get_orders():
    conn = get_db_connection()
    orders = conn.execute(
        """
        SELECT order_id, order_name, order_address, order_status,
               product_name, quantity, total_amount
        FROM orders
        """
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in orders])


@app.put("/orders/<int:order_id>")
def update_order(order_id):
    data = request.get_json()
    order_name = data.get("order_name", "")
    order_address = data.get("order_address", "")
    order_status = data.get("order_status", "pending") or "pending"
    product_name = data.get("product_name", "")
    quantity = data.get("quantity", 1)
    total_amount = data.get("total_amount")
 
    if not order_name:
        return jsonify({"error": "order_name required"}), 400
    if not order_address:
        return jsonify({"error": "order_address required"}), 400
    if not product_name:
        return jsonify({"error": "product_name required"}), 400
    if total_amount is None:
        return jsonify({"error": "total_amount required"}), 400
 
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT order_id FROM orders WHERE order_id = ?", (order_id,)
    ).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"error": "Order not found"}), 404
 
    conn.execute(
        """
        UPDATE orders
        SET order_name = ?,
            order_address = ?,
            order_status = ?,
            product_name = ?,
            quantity = ?,
            total_amount = ?
        WHERE order_id = ?
        """,
        (order_name, order_address, order_status, product_name, quantity, total_amount, order_id),
    )
    conn.commit()
    conn.close()
 
    return jsonify({
        "order_id": order_id,
        "order_name": order_name,
        "order_address": order_address,
        "order_status": order_status,
        "product_name": product_name,
        "quantity": quantity,
        "total_amount": total_amount,
    }), 200
 
@app.delete("/orders/<int:order_id>")
def delete_order(order_id):
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT order_id FROM orders WHERE order_id = ?", (order_id,)
    ).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"error": "Order not found"}), 404
 
    conn.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))
    conn.commit()
    conn.close()
 
    return jsonify({"order_id": order_id, "deleted": True}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
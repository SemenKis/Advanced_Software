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
    order_name = data.get("order_name", "").strip()
    if not order_name:
        return jsonify({"error": "order_name required"}), 400

    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO orders (order_name) VALUES (?)", (order_name,)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({"order_id": new_id, "order_name": order_name}), 201

@app.get("/orders")
def get_orders():
    conn = get_db_connection()
    orders = conn.execute("SELECT order_id, order_name FROM orders").fetchall()
    conn.close()
    return jsonify([dict(row) for row in orders])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
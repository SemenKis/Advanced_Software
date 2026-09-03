import sqlite3
from flask import Flask, jsonify, request
from datetime import datetime

app = Flask(__name__)

DATABASE_NAME = "/app/data/inventory.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def health():
    return jsonify({"service": "database-service", "status": "running"})

@app.get("/categories")
def get_categories():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM category ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.post("/categories")
def create_category():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    conn = get_db_connection()
    cur = conn.execute("INSERT INTO category (name) VALUES (?)", (name,))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"category_id": new_id, "name": name}), 201


@app.get("/suppliers")
def get_suppliers():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM supplier ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.post("/suppliers")
def create_supplier():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    conn = get_db_connection()
    cur = conn.execute(
        "INSERT INTO supplier (name, phone_number, email) VALUES (?, ?, ?)",
        (name, data.get("phone_number", ""), data.get("email", "")),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"supplier_id": new_id}), 201



PRODUCT_VIEW_SQL = """
    SELECT
        p.product_id, p.category_id, p.supplier_id, p.name, p.brand,
        p.description, p.price, p.quantity, p.reorder_level,
        c.name AS category_name, s.name AS supplier_name
    FROM products p
    JOIN category c ON c.category_id = p.category_id
    JOIN supplier s ON s.supplier_id = p.supplier_id
"""


@app.get("/products")
def get_products():
    category_id = request.args.get("category_id")
    supplier_id = request.args.get("supplier_id")
    search = request.args.get("search", "").strip()
    sort_by = request.args.get("sort_by", "name")
    sort_dir = request.args.get("sort_dir", "asc").lower()

    sort_column_map = {
        "name": "p.name",
        "price": "p.price",
        "quantity": "p.quantity",
        "category_name": "c.name",
        "supplier_name": "s.name",
    }
    sort_column = sort_column_map.get(sort_by, "p.name")
    sort_dir = "DESC" if sort_dir == "desc" else "ASC"

    query = PRODUCT_VIEW_SQL
    conditions = []
    params = []

    if category_id:
        conditions.append("p.category_id = ?")
        params.append(category_id)
    if supplier_id:
        conditions.append("p.supplier_id = ?")
        params.append(supplier_id)
    if search:
        conditions.append("(p.name LIKE ? OR p.brand LIKE ? OR p.description LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += f" ORDER BY {sort_column} {sort_dir}"

    conn = get_db_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/products/low-stock")
def get_low_stock_products():
    conn = get_db_connection()
    rows = conn.execute(
        PRODUCT_VIEW_SQL + " WHERE p.quantity <= p.reorder_level ORDER BY p.quantity ASC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/products/<int:product_id>")
def get_product(product_id):
    conn = get_db_connection()
    row = conn.execute(PRODUCT_VIEW_SQL + " WHERE p.product_id = ?", (product_id,)).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(dict(row))


@app.post("/products")
def create_product():
    data = request.get_json(force=True, silent=True) or {}
    required = ["name", "category_id", "supplier_id", "price"]
    missing = [f for f in required if data.get(f) in (None, "")]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    conn = get_db_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO products (
                category_id, supplier_id, name, brand, description, price, quantity, reorder_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["category_id"],
                data["supplier_id"],
                data["name"],
                data.get("brand", ""),
                data.get("description", ""),
                data["price"],
                data.get("quantity", 0),
                data.get("reorder_level", 10),
            ),
        )
        conn.commit()
        new_id = cur.lastrowid
    except sqlite3.IntegrityError as exc:
        conn.close()
        return jsonify({"error": f"Integrity error: {exc}"}), 400
    conn.close()
    return jsonify({"product_id": new_id}), 201


@app.put("/products/<int:product_id>")
def update_product(product_id):
    data = request.get_json(force=True, silent=True) or {}
    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM products WHERE product_id = ?", (product_id,)).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"error": "Product not found"}), 404

    fields = ["category_id", "supplier_id", "name", "brand", "description", "price", "quantity", "reorder_level"]
    updated = {f: data.get(f, existing[f]) for f in fields}

    conn.execute(
        """
        UPDATE products
        SET category_id = ?, supplier_id = ?, name = ?, brand = ?, description = ?,
            price = ?, quantity = ?, reorder_level = ?
        WHERE product_id = ?
        """,
        (
            updated["category_id"], updated["supplier_id"], updated["name"], updated["brand"],
            updated["description"], updated["price"], updated["quantity"], updated["reorder_level"],
            product_id,
        ),
    )
    conn.commit()
    conn.close()
    return jsonify({"product_id": product_id, "status": "updated"})


@app.delete("/products/<int:product_id>")
def delete_product(product_id):
    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM products WHERE product_id = ?", (product_id,)).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"error": "Product not found"}), 404
    conn.execute("DELETE FROM stocktake WHERE product_id = ?", (product_id,))
    conn.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
    conn.commit()
    conn.close()
    return jsonify({"product_id": product_id, "status": "deleted"})



@app.get("/stocktakes")
def get_stocktakes():
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT st.stocktake_id, st.product_id, p.name AS product_name,
               st.member_name, st.counted_quantity, st.timestamp
        FROM stocktake st
        JOIN products p ON p.product_id = st.product_id
        ORDER BY st.timestamp DESC
        """
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.post("/stocktakes")
def create_stocktake():
    data = request.get_json(force=True, silent=True) or {}
    product_id = data.get("product_id")
    member_name = (data.get("member_name") or "").strip()
    counted_quantity = data.get("counted_quantity")

    if not product_id or not member_name or counted_quantity is None:
        return jsonify({"error": "product_id, member_name and counted_quantity are required"}), 400

    conn = get_db_connection()
    product = conn.execute("SELECT * FROM products WHERE product_id = ?", (product_id,)).fetchone()
    if product is None:
        conn.close()
        return jsonify({"error": "Product not found"}), 404

    timestamp = datetime.utcnow().isoformat(timespec="seconds")
    cur = conn.execute(
        "INSERT INTO stocktake (product_id, member_name, counted_quantity, timestamp) VALUES (?, ?, ?, ?)",
        (product_id, member_name, counted_quantity, timestamp),
    )

    conn.execute(
        "UPDATE products SET quantity = ? WHERE product_id = ?",
        (counted_quantity, product_id),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"stocktake_id": new_id, "timestamp": timestamp}), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)

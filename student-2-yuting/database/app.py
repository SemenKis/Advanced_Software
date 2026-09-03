from flask import Flask, jsonify, request, abort
import sqlite3
import os
from datetime import datetime


app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "warehouse.db")


TABLES = {
    "storage-locations": {
        "table": "storage_locations",
        "columns": ["zone_name", "aisle", "shelf", "bin_code", "capacity", "current_load", "status"],
    },
    "packing-lists": {
        "table": "packing_lists",
        "columns": ["order_id", "items_json", "status"],
    },
    "shipping-tasks": {
        "table": "shipping_tasks",
        "columns": ["order_id", "packing_list_id", "task_type", "assigned_to", "priority", "status", "bottleneck_risk"],
    },
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    conn = get_db()
    with open(schema_path, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def row_to_dict(row):
    return dict(row)


@app.route("/health")
def health():
    return {"status": "ok", "service": "student2-database"}



@app.route("/api/<resource>", methods=["GET", "POST"])
def collection(resource):
    if resource not in TABLES:
        abort(404, description=f"Resource '{resource}'")
    meta = TABLES[resource]
    conn = get_db()

   


    if request.method == "GET":
        rows = conn.execute(f"SELECT * FROM {meta['table']} ORDER BY id DESC").fetchall()
        conn.close()
        return jsonify([row_to_dict(r) for r in rows])

    data = request.get_json(force=True) or {}
    cols = [c for c in meta["columns"] if c in data]
    if not cols:
        conn.close()
        abort(400, description="No valid columns provided")
    values = [data[c] for c in cols]
    now = datetime.utcnow().isoformat()
    placeholders = ",".join(["?"] * len(cols))
    cols_sql = ",".join(cols + ["created_at", "updated_at"])
    cur = conn.execute(
        f"INSERT INTO {meta['table']} ({cols_sql}) VALUES ({placeholders}, ?, ?)",
        values + [now, now]
    )
    conn.commit()
    new_id = cur.lastrowid
    row = conn.execute(f"SELECT * FROM {meta['table']} WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row)), 201


@app.route("/api/<resource>/<int:item_id>", methods=["GET", "PUT", "DELETE"])
def item(resource, item_id):
    if resource not in TABLES:
        abort(404, description=f"Unknown resource '{resource}'")
    meta = TABLES[resource]
    conn = get_db()

    row = conn.execute(f"SELECT * FROM {meta['table']} WHERE id = ?", (item_id,)).fetchone()
    if not row:
        conn.close()
        abort(404, description=f"{resource} with id {item_id} not found")

    if request.method == "GET":
        conn.close()
        return jsonify(row_to_dict(row))

    if request.method == "PUT":
        data = request.get_json(force=True) or {}
        cols = [c for c in meta["columns"] if c in data]
        if not cols:
            conn.close()
            abort(400, description="No valid columns provided")
        values = [data[c] for c in cols]
        now = datetime.utcnow().isoformat()
        set_sql = ",".join([f"{c} = ?" for c in cols])
        conn.execute(
            f"UPDATE {meta['table']} SET {set_sql}, updated_at = ? WHERE id = ?",
            values + [now, item_id]
        )
        conn.commit()
        row = conn.execute(f"SELECT * FROM {meta['table']} WHERE id = ?", (item_id,)).fetchone()
        conn.close()
        return jsonify(row_to_dict(row))

    conn.execute(f"DELETE FROM {meta['table']} WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return "", 204

if __name__ == "__main__":
    db_already_existed = os.path.exists(DB_PATH)
    init_db()
    if not db_already_existed:
        from seed import seed_all
        seed_all()
    app.run(host="0.0.0.0", port=5002)

   
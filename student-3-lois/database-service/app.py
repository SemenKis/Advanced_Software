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

@app.get("/suppliers")
def get_suppliers():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM supplier ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)

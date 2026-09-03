
import os
import sqlite3
from datetime import datetime, timedelta

DATA_DIR = "/app/data"
DATABASE_NAME = os.path.join(DATA_DIR, "inventory.db")

os.makedirs(DATA_DIR, exist_ok=True)

conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

cursor.executescript(
    """
    CREATE TABLE IF NOT EXISTS category (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS supplier (
        supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone_number TEXT,
        email TEXT
    );

    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL,
        supplier_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        brand TEXT,
        description TEXT,
        price REAL NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 0,
        reorder_level INTEGER NOT NULL DEFAULT 10,
        FOREIGN KEY (category_id) REFERENCES category (category_id),
        FOREIGN KEY (supplier_id) REFERENCES supplier (supplier_id)
    );

    CREATE TABLE IF NOT EXISTS stocktake (
        stocktake_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        member_name TEXT NOT NULL,
        counted_quantity INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products (product_id)
    );
    """
)

cursor.execute("DELETE FROM stocktake")
cursor.execute("DELETE FROM products")
cursor.execute("DELETE FROM supplier")
cursor.execute("DELETE FROM category")

categories = [
    (1, "Organisation Tools"),
    (2, "Loading Equipment"),
    (3, "Cleaning Supplies"),
    (4, "Perishables"),
    (5, "Safety Gear"),

]

cursor.executemany("INSERT INTO category (category_id, name) VALUES (?, ?)", categories)

suppliers = [
    (1, "TrackTools Co.", "0400111222", "orders@tracktools.example.com"),
    (2, "Global Machinery Ltd.", "0400222333", "sales@globalmachinery.example.com"),
    (3, "Protection Company", "0400333444", "contact@protectcompany.example.com"),
    (4, "CleanPro Supplies", "0400444555", "info@cleanpro.example.com"),
    (5, "SnackWorld Distribution", "0400555666", "orders@snackworld.example.com"),

]
cursor.executemany(
    "INSERT INTO supplier (supplier_id, name, phone_number, email) VALUES (?, ?, ?, ?)",
    suppliers,
)

products = [
    (1, 1, 1, "Barcode Scanners", "ClickTech", "Handheld scanner with Bluetooth connectivity", 35.99, 120, 20),
    (2, 2, 2, "Pallet Jacks", "LoadMaster", "Stainless steel adjustable pallet jack", 139.49, 8, 15),
    (3, 5, 3, "Medium Safety Gloves", "SafetyFirst", "Rubber gloves, medium-sized", 10.20, 45, 10),
    (4, 4, 5, "Kettle Korn", "CrispCo", "Kettle-cooked chips, 150g bag", 5.10, 60, 15),
    (5, 3, 4, "Bucket'n'Mop", "SqueakyClean", "Cleaning set with bucket and mop", 19.99, 35, 10),

]
cursor.executemany(
    """
    INSERT INTO products (
        product_id, category_id, supplier_id, name, brand, description, price, quantity, reorder_level
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    products,
)

stocktakes = [
    (1, 1, "Alex Chen", 118, "2026-01-01 15:15:00"),
    (2, 2, "Alex Chen", 8, "2026-02-01 10:30:00"),
    (3, 3, "Priya Nair", 45, "2026-03-01 09:55:00"),
    (4, 4, "Priya Nair", 60, "2026-04-01 10:00:00"),
    (5, 5, "Jordan Lee", 35, "2026-05-01 20:30:00"),
]
cursor.executemany(
    """
    INSERT INTO stocktake (stocktake_id, product_id, member_name, counted_quantity, timestamp)
    VALUES (?, ?, ?, ? , ?)
    """,
    stocktakes,
)

conn.commit()
conn.close()

print("Inventory database initialized: 8 categories, 8 suppliers, 12 products, 10 stocktake records.")

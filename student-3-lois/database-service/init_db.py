
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
    (1, "Beverages"),
    (2, "Snacks"),
    (3, "Dairy"),
    (4, "Frozen Foods"),
    (5, "Cleaning Supplies"),
    (6, "Electronics"),
    (7, "Stationery"),
    (8, "Personal Care"),
]
cursor.executemany("INSERT INTO category (category_id, name) VALUES (?, ?)", categories)

suppliers = [
    (1, "Fresh Farms Co.", "0400111222", "orders@freshfarms.example.com"),
    (2, "Global Beverages Ltd.", "0400222333", "sales@globalbev.example.com"),
    (3, "SnackWorld Distribution", "0400333444", "contact@snackworld.example.com"),
    (4, "CleanPro Supplies", "0400444555", "info@cleanpro.example.com"),
    (5, "TechStock Wholesale", "0400555666", "orders@techstock.example.com"),
    (6, "OfficeMart Supplies", "0400666777", "sales@officemart.example.com"),
    (7, "PureCare Distributors", "0400777888", "hello@purecare.example.com"),
    (8, "FrostLine Foods", "0400888999", "support@frostline.example.com"),
]
cursor.executemany(
    "INSERT INTO supplier (supplier_id, name, phone_number, email) VALUES (?, ?, ?, ?)",
    suppliers,
)

products = [
    (1, 1, 2, "Sparkling Water 12-Pack", "AquaFizz", "Carbonated spring water, 12x330ml cans", 8.99, 120, 20),
    (2, 2, 3, "Sea Salt Potato Chips", "CrispCo", "Kettle-cooked chips, 150g bag", 3.49, 8, 15),
    (3, 3, 1, "Full Cream Milk 2L", "DairyBest", "Pasteurised full cream milk", 4.20, 45, 10),
    (4, 4, 8, "Frozen Mixed Vegetables 1kg", "FrostLine", "Peas, corn, carrots blend", 5.10, 60, 15),
    (5, 5, 5, "Wireless Mouse", "ClickTech", "2.4GHz wireless optical mouse", 19.99, 35, 10),
    (6, 6, 6, "A4 Notebook Pack (5)", "PaperPro", "5x 100-page ruled notebooks", 12.50, 5, 10),
    (7, 7, 7, "Hand Sanitizer 500ml", "PureCare", "70% alcohol gel sanitizer", 6.75, 90, 20),
    (8, 5, 4, "Dish Soap Concentrate", "CleanPro", "Grease-cutting dish soap, 750ml", 3.95, 3, 12),
    (9, 1, 2, "Orange Juice 1L", "AquaFizz", "100% pure squeezed orange juice", 4.60, 55, 15),
    (10, 2, 3, "Chocolate Cookies 300g", "CrispCo", "Double chocolate chip cookies", 4.10, 70, 15),
    (11, 6, 5, "USB-C Charging Cable", "ClickTech", "1.5m braided USB-C cable", 9.99, 100, 20),
    (12, 8, 7, "Moisturising Body Wash", "PureCare", "Aloe vera enriched body wash, 500ml", 5.50, 12, 15),
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
    (1, 1, "Alex Chen", 118),
    (2, 2, "Alex Chen", 8,),
    (3, 3, "Priya Nair", 45),
    (4, 6, "Priya Nair", 5),
    (5, 8, "Jordan Lee", 3),
    (6, 5, "Jordan Lee", 35),
    (7, 12, "Alex Chen", 12),
    (8, 9, "Priya Nair", 55),
    (9, 4, "Jordan Lee", 60),
    (10, 11, "Alex Chen", 100),
]
cursor.executemany(
    """
    INSERT INTO stocktake (stocktake_id, product_id, member_name, counted_quantity)
    VALUES (?, ?, ?, ?)
    """,
    stocktakes,
)

conn.commit()
conn.close()

print("Inventory database initialized: 8 categories, 8 suppliers, 12 products, 10 stocktake records.")

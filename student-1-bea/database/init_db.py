import os
import sqlite3

DATA_DIR = "/app/data"
DATABASE_NAME = os.path.join(DATA_DIR, "order.db")

os.makedirs(DATA_DIR, exist_ok=True)

conn = sqlite3.connect(
    DATABASE_NAME
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_name TEXT NOT NULL
)
""")

cursor.execute(
    "DELETE FROM orders"
)

# later fields: orderId, name, recipient, address, products, quantity, price, status

orders = [
    (1, "John Smith"),
    (2, "Sarah Jones"),
    (3, "Michael Lee"),
    (4, "Emma Brown"),
    (5, "James Wilson"),
    (6, "Olivia White"),
    (7, "Daniel Green"),
    (8, "Sophia Hall"),
    (9, "Liam King"),
    (10, "Chloe Young"),
]

cursor.executemany(
    """
    INSERT INTO orders (
        order_id,
        order_name
    )
    VALUES (?, ?)
    """,
    orders
)

conn.commit()
conn.close()

print(
    "Database initialized with 10 orders."
)
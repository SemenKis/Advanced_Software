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
    order_name TEXT NOT NULL,
    order_address TEXT NOT NULL,
    order_status TEXT NOT NULL DEFAULT 'pending',
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    total_amount REAL NOT NULL
)
""")

cursor.execute(
    "DELETE FROM orders"
)

# price and total amount should be calculated in backend since it is dependent on products-service

orders = [
    (1, "John Smith", "12 Wattle St, Sydney NSW", "pending", "Calendar", 2, 39.98),
    (2, "Sarah Jones", "5 Kingsway, Brisbane QLD", "pending", "Office Chair", 1, 149.00),
    (3, "Michael Lee", "88 High St, Melbourne VIC", "shipped", "Monitor Stand", 1, 45.50),
    (4, "Emma Brown", "3 Beach Rd, Perth WA", "pending", "Keyboard", 1, 79.99),
    (5, "James Wilson", "21 Park Ave, Adelaide SA", "delivered", "Webcam", 1, 59.95),
    (6, "Olivia White", "7 River St, Hobart TAS", "pending", "Calendar", 1, 19.99),
    (7, "Daniel Green", "16 Ocean Dr, Gold Coast QLD", "shipped", "Office Chair", 2, 298.00),
    (8, "Sophia Hall", "40 Union St, Canberra ACT", "pending", "Mouse", 3, 44.97),
    (9, "Liam King", "9 Hill Rd, Darwin NT", "delivered", "Monitor Stand", 2, 91.00),
    (10, "Chloe Young", "2 Market St, Newcastle NSW", "pending", "Keyboard", 1, 79.99),
]

cursor.executemany(
    """
    INSERT INTO orders (
        order_id,
        order_name,
        order_address,
        order_status,
        product_name,
        quantity,
        total_amount
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    orders
)

conn.commit()
conn.close()

print(
    "Database initialized with 10 orders."
)
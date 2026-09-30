import sqlite3
import os
import json
import random
from datetime import datetime


DB_PATH = os.environ.get("DB_PATH", "warehouse.db")

def seed_all():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    zones = ["A", "B", "C", "D", "E"]

    for i in range(1, 13):
        cur.execute(
            "INSERT INTO storage_locations "
            "(zone_name, aisle, shelf, bin_code, capacity, current_load, "
            "status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"Zone-{zones[i % 5]}", f"Aisle-{(i % 4) + 1}",
             f"Shelf-{(i % 6) + 1}", f"Bin-{1000 + i}",
             100, random.randint(10, 95), "active", now, now),
        )

    for i in range(1, 13):
        items = [{"sku": f"SKU-{1000 + j}", "quantity": random.randint(1, 5)} for j in range(1, 4)]
        cur.execute(
            "INSERT INTO packing_lists (order_id, items_json, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (5000 + i, json.dumps(items),
             random.choice(["pending", "packed", "shipped"]), now, now),
           
        )


    for i in range(1, 13):
        cur.execute(
            "INSERT INTO shipping_tasks "
            "(order_id, packing_list_id, task_type, assigned_to, priority, status, bottleneck_risk, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (5000 + i, i, random.choice(["pick", "pack", "load"]),
             f"Worker-{(i % 4) + 1}", random.randint(1, 10),
             random.choice(["pending", "in_progress", "completed"]), "low", now, now),
        
        )

    conn.commit()
    conn.close()
    print("Seeded storage_locations, packing_lists, and shipping_tasks tables with 12 records each.")



if __name__ == "__main__":
    seed_all()


CREATE TABLE IF NOT EXISTS storage_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_name TEXT NOT NULL,
    aisle TEXT,
    shelf TEXT,
    bin_code TEXT,
    current_load INTEGER DEFAULT 0,
    capacity INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS packing_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    items_json TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS shipping_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    packing_list_id INTEGER,
    order_id INTEGER,
    task_type TEXT,
    assigned_to TEXT,
    priority INTEGER DEFAULT 5,
    status TEXT DEFAULT 'pending',
    bottleneck_risk TEXT DEFAULT 'low',
    created_at TEXT,
    updated_at TEXT
);


CREATE TABLE IF NOT EXISTS shipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    origin TEXT NOT NULL,
    destination TEXT NOT NULL,

    status TEXT NOT NULL DEFAULT 'PLANNED',

    driver TEXT,
    vehicle TEXT,

    departure_date TEXT,
    estimated_arrival TEXT,

    delay_minutes INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
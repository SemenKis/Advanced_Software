import os
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    str(BASE_DIR / "database" / "transportation.db")
)

SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
SEED_PATH = BASE_DIR / "database" / "seed.sql"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def init_database(seed=False):
    database_directory = Path(DATABASE_PATH).parent
    database_directory.mkdir(parents=True, exist_ok=True)

    connection = get_connection()

    with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
        connection.executescript(file.read())

    if seed:
        count = connection.execute(
            "SELECT COUNT(*) AS count FROM shipments"
        ).fetchone()["count"]

        if count == 0:
            with open(SEED_PATH, "r", encoding="utf-8") as file:
                connection.executescript(file.read())

    connection.commit()
    connection.close()
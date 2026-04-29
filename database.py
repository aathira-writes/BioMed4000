import sqlite3
from datetime import datetime

DB_NAME = "med_app.db"

def get_db():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'crew'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        login_time TEXT,
        logout_time TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conflicts (
        conflict_id INTEGER PRIMARY KEY AUTOINCREMENT,
        login_user_id INTEGER,
        detected_user_id INTEGER,
        timestamp TEXT,
        status TEXT DEFAULT 'unresolved',
        notes TEXT,
        FOREIGN KEY(login_user_id) REFERENCES users(user_id),
        FOREIGN KEY(detected_user_id) REFERENCES users(user_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medications (
        med_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        quantity INTEGER NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        med_id INTEGER,
        amount INTEGER,
        timestamp TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(med_id) REFERENCES medications(med_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 0,
        expiration_date TEXT,
        checked_out INTEGER DEFAULT 0,
        last_checked_out TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS checkout_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        user_id INTEGER,
        amount INTEGER,
        timestamp TEXT,
        FOREIGN KEY(item_id) REFERENCES inventory(item_id),
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS calendar_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        event_date TEXT NOT NULL,
        end_date TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS personal_medications (
        pm_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL,
        name        TEXT NOT NULL,
        dosage      TEXT,
        notes       TEXT,
        barcode     TEXT,
        added_date  TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """)

    # Migrate existing tables with new columns (safe on repeated runs)
    migrations = [
        "ALTER TABLE inventory ADD COLUMN barcode TEXT",
        "ALTER TABLE users ADD COLUMN health_notes TEXT",
        "ALTER TABLE personal_medications ADD COLUMN expiry TEXT",
    ]
    for sql in migrations:
        try:
            cursor.execute(sql)
        except sqlite3.OperationalError:
            pass  # column already exists

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()


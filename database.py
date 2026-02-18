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

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()


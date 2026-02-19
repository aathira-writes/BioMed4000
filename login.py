from database import get_db
import sqlite3


def login(username, password):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT user_id, role FROM users WHERE username=? AND password=?",
        (username, password)
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        print("Invalid username or password.")
        return None

    user_id, role = row
    return user_id, role




def create_user(username, password, role="crew"):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, password, role)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return user_id


    except sqlite3.IntegrityError:
        # Username already exists
        return None

    finally:
        conn.close()





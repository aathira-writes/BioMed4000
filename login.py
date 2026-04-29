from database import get_db
import sqlite3


def update_user_role(user_id, new_role):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role=? WHERE user_id=?", (new_role, user_id))
    conn.commit()
    conn.close()


def admin_exists():
    """Returns True if at least one admin account is registered."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


def verify_admin(username, password):
    """Returns True if the given credentials belong to an admin account."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM users WHERE username=? AND password=? AND role='admin'",
        (username, password)
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None


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





from database import get_db
from datetime import datetime

def log_conflict(login_user_id, detected_user_id, notes=""):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO conflicts (login_user_id, detected_user_id, timestamp, notes) VALUES (?, ?, ?, ?)",
        (login_user_id, detected_user_id, datetime.now().isoformat(), notes)
    )

    conn.commit()
    conn.close()

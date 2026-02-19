from database import get_db
from datetime import datetime

def log_session(user_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO sessions (user_id, login_time) VALUES (?, ?)",
        (user_id, datetime.now().isoformat())
    )

    conn.commit()
    conn.close()

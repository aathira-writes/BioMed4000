from database import get_db
from datetime import datetime

def dispense_medication(user_id, med_id, amount):
    conn = get_db()
    cursor = conn.cursor()

    # reduce inventory
    cursor.execute("UPDATE medications SET quantity = quantity - ? WHERE med_id=?", (amount, med_id))

    # log transaction
    cursor.execute("""
        INSERT INTO transactions (user_id, med_id, amount, timestamp)
        VALUES (?, ?, ?, ?)
    """, (user_id, med_id, amount, datetime.now().isoformat()))

    conn.commit()
    conn.close()

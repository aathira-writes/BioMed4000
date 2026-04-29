from database import get_db
from datetime import datetime, date, timedelta


def add_item(name, quantity, expiration_date=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO inventory (item_name, quantity, expiration_date) VALUES (?, ?, ?)",
        (name, quantity, expiration_date)
    )
    conn.commit()
    item_id = cursor.lastrowid
    conn.close()
    return item_id


def get_all_items():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT item_id, item_name, quantity, expiration_date, checked_out, last_checked_out "
        "FROM inventory ORDER BY item_name"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_item(item_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT item_id, item_name, quantity, expiration_date, checked_out, last_checked_out "
        "FROM inventory WHERE item_id=?",
        (item_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row


def edit_item(item_id, name, quantity, expiration_date):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE inventory SET item_name=?, quantity=?, expiration_date=? WHERE item_id=?",
        (name, quantity, expiration_date, item_id)
    )
    conn.commit()
    conn.close()


def delete_item(item_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM checkout_log WHERE item_id=?", (item_id,))
    cursor.execute("DELETE FROM inventory WHERE item_id=?", (item_id,))
    conn.commit()
    conn.close()


def checkout_item(item_id, user_id, amount=1):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM inventory WHERE item_id=?", (item_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return False, "Item not found."
    if row[0] < amount:
        conn.close()
        return False, f"Insufficient stock (only {row[0]} available)."
    now = datetime.now().isoformat()
    cursor.execute(
        "UPDATE inventory SET quantity=quantity-?, checked_out=checked_out+?, last_checked_out=? WHERE item_id=?",
        (amount, amount, now, item_id)
    )
    cursor.execute(
        "INSERT INTO checkout_log (item_id, user_id, amount, timestamp) VALUES (?, ?, ?, ?)",
        (item_id, user_id, amount, now)
    )
    conn.commit()
    conn.close()
    return True, "Checkout successful."


def get_dashboard_stats():
    conn = get_db()
    cursor = conn.cursor()
    today = date.today().isoformat()

    cursor.execute("SELECT COALESCE(SUM(quantity), 0) FROM inventory")
    total_qty = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM inventory WHERE quantity <= 5")
    low_stock = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM inventory WHERE expiration_date IS NOT NULL AND expiration_date < ?",
        (today,)
    )
    expired = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(checked_out), 0) FROM inventory")
    total_checkouts = cursor.fetchone()[0]

    conn.close()
    return {
        "total": total_qty,
        "low_stock": low_stock,
        "expired": expired,
        "checkouts": total_checkouts,
    }


def get_weekly_usage():
    conn = get_db()
    cursor = conn.cursor()
    today = date.today()
    results = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.isoformat()
        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM checkout_log WHERE timestamp LIKE ?",
            (f"{day_str}%",)
        )
        count = cursor.fetchone()[0]
        results.append((day.strftime("%a"), count))
    conn.close()
    return results


def get_alerts():
    conn = get_db()
    cursor = conn.cursor()
    today = date.today().isoformat()
    alerts = []

    cursor.execute("SELECT item_name, quantity FROM inventory WHERE quantity <= 5 ORDER BY quantity")
    for name, qty in cursor.fetchall():
        alerts.append(("low", f"LOW STOCK: {name} ({qty} remaining)"))

    cursor.execute(
        "SELECT item_name, expiration_date FROM inventory "
        "WHERE expiration_date IS NOT NULL AND expiration_date < ? ORDER BY expiration_date",
        (today,)
    )
    for name, exp in cursor.fetchall():
        alerts.append(("expired", f"EXPIRED: {name} (expired {exp})"))

    conn.close()
    return alerts


def get_risk_level():
    stats = get_dashboard_stats()
    if stats["expired"] > 0 or stats["low_stock"] > 3:
        return "CRITICAL", "#f85149"
    if stats["low_stock"] > 0:
        return "CAUTION", "#d29922"
    return "NOMINAL", "#3fb950"


def get_depletion_forecast(lookback_days=14):
    """
    Returns list of (item_name, qty, avg_daily, days_until_depletion, risk)
    only for items that have had at least one checkout in the lookback window.
    Sorted most critical first.
    """
    conn = get_db()
    cursor = conn.cursor()
    cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()

    cursor.execute("SELECT item_id, item_name, quantity FROM inventory")
    items = cursor.fetchall()

    results = []
    for item_id, name, qty in items:
        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM checkout_log "
            "WHERE item_id=? AND timestamp >= ?",
            (item_id, cutoff)
        )
        total_used = cursor.fetchone()[0]
        if total_used == 0:
            continue
        avg_daily = total_used / lookback_days
        days = qty / avg_daily if avg_daily > 0 else float("inf")
        if days <= 30:
            risk = "CRITICAL"
        elif days <= 60:
            risk = "CAUTION"
        else:
            risk = "NOMINAL"
        results.append((name, qty, round(avg_daily, 2), round(days), risk))

    conn.close()
    results.sort(key=lambda x: x[3])
    return results


def get_item_forecast(item_id, lookback_days=14):
    """Detailed forecast for one item. Returns dict or None."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, quantity FROM inventory WHERE item_id=?", (item_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    name, qty = row

    cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM checkout_log WHERE item_id=? AND timestamp >= ?",
        (item_id, cutoff)
    )
    total_used = cursor.fetchone()[0]
    conn.close()

    avg_daily = total_used / lookback_days
    if avg_daily > 0:
        days = qty / avg_daily
        risk = "CRITICAL" if days <= 30 else "CAUTION" if days <= 60 else "NOMINAL"
    else:
        days = None
        risk = "UNKNOWN"

    return {
        "name":      name,
        "qty":       qty,
        "avg_daily": round(avg_daily, 2),
        "days":      round(days) if days is not None else None,
        "risk":      risk,
    }


def get_item_by_barcode(barcode):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT item_id, item_name, quantity, expiration_date, checked_out, last_checked_out "
        "FROM inventory WHERE barcode=?", (barcode,)
    )
    row = cursor.fetchone()
    conn.close()
    return row


def set_item_barcode(item_id, barcode):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE inventory SET barcode=? WHERE item_id=?", (barcode, item_id))
    conn.commit()
    conn.close()


def get_user_checkout_history(user_id, limit=15):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT i.item_name, c.amount, c.timestamp "
        "FROM checkout_log c JOIN inventory i ON c.item_id = i.item_id "
        "WHERE c.user_id=? ORDER BY c.timestamp DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_health_notes(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username, role, health_notes FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def update_health_notes(user_id, notes):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET health_notes=? WHERE user_id=?", (notes, user_id))
    conn.commit()
    conn.close()


def get_calendar_events():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT event_id, title, event_date, end_date FROM calendar_events ORDER BY event_date")
    rows = cursor.fetchall()
    conn.close()
    return rows


def add_calendar_event(title, event_date, end_date=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO calendar_events (title, event_date, end_date) VALUES (?, ?, ?)",
        (title, event_date, end_date)
    )
    conn.commit()
    event_id = cursor.lastrowid
    conn.close()
    return event_id


def delete_calendar_event(event_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM calendar_events WHERE event_id=?", (event_id,))
    conn.commit()
    conn.close()

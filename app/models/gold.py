"""Gold asset models: SGB (Sovereign Gold Bonds)."""

from datetime import datetime
from app.core.database import get_connection


def _now() -> str:
    return datetime.now().isoformat()


def get_all_sgb(active_only: bool = True) -> list[dict]:
    conn = get_connection()
    try:
        q = "SELECT * FROM sgb"
        if active_only:
            q += " WHERE is_active = 1"
        q += " ORDER BY purchase_date"
        return [dict(r) for r in conn.execute(q).fetchall()]
    finally:
        conn.close()


def add_sgb(data: dict) -> int:
    now = _now()
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO sgb (series_name, units, issue_price, purchase_date, maturity_date, "
            "coupon_rate, is_active, notes, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)",
            (
                data["series_name"], data["units"], data["issue_price"],
                data["purchase_date"], data["maturity_date"],
                data.get("coupon_rate", 2.5),
                data.get("notes", ""), now, now,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_sgb(sgb_id: int, data: dict) -> None:
    now = _now()
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE sgb SET series_name=?, units=?, issue_price=?, purchase_date=?, maturity_date=?, "
            "coupon_rate=?, is_active=?, notes=?, updated_at=? WHERE id=?",
            (
                data["series_name"], data["units"], data["issue_price"],
                data["purchase_date"], data["maturity_date"],
                data.get("coupon_rate", 2.5),
                data.get("is_active", 1), data.get("notes", ""), now, sgb_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_sgb(sgb_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM sgb WHERE id = ?", (sgb_id,))
        conn.commit()
    finally:
        conn.close()

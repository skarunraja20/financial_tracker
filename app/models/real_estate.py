"""Real estate model: Properties."""

from datetime import datetime
from app.core.database import get_connection


def _now() -> str:
    return datetime.now().isoformat()


def get_all_properties(active_only: bool = True) -> list[dict]:
    conn = get_connection()
    try:
        q = "SELECT * FROM real_estate"
        # real_estate has no is_active; soft-delete not needed for properties
        q += " ORDER BY property_name"
        return [dict(r) for r in conn.execute(q).fetchall()]
    finally:
        conn.close()


def get_property_choices() -> list[tuple[int, str]]:
    """Return [(id, name), ...] for dropdowns (e.g. in home loan linking)."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, property_name FROM real_estate ORDER BY property_name").fetchall()
        return [(r["id"], r["property_name"]) for r in rows]
    finally:
        conn.close()


def add_property(data: dict) -> int:
    now = _now()
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO real_estate (property_name, property_type, location, purchase_price, "
            "purchase_date, current_value, area_sqft, is_primary, notes, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                data["property_name"], data["property_type"],
                data.get("location", ""), data["purchase_price"],
                data["purchase_date"], data["current_value"],
                data.get("area_sqft"), data.get("is_primary", 0),
                data.get("notes", ""), now, now,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_property(prop_id: int, data: dict) -> None:
    now = _now()
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE real_estate SET property_name=?, property_type=?, location=?, purchase_price=?, "
            "purchase_date=?, current_value=?, area_sqft=?, is_primary=?, notes=?, updated_at=? WHERE id=?",
            (
                data["property_name"], data["property_type"],
                data.get("location", ""), data["purchase_price"],
                data["purchase_date"], data["current_value"],
                data.get("area_sqft"), data.get("is_primary", 0),
                data.get("notes", ""), now, prop_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_property(prop_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM real_estate WHERE id = ?", (prop_id,))
        conn.commit()
    finally:
        conn.close()

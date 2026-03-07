"""Shared mutual fund CRUD (debt, equity, gold categories)."""

from datetime import datetime
from app.core.database import get_connection


def _now() -> str:
    return datetime.now().isoformat()


def get_by_category(category: str, active_only: bool = True) -> list[dict]:
    conn = get_connection()
    try:
        q = "SELECT * FROM mutual_funds WHERE fund_category = ?"
        params = [category]
        if active_only:
            q += " AND is_active = 1"
        q += " ORDER BY fund_name"
        return [dict(r) for r in conn.execute(q, params).fetchall()]
    finally:
        conn.close()


def get_all_active() -> list[dict]:
    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM mutual_funds WHERE is_active = 1 ORDER BY fund_category, fund_name"
        ).fetchall()]
    finally:
        conn.close()


def get_by_id(fund_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM mutual_funds WHERE id = ?", (fund_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add(data: dict) -> int:
    now = _now()
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO mutual_funds (fund_name, amfi_code, fund_category, units, avg_nav, "
            "purchase_value, current_nav, purchase_date, folio_number, is_active, notes, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)",
            (
                data["fund_name"], data.get("amfi_code", ""), data["fund_category"],
                data["units"], data["avg_nav"], data["purchase_value"],
                data["current_nav"], data["purchase_date"],
                data.get("folio_number", ""), data.get("notes", ""), now, now,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update(fund_id: int, data: dict) -> None:
    now = _now()
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE mutual_funds SET fund_name=?, amfi_code=?, fund_category=?, units=?, avg_nav=?, "
            "purchase_value=?, current_nav=?, purchase_date=?, folio_number=?, is_active=?, notes=?, updated_at=? "
            "WHERE id=?",
            (
                data["fund_name"], data.get("amfi_code", ""), data["fund_category"],
                data["units"], data["avg_nav"], data["purchase_value"],
                data["current_nav"], data["purchase_date"],
                data.get("folio_number", ""), data.get("is_active", 1),
                data.get("notes", ""), now, fund_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_nav(fund_id: int, new_nav: float) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE mutual_funds SET current_nav = ?, updated_at = ? WHERE id = ?",
            (new_nav, _now(), fund_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete(fund_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM mutual_funds WHERE id = ?", (fund_id,))
        conn.commit()
    finally:
        conn.close()

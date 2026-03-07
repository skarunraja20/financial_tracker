"""Equity asset models: Stocks (NSE/BSE)."""

from datetime import datetime
from app.core.database import get_connection


def _now() -> str:
    return datetime.now().isoformat()


def get_all_stocks(active_only: bool = True) -> list[dict]:
    conn = get_connection()
    try:
        q = "SELECT * FROM stocks"
        if active_only:
            q += " WHERE is_active = 1"
        q += " ORDER BY company_name"
        return [dict(r) for r in conn.execute(q).fetchall()]
    finally:
        conn.close()


def add_stock(data: dict) -> int:
    now = _now()
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO stocks (company_name, ticker_symbol, exchange, quantity, avg_buy_price, "
            "purchase_value, current_price, purchase_date, demat_account, is_active, notes, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)",
            (
                data["company_name"], data["ticker_symbol"].upper(),
                data.get("exchange", "NSE").upper(),
                data["quantity"], data["avg_buy_price"], data["purchase_value"],
                data["current_price"], data["purchase_date"],
                data.get("demat_account", ""), data.get("notes", ""), now, now,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_stock(stock_id: int, data: dict) -> None:
    now = _now()
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE stocks SET company_name=?, ticker_symbol=?, exchange=?, quantity=?, avg_buy_price=?, "
            "purchase_value=?, current_price=?, purchase_date=?, demat_account=?, is_active=?, notes=?, updated_at=? "
            "WHERE id=?",
            (
                data["company_name"], data["ticker_symbol"].upper(),
                data.get("exchange", "NSE").upper(),
                data["quantity"], data["avg_buy_price"], data["purchase_value"],
                data["current_price"], data["purchase_date"],
                data.get("demat_account", ""), data.get("is_active", 1),
                data.get("notes", ""), now, stock_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_price(stock_id: int, new_price: float) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE stocks SET current_price = ?, updated_at = ? WHERE id = ?",
            (new_price, _now(), stock_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_stock(stock_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM stocks WHERE id = ?", (stock_id,))
        conn.commit()
    finally:
        conn.close()

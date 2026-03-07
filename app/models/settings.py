"""Settings model: key/value store for app preferences."""

from datetime import datetime
from app.core.database import get_connection
from app.core.constants import (
    SETTING_USD_RATE, SETTING_GOLD_PRICE, SETTING_THEME,
    SETTING_GOLD_UPDATED, DEFAULT_USD_RATE, DEFAULT_GOLD_PRICE,
)


def get(key: str, default=None):
    """Retrieve a setting value by key."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


def set(key: str, value) -> None:
    """Insert or update a setting."""
    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, str(value), now),
        )
        conn.commit()
    finally:
        conn.close()


def get_usd_rate() -> float:
    return float(get(SETTING_USD_RATE, DEFAULT_USD_RATE))


def set_usd_rate(rate: float) -> None:
    set(SETTING_USD_RATE, rate)


def get_gold_price() -> float:
    return float(get(SETTING_GOLD_PRICE, DEFAULT_GOLD_PRICE))


def set_gold_price(price: float) -> None:
    set(SETTING_GOLD_PRICE, price)
    set(SETTING_GOLD_UPDATED, datetime.now().isoformat())


def get_gold_last_updated() -> str | None:
    return get(SETTING_GOLD_UPDATED)


def get_theme() -> str:
    return get(SETTING_THEME, "dark")


def set_theme(theme: str) -> None:
    set(SETTING_THEME, theme)


def get_all() -> dict:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT key, value, updated_at FROM settings").fetchall()
        return {r["key"]: {"value": r["value"], "updated_at": r["updated_at"]} for r in rows}
    finally:
        conn.close()

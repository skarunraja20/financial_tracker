"""Networth snapshot CRUD."""

from datetime import datetime, date
from app.core.database import get_connection


def _now() -> str:
    return datetime.now().isoformat()


def save_snapshot(data: dict) -> int:
    """Insert a networth snapshot. data keys must match table columns."""
    now = _now()
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO networth_snapshots (
                snapshot_date, snapshot_type,
                total_pf, total_ppf, total_nps,
                total_fd, total_bonds, total_debt_mf,
                total_equity_mf, total_stocks, total_gold_mf, total_sgb, total_real_estate,
                total_home_loans, total_personal_loans, total_gold_loans, total_mf_loans,
                total_debt_assets, total_equity_assets, total_gold_assets,
                gross_assets, total_liabilities, net_worth,
                usd_to_inr_rate, net_worth_usd, gold_price_per_gram,
                notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("snapshot_date", date.today().isoformat()),
                data.get("snapshot_type", "manual"),
                data.get("total_pf", 0), data.get("total_ppf", 0), data.get("total_nps", 0),
                data.get("total_fd", 0),
                data.get("total_bonds", 0), data.get("total_debt_mf", 0),
                data.get("total_equity_mf", 0), data.get("total_stocks", 0),
                data.get("total_gold_mf", 0), data.get("total_sgb", 0),
                data.get("total_real_estate", 0),
                data.get("total_home_loans", 0), data.get("total_personal_loans", 0),
                data.get("total_gold_loans", 0), data.get("total_mf_loans", 0),
                data.get("total_debt_assets", 0), data.get("total_equity_assets", 0),
                data.get("total_gold_assets", 0),
                data.get("gross_assets", 0), data.get("total_liabilities", 0),
                data.get("net_worth", 0),
                data.get("usd_to_inr_rate"), data.get("net_worth_usd"),
                data.get("gold_price_per_gram"),
                data.get("notes", ""), now,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_all_snapshots(limit: int = 0) -> list[dict]:
    conn = get_connection()
    try:
        q = "SELECT * FROM networth_snapshots ORDER BY snapshot_date DESC"
        if limit > 0:
            q += f" LIMIT {limit}"
        return [dict(r) for r in conn.execute(q).fetchall()]
    finally:
        conn.close()


def get_snapshot_for_month(year: int, month: int) -> dict | None:
    """Return the snapshot for a given month, if any."""
    prefix = f"{year:04d}-{month:02d}"
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM networth_snapshots WHERE snapshot_date LIKE ? ORDER BY snapshot_date DESC LIMIT 1",
            (f"{prefix}%",),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_snapshot(snapshot_id: int, data: dict) -> None:
    """Update an existing snapshot row (used when re-snapshotting same month)."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE networth_snapshots SET
                total_pf=?, total_ppf=?, total_nps=?,
                total_fd=?, total_bonds=?, total_debt_mf=?,
                total_equity_mf=?, total_stocks=?, total_gold_mf=?, total_sgb=?, total_real_estate=?,
                total_home_loans=?, total_personal_loans=?, total_gold_loans=?, total_mf_loans=?,
                total_debt_assets=?, total_equity_assets=?, total_gold_assets=?,
                gross_assets=?, total_liabilities=?, net_worth=?,
                usd_to_inr_rate=?, net_worth_usd=?, gold_price_per_gram=?, notes=?
            WHERE id=?""",
            (
                data.get("total_pf", 0), data.get("total_ppf", 0), data.get("total_nps", 0),
                data.get("total_fd", 0),
                data.get("total_bonds", 0), data.get("total_debt_mf", 0),
                data.get("total_equity_mf", 0), data.get("total_stocks", 0),
                data.get("total_gold_mf", 0), data.get("total_sgb", 0),
                data.get("total_real_estate", 0),
                data.get("total_home_loans", 0), data.get("total_personal_loans", 0),
                data.get("total_gold_loans", 0), data.get("total_mf_loans", 0),
                data.get("total_debt_assets", 0), data.get("total_equity_assets", 0),
                data.get("total_gold_assets", 0),
                data.get("gross_assets", 0), data.get("total_liabilities", 0),
                data.get("net_worth", 0),
                data.get("usd_to_inr_rate"), data.get("net_worth_usd"),
                data.get("gold_price_per_gram"),
                data.get("notes", ""), snapshot_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_snapshot(snapshot_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM networth_snapshots WHERE id = ?", (snapshot_id,))
        conn.commit()
    finally:
        conn.close()


def get_snapshots_for_chart(months: int = 0) -> list[dict]:
    """Return snapshots for chart display, oldest first. months=0 means all."""
    conn = get_connection()
    try:
        if months > 0:
            q = ("SELECT * FROM networth_snapshots ORDER BY snapshot_date DESC LIMIT ?")
            rows = conn.execute(q, (months,)).fetchall()
            rows = list(reversed(rows))
        else:
            rows = conn.execute(
                "SELECT * FROM networth_snapshots ORDER BY snapshot_date ASC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

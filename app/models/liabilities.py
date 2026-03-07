"""Liabilities model: Home Loan, Personal Loan, Gold Loan, MF Loan."""

from datetime import datetime
from app.core.database import get_connection
from app.core.constants import LOAN_HOME, LOAN_PERSONAL, LOAN_GOLD, LOAN_MF


def _now() -> str:
    return datetime.now().isoformat()


def get_all(active_only: bool = True, loan_type: str | None = None) -> list[dict]:
    conn = get_connection()
    try:
        conditions = []
        params = []
        if active_only:
            conditions.append("l.is_active = 1")
        if loan_type:
            conditions.append("loan_type = ?")
            params.append(loan_type)
        q = "SELECT l.*, re.property_name, mf.fund_name FROM liabilities l "
        q += "LEFT JOIN real_estate re ON l.linked_property_id = re.id "
        q += "LEFT JOIN mutual_funds mf ON l.linked_fund_id = mf.id"
        if conditions:
            q += " WHERE " + " AND ".join(conditions)
        q += " ORDER BY loan_type, lender_name"
        return [dict(r) for r in conn.execute(q, params).fetchall()]
    finally:
        conn.close()


def get_totals_by_type() -> dict[str, float]:
    """Return outstanding totals per loan type for dashboard/snapshot."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT loan_type, SUM(outstanding_amount) AS total FROM liabilities "
            "WHERE is_active = 1 GROUP BY loan_type"
        ).fetchall()
        result = {LOAN_HOME: 0.0, LOAN_PERSONAL: 0.0, LOAN_GOLD: 0.0, LOAN_MF: 0.0}
        for r in rows:
            if r["loan_type"] in result:
                result[r["loan_type"]] = r["total"] or 0.0
        return result
    finally:
        conn.close()


def add(data: dict) -> int:
    now = _now()
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO liabilities (loan_type, lender_name, loan_account, original_amount, "
            "outstanding_amount, interest_rate, emi_amount, sanction_date, loan_end_date, "
            "linked_property_id, linked_fund_id, gold_weight_grams, purpose, is_active, notes, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)",
            (
                data["loan_type"], data["lender_name"], data.get("loan_account", ""),
                data["original_amount"], data["outstanding_amount"],
                data["interest_rate"], data.get("emi_amount"),
                data["sanction_date"], data.get("loan_end_date"),
                data.get("linked_property_id"), data.get("linked_fund_id"),
                data.get("gold_weight_grams"), data.get("purpose"),
                data.get("notes", ""), now, now,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update(liability_id: int, data: dict) -> None:
    now = _now()
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE liabilities SET loan_type=?, lender_name=?, loan_account=?, original_amount=?, "
            "outstanding_amount=?, interest_rate=?, emi_amount=?, sanction_date=?, loan_end_date=?, "
            "linked_property_id=?, linked_fund_id=?, gold_weight_grams=?, purpose=?, is_active=?, "
            "notes=?, updated_at=? WHERE id=?",
            (
                data["loan_type"], data["lender_name"], data.get("loan_account", ""),
                data["original_amount"], data["outstanding_amount"],
                data["interest_rate"], data.get("emi_amount"),
                data["sanction_date"], data.get("loan_end_date"),
                data.get("linked_property_id"), data.get("linked_fund_id"),
                data.get("gold_weight_grams"), data.get("purpose"),
                data.get("is_active", 1), data.get("notes", ""), now, liability_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_outstanding(liability_id: int, outstanding: float) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE liabilities SET outstanding_amount = ?, updated_at = ? WHERE id = ?",
            (outstanding, _now(), liability_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete(liability_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM liabilities WHERE id = ?", (liability_id,))
        conn.commit()
    finally:
        conn.close()

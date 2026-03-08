"""Debt asset models: PF, Fixed Deposits, Bonds, Debt Mutual Funds."""

from datetime import datetime, date
from app.core.database import get_connection
from app.core.constants import FUND_CATEGORY_DEBT


def _now() -> str:
    return datetime.now().isoformat()


def _today() -> str:
    return date.today().isoformat()


# ── PF ────────────────────────────────────────────────────────────────────────

def get_pf() -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM pf_account WHERE id = 1").fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def save_pf(total_balance: float, as_of_date: str, account_number: str = "", notes: str = "") -> None:
    now = _now()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO pf_account (id, account_number, total_balance, as_of_date, notes, updated_at) "
            "VALUES (1, ?, ?, ?, ?, ?)",
            (account_number, total_balance, as_of_date, notes, now),
        )
        conn.commit()
    finally:
        conn.close()


# ── PPF ───────────────────────────────────────────────────────────────────────

def get_ppf() -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM ppf_account WHERE id = 1").fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def save_ppf(
    current_balance: float,
    as_of_date: str,
    account_number: str = "",
    bank_name: str = "",
    opening_date: str = "",
    maturity_date: str = "",
    annual_contribution: float = 0.0,
    interest_rate: float = 7.1,
    notes: str = "",
) -> None:
    now = _now()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO ppf_account "
            "(id, account_number, bank_name, opening_date, maturity_date, "
            "current_balance, annual_contribution, interest_rate, as_of_date, notes, updated_at) "
            "VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (account_number, bank_name, opening_date, maturity_date,
             current_balance, annual_contribution, interest_rate, as_of_date, notes, now),
        )
        conn.commit()
    finally:
        conn.close()


# ── NPS ───────────────────────────────────────────────────────────────────────

def get_nps() -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM nps_account WHERE id = 1").fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def save_nps(
    tier1_corpus: float,
    as_of_date: str,
    pran_number: str = "",
    pfm_name: str = "",
    tier1_contributions: float = 0.0,
    tier2_corpus: float = 0.0,
    tier2_contributions: float = 0.0,
    equity_pct: float = 0.0,
    govt_pct: float = 0.0,
    corp_pct: float = 0.0,
    notes: str = "",
) -> None:
    now = _now()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO nps_account "
            "(id, pran_number, pfm_name, tier1_corpus, tier1_contributions, "
            "tier2_corpus, tier2_contributions, equity_pct, govt_pct, corp_pct, "
            "as_of_date, notes, updated_at) "
            "VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (pran_number, pfm_name, tier1_corpus, tier1_contributions,
             tier2_corpus, tier2_contributions, equity_pct, govt_pct, corp_pct,
             as_of_date, notes, now),
        )
        conn.commit()
    finally:
        conn.close()


# ── Fixed Deposits ─────────────────────────────────────────────────────────────

def get_all_fds(active_only: bool = True) -> list[dict]:
    conn = get_connection()
    try:
        q = "SELECT * FROM fixed_deposits"
        if active_only:
            q += " WHERE is_active = 1"
        q += " ORDER BY maturity_date"
        return [dict(r) for r in conn.execute(q).fetchall()]
    finally:
        conn.close()


def add_fd(data: dict) -> int:
    now = _now()
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO fixed_deposits (bank_name, fd_number, principal, interest_rate, compounding, "
            "start_date, maturity_date, maturity_amount, current_value, is_active, notes, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)",
            (
                data["bank_name"], data.get("fd_number", ""), data["principal"],
                data["interest_rate"], data.get("compounding", "quarterly"),
                data["start_date"], data["maturity_date"],
                data.get("maturity_amount"), data.get("current_value"),
                data.get("notes", ""), now, now,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_fd(fd_id: int, data: dict) -> None:
    now = _now()
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE fixed_deposits SET bank_name=?, fd_number=?, principal=?, interest_rate=?, "
            "compounding=?, start_date=?, maturity_date=?, maturity_amount=?, current_value=?, "
            "is_active=?, notes=?, updated_at=? WHERE id=?",
            (
                data["bank_name"], data.get("fd_number", ""), data["principal"],
                data["interest_rate"], data.get("compounding", "quarterly"),
                data["start_date"], data["maturity_date"],
                data.get("maturity_amount"), data.get("current_value"),
                data.get("is_active", 1), data.get("notes", ""), now, fd_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_fd(fd_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM fixed_deposits WHERE id = ?", (fd_id,))
        conn.commit()
    finally:
        conn.close()


def calculate_fd_value(principal: float, rate: float, compounding: str, start_date_str: str) -> float:
    """Calculate current value using compound/simple interest formula."""
    try:
        start = date.fromisoformat(start_date_str)
        years = (date.today() - start).days / 365.25
        n_map = {"monthly": 12, "quarterly": 4, "yearly": 1, "simple": 0}
        n = n_map.get(compounding, 4)
        if n == 0:
            return principal * (1 + (rate / 100) * years)
        return principal * ((1 + (rate / 100) / n) ** (n * years))
    except Exception:
        return principal


# ── Bonds ─────────────────────────────────────────────────────────────────────

def get_all_bonds(active_only: bool = True) -> list[dict]:
    conn = get_connection()
    try:
        q = "SELECT * FROM bonds"
        if active_only:
            q += " WHERE is_active = 1"
        q += " ORDER BY bond_name"
        return [dict(r) for r in conn.execute(q).fetchall()]
    finally:
        conn.close()


def add_bond(data: dict) -> int:
    now = _now()
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO bonds (bond_name, issuer, bond_type, face_value, units, purchase_price, "
            "coupon_rate, purchase_date, maturity_date, current_price, is_active, notes, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)",
            (
                data["bond_name"], data["issuer"], data["bond_type"],
                data["face_value"], data["units"], data["purchase_price"],
                data.get("coupon_rate"), data["purchase_date"],
                data.get("maturity_date"), data.get("current_price", data["purchase_price"]),
                data.get("notes", ""), now, now,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_bond(bond_id: int, data: dict) -> None:
    now = _now()
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE bonds SET bond_name=?, issuer=?, bond_type=?, face_value=?, units=?, "
            "purchase_price=?, coupon_rate=?, purchase_date=?, maturity_date=?, current_price=?, "
            "is_active=?, notes=?, updated_at=? WHERE id=?",
            (
                data["bond_name"], data["issuer"], data["bond_type"],
                data["face_value"], data["units"], data["purchase_price"],
                data.get("coupon_rate"), data["purchase_date"],
                data.get("maturity_date"), data.get("current_price"),
                data.get("is_active", 1), data.get("notes", ""), now, bond_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_bond(bond_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM bonds WHERE id = ?", (bond_id,))
        conn.commit()
    finally:
        conn.close()


# ── Debt Mutual Funds (shared table with equity/gold MF) ─────────────────────

def get_all_debt_mfs(active_only: bool = True) -> list[dict]:
    conn = get_connection()
    try:
        q = "SELECT * FROM mutual_funds WHERE fund_category = 'debt'"
        if active_only:
            q += " AND is_active = 1"
        q += " ORDER BY fund_name"
        return [dict(r) for r in conn.execute(q).fetchall()]
    finally:
        conn.close()

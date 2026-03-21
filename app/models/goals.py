"""
CRUD operations for Goals and asset-goal linking.
Also provides current-value calculation for any tagged asset.
"""

from datetime import datetime
from app.core.database import get_connection
from app.core.constants import (
    ASSET_TYPE_PF, ASSET_TYPE_FD, ASSET_TYPE_BONDS, ASSET_TYPE_DEBT_MF,
    ASSET_TYPE_EQUITY_MF, ASSET_TYPE_STOCKS, ASSET_TYPE_GOLD_MF,
    ASSET_TYPE_SGB, ASSET_TYPE_REAL_ESTATE,
    SETTING_GOLD_PRICE,
)


# ── Goal CRUD ─────────────────────────────────────────────────────────────────

def get_all_goals() -> list[dict]:
    """Return all active goals, ordered by creation date."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM goals WHERE is_active = 1 ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_goal(goal_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM goals WHERE id = ?", (goal_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_goal(name: str, target_amount: float, description: str = "",
             color: str = "#14b8a6", icon: str = "🎯",
             deadline: str | None = None) -> int:
    """Insert a new goal. Returns the new goal id."""
    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO goals
               (name, description, target_amount, color, icon, deadline,
                is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)""",
            (name, description, target_amount, color, icon, deadline, now, now)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_goal(goal_id: int, name: str, target_amount: float,
                description: str = "", color: str = "#14b8a6",
                icon: str = "🎯", deadline: str | None = None) -> None:
    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE goals SET name=?, description=?, target_amount=?,
               color=?, icon=?, deadline=?, updated_at=?
               WHERE id=?""",
            (name, description, target_amount, color, icon, deadline, now, goal_id)
        )
        conn.commit()
    finally:
        conn.close()


def delete_goal(goal_id: int) -> None:
    """Soft-delete a goal (asset_goals rows cascade-deleted)."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM goals WHERE id=?", (goal_id,))
        conn.commit()
    finally:
        conn.close()


# ── Asset-Goal linking ────────────────────────────────────────────────────────

def get_tagged_assets(goal_id: int) -> list[dict]:
    """Return all asset_goals rows for a given goal."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM asset_goals WHERE goal_id=? ORDER BY asset_type, asset_id",
            (goal_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def tag_asset(goal_id: int, asset_type: str, asset_id: int,
              notes: str = "") -> None:
    """Link an asset to a goal (ignore if already linked)."""
    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO asset_goals
               (goal_id, asset_type, asset_id, notes, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (goal_id, asset_type, asset_id, notes, now)
        )
        conn.commit()
    finally:
        conn.close()


def untag_asset(goal_id: int, asset_type: str, asset_id: int) -> None:
    """Remove an asset from a goal."""
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM asset_goals WHERE goal_id=? AND asset_type=? AND asset_id=?",
            (goal_id, asset_type, asset_id)
        )
        conn.commit()
    finally:
        conn.close()


def set_tagged_assets(goal_id: int, asset_list: list[tuple]) -> None:
    """
    Replace ALL tagged assets for a goal with the provided list.
    asset_list: [(asset_type, asset_id), ...]
    """
    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM asset_goals WHERE goal_id=?", (goal_id,))
        for asset_type, asset_id in asset_list:
            conn.execute(
                """INSERT INTO asset_goals
                   (goal_id, asset_type, asset_id, notes, created_at)
                   VALUES (?, ?, ?, '', ?)""",
                (goal_id, asset_type, asset_id, now)
            )
        conn.commit()
    finally:
        conn.close()


def get_goal_to_assets_map() -> dict[int, list[tuple]]:
    """Return {goal_id: [(asset_type, asset_id), ...]} for all goals."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT goal_id, asset_type, asset_id FROM asset_goals"
        ).fetchall()
        result: dict[int, list] = {}
        for r in rows:
            result.setdefault(r["goal_id"], []).append(
                (r["asset_type"], r["asset_id"])
            )
        return result
    finally:
        conn.close()


# ── Current value lookup per asset ───────────────────────────────────────────

def _get_gold_price() -> float:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key=?", (SETTING_GOLD_PRICE,)
        ).fetchone()
        return float(row["value"]) if row else 6500.0
    finally:
        conn.close()


def get_asset_current_value(asset_type: str, asset_id: int) -> float:
    """Return the current INR value of a single asset by type and id."""
    conn = get_connection()
    try:
        if asset_type == ASSET_TYPE_PF:
            row = conn.execute(
                "SELECT total_balance FROM pf_account WHERE id=?", (asset_id,)
            ).fetchone()
            return float(row["total_balance"]) if row else 0.0

        elif asset_type == ASSET_TYPE_FD:
            row = conn.execute(
                """SELECT principal, interest_rate, compounding,
                          start_date, maturity_date, maturity_amount, current_value
                   FROM fixed_deposits WHERE id=?""", (asset_id,)
            ).fetchone()
            if not row:
                return 0.0
            if row["current_value"]:
                return float(row["current_value"])
            if row["maturity_amount"]:
                return float(row["maturity_amount"])
            # Compute compound interest
            return _compute_fd_value(dict(row))

        elif asset_type == ASSET_TYPE_BONDS:
            row = conn.execute(
                "SELECT face_value, units, purchase_price, current_price FROM bonds WHERE id=?",
                (asset_id,)
            ).fetchone()
            if not row:
                return 0.0
            cp = row["current_price"] if row["current_price"] else row["purchase_price"]
            return float(row["units"]) * float(cp)

        elif asset_type in (ASSET_TYPE_DEBT_MF, ASSET_TYPE_EQUITY_MF, ASSET_TYPE_GOLD_MF):
            row = conn.execute(
                "SELECT units, current_nav FROM mutual_funds WHERE id=?", (asset_id,)
            ).fetchone()
            return float(row["units"]) * float(row["current_nav"]) if row else 0.0

        elif asset_type == ASSET_TYPE_STOCKS:
            row = conn.execute(
                "SELECT quantity, current_price FROM stocks WHERE id=?", (asset_id,)
            ).fetchone()
            return float(row["quantity"]) * float(row["current_price"]) if row else 0.0

        elif asset_type == ASSET_TYPE_SGB:
            row = conn.execute(
                "SELECT units FROM sgb WHERE id=?", (asset_id,)
            ).fetchone()
            if not row:
                return 0.0
            gold_price = _get_gold_price()
            # SGB standard: 1 unit = 1 gram
            return float(row["units"]) * gold_price

        elif asset_type == ASSET_TYPE_REAL_ESTATE:
            row = conn.execute(
                "SELECT current_value FROM real_estate WHERE id=?", (asset_id,)
            ).fetchone()
            return float(row["current_value"]) if row else 0.0

        return 0.0
    finally:
        conn.close()


def _compute_fd_value(row: dict) -> float:
    """Approximate FD current value using compound interest."""
    from datetime import date
    try:
        start = date.fromisoformat(row["start_date"])
        today = date.today()
        years = (today - start).days / 365.25
        if years <= 0:
            return float(row["principal"])
        r = float(row["interest_rate"]) / 100
        P = float(row["principal"])
        comp = row.get("compounding", "quarterly")
        n_map = {"monthly": 12, "quarterly": 4, "yearly": 1, "simple": 0}
        n = n_map.get(comp, 4)
        if n == 0:  # simple interest
            return P * (1 + r * years)
        return P * ((1 + r / n) ** (n * years))
    except Exception:
        return float(row.get("principal", 0))


# ── Asset class groupings ─────────────────────────────────────────────────────

_DEBT_TYPES = {ASSET_TYPE_PF, ASSET_TYPE_FD, ASSET_TYPE_BONDS, ASSET_TYPE_DEBT_MF}
_EQUITY_TYPES = {ASSET_TYPE_EQUITY_MF, ASSET_TYPE_STOCKS}
_GOLD_TYPES = {ASSET_TYPE_GOLD_MF, ASSET_TYPE_SGB}
_REAL_ESTATE_TYPES = {ASSET_TYPE_REAL_ESTATE}


def get_goal_allocation(goal_id: int) -> dict:
    """
    Returns asset-class allocation for all tagged assets of a goal.
    Result keys: debt, equity, gold, real_estate, total (all floats).
    """
    tagged = get_tagged_assets(goal_id)
    buckets = {"debt": 0.0, "equity": 0.0, "gold": 0.0, "real_estate": 0.0}
    for t in tagged:
        val = get_asset_current_value(t["asset_type"], t["asset_id"])
        at = t["asset_type"]
        if at in _DEBT_TYPES:
            buckets["debt"] += val
        elif at in _EQUITY_TYPES:
            buckets["equity"] += val
        elif at in _GOLD_TYPES:
            buckets["gold"] += val
        elif at in _REAL_ESTATE_TYPES:
            buckets["real_estate"] += val
    buckets["total"] = sum(buckets[k] for k in ("debt", "equity", "gold", "real_estate"))
    return buckets


# ── Goal progress calculation ─────────────────────────────────────────────────

def calculate_goal_progress(goal_id: int) -> tuple[float, float]:
    """
    Returns (current_amount, target_amount) for a goal.
    current_amount = sum of current values of all tagged assets.
    """
    goal = get_goal(goal_id)
    if not goal:
        return 0.0, 0.0
    tagged = get_tagged_assets(goal_id)
    current = sum(
        get_asset_current_value(t["asset_type"], t["asset_id"])
        for t in tagged
    )
    return current, float(goal["target_amount"])


def get_all_goals_with_progress() -> list[dict]:
    """
    Returns all goals enriched with current_amount and percentage.
    """
    goals = get_all_goals()
    for g in goals:
        current, target = calculate_goal_progress(g["id"])
        g["current_amount"] = current
        g["percentage"] = min(current / target * 100, 100) if target > 0 else 0.0
        tagged = get_tagged_assets(g["id"])
        g["tagged_count"] = len(tagged)
        g["allocation"] = get_goal_allocation(g["id"])
    return goals


# ── All available assets (for tagging dialog) ─────────────────────────────────

def get_all_assets_for_tagging(goal_id: int) -> dict[str, list[dict]]:
    """
    Returns a dict keyed by asset_type, each value is a list of asset dicts
    with 'id', 'name', 'current_value', 'is_tagged' (bool for this goal).
    """
    conn = get_connection()
    try:
        tagged_rows = conn.execute(
            "SELECT asset_type, asset_id FROM asset_goals WHERE goal_id=?",
            (goal_id,)
        ).fetchall()
        tagged_set = {(r["asset_type"], r["asset_id"]) for r in tagged_rows}

        result: dict[str, list] = {}

        # PF (single row, id=1)
        pf = conn.execute(
            "SELECT id, total_balance FROM pf_account"
        ).fetchone()
        if pf:
            result[ASSET_TYPE_PF] = [{
                "id": pf["id"], "name": "Provident Fund (PF)",
                "current_value": float(pf["total_balance"]),
                "is_tagged": (ASSET_TYPE_PF, pf["id"]) in tagged_set,
            }]

        # FD
        fds = conn.execute(
            "SELECT id, bank_name, principal FROM fixed_deposits WHERE is_active=1"
        ).fetchall()
        if fds:
            result[ASSET_TYPE_FD] = [{
                "id": r["id"], "name": r["bank_name"],
                "current_value": get_asset_current_value(ASSET_TYPE_FD, r["id"]),
                "is_tagged": (ASSET_TYPE_FD, r["id"]) in tagged_set,
            } for r in fds]

        # Bonds
        bonds = conn.execute(
            "SELECT id, bond_name FROM bonds WHERE is_active=1"
        ).fetchall()
        if bonds:
            result[ASSET_TYPE_BONDS] = [{
                "id": r["id"], "name": r["bond_name"],
                "current_value": get_asset_current_value(ASSET_TYPE_BONDS, r["id"]),
                "is_tagged": (ASSET_TYPE_BONDS, r["id"]) in tagged_set,
            } for r in bonds]

        # Mutual funds (all categories)
        mfs = conn.execute(
            "SELECT id, fund_name, fund_category FROM mutual_funds WHERE is_active=1"
        ).fetchall()
        cat_to_type = {"debt": ASSET_TYPE_DEBT_MF, "equity": ASSET_TYPE_EQUITY_MF,
                       "gold": ASSET_TYPE_GOLD_MF}
        for r in mfs:
            at = cat_to_type.get(r["fund_category"], ASSET_TYPE_DEBT_MF)
            result.setdefault(at, []).append({
                "id": r["id"], "name": r["fund_name"],
                "current_value": get_asset_current_value(at, r["id"]),
                "is_tagged": (at, r["id"]) in tagged_set,
            })

        # Stocks
        stocks = conn.execute(
            "SELECT id, company_name, ticker_symbol FROM stocks WHERE is_active=1"
        ).fetchall()
        if stocks:
            result[ASSET_TYPE_STOCKS] = [{
                "id": r["id"],
                "name": f"{r['company_name']} ({r['ticker_symbol']})",
                "current_value": get_asset_current_value(ASSET_TYPE_STOCKS, r["id"]),
                "is_tagged": (ASSET_TYPE_STOCKS, r["id"]) in tagged_set,
            } for r in stocks]

        # SGB
        sgbs = conn.execute(
            "SELECT id, series_name FROM sgb WHERE is_active=1"
        ).fetchall()
        if sgbs:
            result[ASSET_TYPE_SGB] = [{
                "id": r["id"], "name": r["series_name"],
                "current_value": get_asset_current_value(ASSET_TYPE_SGB, r["id"]),
                "is_tagged": (ASSET_TYPE_SGB, r["id"]) in tagged_set,
            } for r in sgbs]

        # Real estate
        props = conn.execute(
            "SELECT id, property_name FROM real_estate"
        ).fetchall()
        if props:
            result[ASSET_TYPE_REAL_ESTATE] = [{
                "id": r["id"], "name": r["property_name"],
                "current_value": get_asset_current_value(ASSET_TYPE_REAL_ESTATE, r["id"]),
                "is_tagged": (ASSET_TYPE_REAL_ESTATE, r["id"]) in tagged_set,
            } for r in props]

        return result
    finally:
        conn.close()

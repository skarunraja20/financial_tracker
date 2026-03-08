"""
Networth calculation service.
Computes current values for all asset types and builds snapshot data.
"""

import math
from datetime import date
from app.models import debt as debt_model
from app.models import mutual_fund as mf_model
from app.models import equity as equity_model
from app.models import gold as gold_model
from app.models import real_estate as re_model
from app.models import liabilities as liab_model
from app.models import settings as settings_model
from app.models import networth as nw_model
from app.core.constants import FUND_CATEGORY_DEBT, FUND_CATEGORY_EQUITY, FUND_CATEGORY_GOLD


def _safe_amount(val, default: float = 0.0) -> float:
    """Return val as a finite non-negative float, or default.

    Guards net-worth calculations against NaN / Inf / negative values
    that could enter via a hand-edited SQLite database.
    """
    try:
        f = float(val)
        return f if math.isfinite(f) and f >= 0.0 else default
    except (TypeError, ValueError):
        return default


def calculate_current_values() -> dict:
    """
    Compute live current values for all asset and liability categories.
    Returns a structured dict suitable for dashboard display and snapshot creation.
    """
    gold_price    = settings_model.get_gold_price()
    currency_info = settings_model.get_currency_info()   # {code, name, symbol, rate}

    # ── PF ────────────────────────────────────────────────────────────────────
    pf = debt_model.get_pf()
    total_pf = _safe_amount(pf["total_balance"]) if pf else 0.0

    # ── PPF ───────────────────────────────────────────────────────────────────
    ppf = debt_model.get_ppf()
    total_ppf = _safe_amount(ppf["current_balance"]) if ppf else 0.0

    # ── NPS ───────────────────────────────────────────────────────────────────
    nps = debt_model.get_nps()
    total_nps = (
        _safe_amount(nps.get("tier1_corpus", 0.0)) +
        _safe_amount(nps.get("tier2_corpus", 0.0))
    ) if nps else 0.0

    # ── Fixed Deposits ────────────────────────────────────────────────────────
    fds = debt_model.get_all_fds()
    total_fd = 0.0
    for fd in fds:
        if fd["maturity_amount"]:
            val = debt_model.calculate_fd_value(
                fd["principal"], fd["interest_rate"], fd["compounding"], fd["start_date"]
            )
            mat_date = date.fromisoformat(fd["maturity_date"])
            if date.today() >= mat_date:
                val = fd["maturity_amount"]
        elif fd.get("current_value"):
            val = fd["current_value"]
        else:
            val = debt_model.calculate_fd_value(
                fd["principal"], fd["interest_rate"], fd["compounding"], fd["start_date"]
            )
        total_fd += _safe_amount(val)

    # ── Bonds ─────────────────────────────────────────────────────────────────
    bonds = debt_model.get_all_bonds()
    total_bonds = sum(
        _safe_amount(b["current_price"] or b["purchase_price"]) * _safe_amount(b["units"])
        for b in bonds
    )

    # ── Debt MF ───────────────────────────────────────────────────────────────
    debt_mfs = mf_model.get_by_category(FUND_CATEGORY_DEBT)
    total_debt_mf = sum(
        _safe_amount(f["units"]) * _safe_amount(f["current_nav"]) for f in debt_mfs
    )

    # ── Equity MF ─────────────────────────────────────────────────────────────
    equity_mfs = mf_model.get_by_category(FUND_CATEGORY_EQUITY)
    total_equity_mf = sum(
        _safe_amount(f["units"]) * _safe_amount(f["current_nav"]) for f in equity_mfs
    )

    # ── Stocks ────────────────────────────────────────────────────────────────
    stocks = equity_model.get_all_stocks()
    total_stocks = sum(
        _safe_amount(s["quantity"]) * _safe_amount(s["current_price"]) for s in stocks
    )

    # ── Gold MF ───────────────────────────────────────────────────────────────
    gold_mfs = mf_model.get_by_category(FUND_CATEGORY_GOLD)
    total_gold_mf = sum(
        _safe_amount(f["units"]) * _safe_amount(f["current_nav"]) for f in gold_mfs
    )

    # ── SGB ───────────────────────────────────────────────────────────────────
    sgbs = gold_model.get_all_sgb()
    total_sgb = sum(_safe_amount(s["units"]) * _safe_amount(gold_price) for s in sgbs)

    # ── Real Estate ───────────────────────────────────────────────────────────
    properties = re_model.get_all_properties()
    total_real_estate = sum(_safe_amount(p["current_value"]) for p in properties)

    # ── Category aggregates ───────────────────────────────────────────────────
    total_debt_assets = total_pf + total_ppf + total_nps + total_fd + total_bonds + total_debt_mf
    total_equity_assets = total_equity_mf + total_stocks
    total_gold_assets = total_gold_mf + total_sgb
    gross_assets = total_debt_assets + total_equity_assets + total_gold_assets + total_real_estate

    # ── Liabilities ───────────────────────────────────────────────────────────
    liab_totals = liab_model.get_totals_by_type()
    total_home_loans = liab_totals.get("home_loan", 0.0)
    total_personal_loans = liab_totals.get("personal_loan", 0.0)
    total_gold_loans = liab_totals.get("gold_loan", 0.0)
    total_mf_loans = liab_totals.get("mf_loan", 0.0)
    total_liabilities = total_home_loans + total_personal_loans + total_gold_loans + total_mf_loans

    # ── Net Worth ─────────────────────────────────────────────────────────────
    net_worth = gross_assets - total_liabilities
    c_rate = currency_info["rate"]
    net_worth_foreign = net_worth / c_rate if c_rate > 0 else 0.0

    return {
        # Individual asset values
        "total_pf": total_pf,
        "total_ppf": total_ppf,
        "total_nps": total_nps,
        "total_fd": total_fd,
        "total_bonds": total_bonds,
        "total_debt_mf": total_debt_mf,
        "total_equity_mf": total_equity_mf,
        "total_stocks": total_stocks,
        "total_gold_mf": total_gold_mf,
        "total_sgb": total_sgb,
        "total_real_estate": total_real_estate,
        # Category totals
        "total_debt_assets": total_debt_assets,
        "total_equity_assets": total_equity_assets,
        "total_gold_assets": total_gold_assets,
        "gross_assets": gross_assets,
        # Liabilities
        "total_home_loans": total_home_loans,
        "total_personal_loans": total_personal_loans,
        "total_gold_loans": total_gold_loans,
        "total_mf_loans": total_mf_loans,
        "total_liabilities": total_liabilities,
        # Net
        "net_worth": net_worth,
        "net_worth_foreign": net_worth_foreign,   # in selected foreign currency
        # Currency meta (replaces old usd_to_inr_rate / net_worth_usd keys)
        "currency_code":   currency_info["code"],
        "currency_symbol": currency_info["symbol"],
        "currency_rate":   currency_info["rate"],
        # kept for any legacy code that reads usd_to_inr_rate
        "usd_to_inr_rate": currency_info["rate"],
        # Meta
        "gold_price_per_gram": gold_price,
        "snapshot_date": date.today().isoformat(),
    }


def save_snapshot(values: dict, notes: str = "") -> int:
    """Save current values as a networth snapshot. Handles month deduplication."""
    today = date.today()
    existing = nw_model.get_snapshot_for_month(today.year, today.month)
    values["notes"] = notes
    if existing:
        nw_model.update_snapshot(existing["id"], values)
        return existing["id"]
    else:
        return nw_model.save_snapshot(values)


def get_allocation_data(values: dict) -> list[tuple[str, float]]:
    """Return [(label, amount), ...] for pie chart, excluding zero values."""
    items = [
        ("PF", values["total_pf"]),
        ("PPF", values.get("total_ppf", 0)),
        ("NPS", values.get("total_nps", 0)),
        ("Fixed Deposits", values["total_fd"]),
        ("Bonds", values["total_bonds"]),
        ("Debt MF", values["total_debt_mf"]),
        ("Equity MF", values["total_equity_mf"]),
        ("Stocks", values["total_stocks"]),
        ("Gold MF", values["total_gold_mf"]),
        ("SGB", values["total_sgb"]),
        ("Real Estate", values["total_real_estate"]),
    ]
    return [(label, amt) for label, amt in items if amt > 0]

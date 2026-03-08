"""
CSV/Excel import service.
Validates, parses, and inserts records for each asset type.
"""

import os
import pandas as pd
from datetime import date
from app.models import debt as debt_model
from app.models import mutual_fund as mf_model
from app.models import equity as equity_model
from app.models import gold as gold_model
from app.core.constants import EXCHANGE_OPTIONS, COMPOUNDING_OPTIONS, BOND_TYPES
from app.core.database import get_connection
from datetime import datetime


REQUIRED_COLUMNS = {
    "fd": ["bank_name", "principal", "interest_rate", "compounding", "start_date", "maturity_date"],
    "bond": ["bond_name", "issuer", "bond_type", "face_value", "units", "purchase_price", "purchase_date"],
    "mutual_fund": ["fund_name", "units", "avg_nav", "purchase_value", "current_nav", "purchase_date"],
    "stock": ["company_name", "ticker_symbol", "exchange", "quantity", "avg_buy_price", "purchase_value",
              "current_price", "purchase_date"],
    "sgb": ["series_name", "units", "issue_price", "purchase_date", "maturity_date"],
}


_MAX_IMPORT_BYTES = 50 * 1024 * 1024  # 50 MB hard cap


def read_file(filepath: str) -> pd.DataFrame:
    """Read a CSV or Excel file into a DataFrame with normalized column names.

    Security hardening applied:
    - File size capped at 50 MB to prevent memory exhaustion.
    - Extension validated to .csv / .xlsx / .xls only.
    - Excel read with explicit engine='openpyxl' (no macro execution).
    """
    try:
        size = os.path.getsize(filepath)
    except OSError as exc:
        raise ValueError(f"Cannot access file: {exc}") from exc

    if size > _MAX_IMPORT_BYTES:
        mb = size // (1024 * 1024)
        raise ValueError(f"File is too large ({mb} MB). Maximum allowed is 50 MB.")

    lower = filepath.lower()
    if lower.endswith(".csv"):
        df = pd.read_csv(filepath, dtype=str)
    elif lower.endswith((".xlsx", ".xls")):
        # engine='openpyxl' disables DDE/macro evaluation
        df = pd.read_excel(filepath, dtype=str, engine="openpyxl")
    else:
        raise ValueError("Unsupported file type. Only .csv and .xlsx files are accepted.")

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df = df.fillna("")
    return df


def validate(df: pd.DataFrame, asset_type: str) -> tuple[list[dict], list[str]]:
    """
    Validate rows. Returns (valid_rows, errors).
    valid_rows: list of dicts ready to insert.
    errors: list of human-readable error strings.
    """
    required = REQUIRED_COLUMNS.get(asset_type, [])
    errors = []

    # Check required columns exist
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        return [], [f"Missing columns: {', '.join(missing_cols)}"]

    valid_rows = []
    for idx, row in df.iterrows():
        row_errors = []
        row_num = idx + 2  # 1-based + header row

        parsed = {}
        for col in required:
            val = str(row.get(col, "")).strip()
            if not val:
                row_errors.append(f"Row {row_num}: '{col}' is empty")

        if row_errors:
            errors.extend(row_errors)
            continue

        try:
            parsed = _parse_row(row, asset_type)
            valid_rows.append(parsed)
        except ValueError as e:
            errors.append(f"Row {row_num}: {e}")

    return valid_rows, errors


def _parse_row(row, asset_type: str) -> dict:
    """Parse and type-cast a single row. Raises ValueError on bad data."""
    def _float(col):
        try:
            return float(str(row.get(col, "")).strip())
        except (ValueError, TypeError):
            raise ValueError(f"'{col}' must be a number, got '{row.get(col)}'")

    def _date(col):
        val = str(row.get(col, "")).strip()
        try:
            date.fromisoformat(val)
            return val
        except ValueError:
            raise ValueError(f"'{col}' must be YYYY-MM-DD, got '{val}'")

    def _str(col, default=""):
        return str(row.get(col, default)).strip()

    if asset_type == "fd":
        compounding = _str("compounding", "quarterly").lower()
        if compounding not in COMPOUNDING_OPTIONS:
            raise ValueError(f"'compounding' must be one of {COMPOUNDING_OPTIONS}")
        return {
            "bank_name": _str("bank_name"),
            "fd_number": _str("fd_number"),
            "principal": _float("principal"),
            "interest_rate": _float("interest_rate"),
            "compounding": compounding,
            "start_date": _date("start_date"),
            "maturity_date": _date("maturity_date"),
            "maturity_amount": _float("maturity_amount") if _str("maturity_amount") else None,
            "notes": _str("notes"),
        }

    elif asset_type == "bond":
        bond_type = _str("bond_type").lower()
        if bond_type not in BOND_TYPES:
            raise ValueError(f"'bond_type' must be one of {BOND_TYPES}")
        return {
            "bond_name": _str("bond_name"),
            "issuer": _str("issuer"),
            "bond_type": bond_type,
            "face_value": _float("face_value"),
            "units": _float("units"),
            "purchase_price": _float("purchase_price"),
            "coupon_rate": _float("coupon_rate") if _str("coupon_rate") else None,
            "purchase_date": _date("purchase_date"),
            "maturity_date": _date("maturity_date") if _str("maturity_date") else None,
            "current_price": _float("current_price") if _str("current_price") else None,
            "notes": _str("notes"),
        }

    elif asset_type == "mutual_fund":
        return {
            "fund_name": _str("fund_name"),
            "amfi_code": _str("amfi_code"),
            "units": _float("units"),
            "avg_nav": _float("avg_nav"),
            "purchase_value": _float("purchase_value"),
            "current_nav": _float("current_nav"),
            "purchase_date": _date("purchase_date"),
            "folio_number": _str("folio_number"),
            "notes": _str("notes"),
        }

    elif asset_type == "stock":
        exchange = _str("exchange").upper()
        if exchange not in EXCHANGE_OPTIONS:
            raise ValueError(f"'exchange' must be NSE or BSE, got '{exchange}'")
        return {
            "company_name": _str("company_name"),
            "ticker_symbol": _str("ticker_symbol").upper(),
            "exchange": exchange,
            "quantity": _float("quantity"),
            "avg_buy_price": _float("avg_buy_price"),
            "purchase_value": _float("purchase_value"),
            "current_price": _float("current_price"),
            "purchase_date": _date("purchase_date"),
            "demat_account": _str("demat_account"),
            "notes": _str("notes"),
        }

    elif asset_type == "sgb":
        return {
            "series_name": _str("series_name"),
            "units": _float("units"),
            "issue_price": _float("issue_price"),
            "purchase_date": _date("purchase_date"),
            "maturity_date": _date("maturity_date"),
            "coupon_rate": _float("coupon_rate") if _str("coupon_rate") else 2.5,
            "notes": _str("notes"),
        }

    raise ValueError(f"Unknown asset type: {asset_type}")


def insert_rows(rows: list[dict], asset_type: str, fund_category: str = "") -> int:
    """Insert validated rows into the database. Returns count inserted."""
    count = 0
    for row in rows:
        if asset_type == "fd":
            debt_model.add_fd(row)
        elif asset_type == "bond":
            debt_model.add_bond(row)
        elif asset_type == "mutual_fund":
            row["fund_category"] = fund_category
            mf_model.add(row)
        elif asset_type == "stock":
            equity_model.add_stock(row)
        elif asset_type == "sgb":
            gold_model.add_sgb(row)
        count += 1
    return count


def log_import(asset_category: str, filename: str, imported: int, skipped: int,
               status: str, error_details: str = "") -> None:
    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO import_log (import_date, asset_category, filename, rows_imported, "
            "rows_skipped, status, error_details, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (now[:10], asset_category, filename, imported, skipped, status, error_details, now),
        )
        conn.commit()
    finally:
        conn.close()

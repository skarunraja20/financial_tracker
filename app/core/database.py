"""
Database initialisation: creates all tables and applies pragmas.
All tables use CREATE TABLE IF NOT EXISTS — safe to call on every startup.
"""

import sqlite3
import os
from app.core.constants import DB_PATH, BACKUP_DIR, DATA_DIR


def get_connection() -> sqlite3.Connection:
    """Return a configured sqlite3 connection."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def initialize_database() -> None:
    """Create all tables if they don't exist. Safe to call on every launch."""
    conn = get_connection()
    try:
        _create_tables(conn)
        _apply_migrations(conn)
        conn.commit()
    finally:
        conn.close()


def _apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply incremental schema changes for existing databases."""
    # Add PPF and NPS columns to networth_snapshots (added in v2)
    for col, default in [("total_ppf", "0"), ("total_nps", "0")]:
        try:
            conn.execute(
                f"ALTER TABLE networth_snapshots ADD COLUMN {col} REAL NOT NULL DEFAULT {default}"
            )
        except Exception:
            pass  # Column already exists — safe to ignore


def is_first_run() -> bool:
    """Return True if no password has been set (first launch)."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) FROM app_config").fetchone()
        return row[0] == 0
    except sqlite3.OperationalError:
        return True
    finally:
        conn.close()


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    -- ── Auth ────────────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS app_config (
        id              INTEGER PRIMARY KEY CHECK (id = 1),
        password_hash   TEXT NOT NULL,
        salt            TEXT NOT NULL,
        created_at      TEXT NOT NULL,
        updated_at      TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS security_questions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        question_index  INTEGER NOT NULL UNIQUE,
        question_text   TEXT NOT NULL,
        answer_hash     TEXT NOT NULL
    );

    -- ── Settings ─────────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS settings (
        key             TEXT PRIMARY KEY,
        value           TEXT NOT NULL,
        updated_at      TEXT NOT NULL
    );

    -- ── Debt assets ──────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS pf_account (
        id              INTEGER PRIMARY KEY CHECK (id = 1),
        account_number  TEXT,
        total_balance   REAL NOT NULL DEFAULT 0.0,
        as_of_date      TEXT NOT NULL,
        notes           TEXT,
        updated_at      TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS ppf_account (
        id                  INTEGER PRIMARY KEY CHECK (id = 1),
        account_number      TEXT,
        bank_name           TEXT,
        opening_date        TEXT,
        maturity_date       TEXT,
        current_balance     REAL NOT NULL DEFAULT 0.0,
        annual_contribution REAL NOT NULL DEFAULT 0.0,
        interest_rate       REAL NOT NULL DEFAULT 7.1,
        as_of_date          TEXT NOT NULL,
        notes               TEXT,
        updated_at          TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS nps_account (
        id                  INTEGER PRIMARY KEY CHECK (id = 1),
        pran_number         TEXT,
        pfm_name            TEXT,
        tier1_corpus        REAL NOT NULL DEFAULT 0.0,
        tier1_contributions REAL NOT NULL DEFAULT 0.0,
        tier2_corpus        REAL NOT NULL DEFAULT 0.0,
        tier2_contributions REAL NOT NULL DEFAULT 0.0,
        equity_pct          REAL NOT NULL DEFAULT 0.0,
        govt_pct            REAL NOT NULL DEFAULT 0.0,
        corp_pct            REAL NOT NULL DEFAULT 0.0,
        as_of_date          TEXT NOT NULL,
        notes               TEXT,
        updated_at          TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS fixed_deposits (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        bank_name       TEXT NOT NULL,
        fd_number       TEXT,
        principal       REAL NOT NULL,
        interest_rate   REAL NOT NULL,
        compounding     TEXT NOT NULL DEFAULT 'quarterly',
        start_date      TEXT NOT NULL,
        maturity_date   TEXT NOT NULL,
        maturity_amount REAL,
        current_value   REAL,
        is_active       INTEGER NOT NULL DEFAULT 1,
        notes           TEXT,
        created_at      TEXT NOT NULL,
        updated_at      TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS bonds (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        bond_name       TEXT NOT NULL,
        issuer          TEXT NOT NULL,
        bond_type       TEXT NOT NULL,
        face_value      REAL NOT NULL,
        units           REAL NOT NULL,
        purchase_price  REAL NOT NULL,
        coupon_rate     REAL,
        purchase_date   TEXT NOT NULL,
        maturity_date   TEXT,
        current_price   REAL,
        is_active       INTEGER NOT NULL DEFAULT 1,
        notes           TEXT,
        created_at      TEXT NOT NULL,
        updated_at      TEXT NOT NULL
    );

    -- ── Mutual funds (debt / equity / gold) ──────────────────────────────────
    CREATE TABLE IF NOT EXISTS mutual_funds (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_name       TEXT NOT NULL,
        amfi_code       TEXT,
        fund_category   TEXT NOT NULL,
        units           REAL NOT NULL,
        avg_nav         REAL NOT NULL,
        purchase_value  REAL NOT NULL,
        current_nav     REAL NOT NULL,
        purchase_date   TEXT NOT NULL,
        folio_number    TEXT,
        is_active       INTEGER NOT NULL DEFAULT 1,
        notes           TEXT,
        created_at      TEXT NOT NULL,
        updated_at      TEXT NOT NULL
    );

    -- ── Equity ───────────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS stocks (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name    TEXT NOT NULL,
        ticker_symbol   TEXT NOT NULL,
        exchange        TEXT NOT NULL DEFAULT 'NSE',
        quantity        REAL NOT NULL,
        avg_buy_price   REAL NOT NULL,
        purchase_value  REAL NOT NULL,
        current_price   REAL NOT NULL,
        purchase_date   TEXT NOT NULL,
        demat_account   TEXT,
        is_active       INTEGER NOT NULL DEFAULT 1,
        notes           TEXT,
        created_at      TEXT NOT NULL,
        updated_at      TEXT NOT NULL
    );

    -- ── Gold ─────────────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS sgb (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        series_name     TEXT NOT NULL,
        units           REAL NOT NULL,
        issue_price     REAL NOT NULL,
        purchase_date   TEXT NOT NULL,
        maturity_date   TEXT NOT NULL,
        coupon_rate     REAL NOT NULL DEFAULT 2.5,
        is_active       INTEGER NOT NULL DEFAULT 1,
        notes           TEXT,
        created_at      TEXT NOT NULL,
        updated_at      TEXT NOT NULL
    );

    -- ── Real Estate ──────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS real_estate (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        property_name   TEXT NOT NULL,
        property_type   TEXT NOT NULL,
        location        TEXT,
        purchase_price  REAL NOT NULL,
        purchase_date   TEXT NOT NULL,
        current_value   REAL NOT NULL,
        area_sqft       REAL,
        is_primary      INTEGER NOT NULL DEFAULT 0,
        notes           TEXT,
        created_at      TEXT NOT NULL,
        updated_at      TEXT NOT NULL
    );

    -- ── Liabilities (all loan types) ─────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS liabilities (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_type           TEXT NOT NULL,
        lender_name         TEXT NOT NULL,
        loan_account        TEXT,
        original_amount     REAL NOT NULL,
        outstanding_amount  REAL NOT NULL,
        interest_rate       REAL NOT NULL,
        emi_amount          REAL,
        sanction_date       TEXT NOT NULL,
        loan_end_date       TEXT,
        linked_property_id  INTEGER,
        linked_fund_id      INTEGER,
        gold_weight_grams   REAL,
        purpose             TEXT,
        is_active           INTEGER NOT NULL DEFAULT 1,
        notes               TEXT,
        created_at          TEXT NOT NULL,
        updated_at          TEXT NOT NULL,
        FOREIGN KEY (linked_property_id) REFERENCES real_estate(id) ON DELETE SET NULL,
        FOREIGN KEY (linked_fund_id) REFERENCES mutual_funds(id) ON DELETE SET NULL
    );

    -- ── Networth snapshots ────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS networth_snapshots (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_date       TEXT NOT NULL,
        snapshot_type       TEXT NOT NULL DEFAULT 'manual',
        total_pf            REAL NOT NULL DEFAULT 0,
        total_ppf           REAL NOT NULL DEFAULT 0,
        total_nps           REAL NOT NULL DEFAULT 0,
        total_fd            REAL NOT NULL DEFAULT 0,
        total_bonds         REAL NOT NULL DEFAULT 0,
        total_debt_mf       REAL NOT NULL DEFAULT 0,
        total_equity_mf     REAL NOT NULL DEFAULT 0,
        total_stocks        REAL NOT NULL DEFAULT 0,
        total_gold_mf       REAL NOT NULL DEFAULT 0,
        total_sgb           REAL NOT NULL DEFAULT 0,
        total_real_estate   REAL NOT NULL DEFAULT 0,
        total_home_loans    REAL NOT NULL DEFAULT 0,
        total_personal_loans REAL NOT NULL DEFAULT 0,
        total_gold_loans    REAL NOT NULL DEFAULT 0,
        total_mf_loans      REAL NOT NULL DEFAULT 0,
        total_debt_assets   REAL NOT NULL DEFAULT 0,
        total_equity_assets REAL NOT NULL DEFAULT 0,
        total_gold_assets   REAL NOT NULL DEFAULT 0,
        gross_assets        REAL NOT NULL DEFAULT 0,
        total_liabilities   REAL NOT NULL DEFAULT 0,
        net_worth           REAL NOT NULL DEFAULT 0,
        usd_to_inr_rate     REAL,
        net_worth_usd       REAL,
        gold_price_per_gram REAL,
        notes               TEXT,
        created_at          TEXT NOT NULL
    );

    -- ── Import audit log ──────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS import_log (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        import_date     TEXT NOT NULL,
        asset_category  TEXT NOT NULL,
        filename        TEXT NOT NULL,
        rows_imported   INTEGER NOT NULL DEFAULT 0,
        rows_skipped    INTEGER NOT NULL DEFAULT 0,
        status          TEXT NOT NULL,
        error_details   TEXT,
        created_at      TEXT NOT NULL
    );

    -- ── Goals ─────────────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS goals (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL,
        description     TEXT,
        target_amount   REAL NOT NULL,
        color           TEXT NOT NULL DEFAULT '#14b8a6',
        icon            TEXT NOT NULL DEFAULT '🎯',
        deadline        TEXT,
        is_active       INTEGER NOT NULL DEFAULT 1,
        created_at      TEXT NOT NULL,
        updated_at      TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS asset_goals (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        goal_id         INTEGER NOT NULL,
        asset_type      TEXT NOT NULL,
        asset_id        INTEGER NOT NULL,
        notes           TEXT,
        created_at      TEXT NOT NULL,
        FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
    );

    -- ── Records: investment holder / nominee details ──────────────────────────
    CREATE TABLE IF NOT EXISTS investment_records (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_type           TEXT NOT NULL,
        asset_id             INTEGER NOT NULL,
        account_folio_number TEXT,
        first_holder         TEXT,
        second_holder        TEXT,
        nominee_1_name       TEXT,
        nominee_1_pct        REAL,
        nominee_2_name       TEXT,
        nominee_2_pct        REAL,
        notes                TEXT,
        updated_at           TEXT NOT NULL,
        UNIQUE(asset_type, asset_id)
    );

    -- ── Records: insurance, emergency fund, will, etc. ────────────────────────
    CREATE TABLE IF NOT EXISTS protection_records (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        record_type       TEXT NOT NULL,
        provider          TEXT,
        policy_number     TEXT,
        coverage_amount   REAL,
        premium_amount    REAL,
        premium_frequency TEXT DEFAULT 'annual',
        start_date        TEXT,
        end_date          TEXT,
        nominee           TEXT,
        notes             TEXT,
        is_active         INTEGER NOT NULL DEFAULT 1,
        created_at        TEXT NOT NULL,
        updated_at        TEXT NOT NULL
    );

    -- ── Records: emergency contacts, advocates, advisors, etc. ───────────────
    CREATE TABLE IF NOT EXISTS contact_records (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        contact_type  TEXT NOT NULL,
        name          TEXT NOT NULL,
        relationship  TEXT,
        phone         TEXT,
        email         TEXT,
        address       TEXT,
        notes         TEXT,
        created_at    TEXT NOT NULL,
        updated_at    TEXT NOT NULL
    );

    -- ── Schema version ────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS app_schema_version (
        version         INTEGER PRIMARY KEY,
        applied_at      TEXT NOT NULL
    );
    """)

    # Insert schema version 1 if not present
    conn.execute(
        "INSERT OR IGNORE INTO app_schema_version (version, applied_at) VALUES (1, datetime('now'))"
    )

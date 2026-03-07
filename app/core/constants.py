"""App-wide constants, enums, and configuration."""

import os
import sys

# ── Path helpers for PyInstaller compatibility ────────────────────────────────
def _writable_base() -> str:
    """
    Root directory for writable runtime data (data/, backups/).
    • Frozen (PyInstaller onedir): folder that contains the .exe
    • Source: repo root (3 levels above app/core/constants.py)
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _resource_base() -> str:
    """
    Root directory for read-only bundled assets (assets/, templates/).
    • Frozen (PyInstaller onedir): sys._MEIPASS  (_internal/ folder)
    • Source: repo root
    """
    if getattr(sys, "frozen", False):
        return sys._MEIPASS          # type: ignore[attr-defined]
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


_WRITABLE = _writable_base()
_RESOURCE = _resource_base()

# ── Paths ────────────────────────────────────────────────────────────────────
APP_DIR      = _WRITABLE                                       # backward compat
DATA_DIR     = os.path.join(_WRITABLE, "data")
DB_PATH      = os.path.join(DATA_DIR,  "financial_app.db")
BACKUP_DIR   = os.path.join(DATA_DIR,  "backups")
TEMPLATES_DIR = os.path.join(_RESOURCE, "templates")
ASSETS_DIR   = os.path.join(_RESOURCE, "assets")
ICON_PATH    = os.path.join(ASSETS_DIR, "icons",  "app_icon.ico")
QSS_PATH     = os.path.join(ASSETS_DIR, "styles", "dark_theme.qss")

# ── Security ─────────────────────────────────────────────────────────────────
BCRYPT_ROUNDS = 12
PBKDF2_ITERATIONS = 600_000
MAX_PASSWORD_LENGTH = 64
MAX_LOGIN_ATTEMPTS = 3
LOCKOUT_SECONDS = 30

# ── Fund categories ───────────────────────────────────────────────────────────
FUND_CATEGORY_DEBT = "debt"
FUND_CATEGORY_EQUITY = "equity"
FUND_CATEGORY_GOLD = "gold"
FUND_CATEGORIES = [FUND_CATEGORY_DEBT, FUND_CATEGORY_EQUITY, FUND_CATEGORY_GOLD]

# ── Loan types ────────────────────────────────────────────────────────────────
LOAN_HOME = "home_loan"
LOAN_PERSONAL = "personal_loan"
LOAN_GOLD = "gold_loan"
LOAN_MF = "mf_loan"
LOAN_TYPES = [LOAN_HOME, LOAN_PERSONAL, LOAN_GOLD, LOAN_MF]
LOAN_TYPE_LABELS = {
    LOAN_HOME: "Home Loan",
    LOAN_PERSONAL: "Personal Loan",
    LOAN_GOLD: "Gold Loan",
    LOAN_MF: "MF Loan",
}

# ── Bond types ────────────────────────────────────────────────────────────────
BOND_TYPES = ["government", "corporate", "tax_free"]
BOND_TYPE_LABELS = {
    "government": "Government",
    "corporate": "Corporate",
    "tax_free": "Tax Free",
}

# ── Compounding options ───────────────────────────────────────────────────────
COMPOUNDING_OPTIONS = ["monthly", "quarterly", "yearly", "simple"]
COMPOUNDING_LABELS = {
    "monthly": "Monthly",
    "quarterly": "Quarterly",
    "yearly": "Yearly",
    "simple": "Simple Interest",
}

# ── Exchange options ──────────────────────────────────────────────────────────
EXCHANGE_OPTIONS = ["NSE", "BSE"]

# ── Property types ────────────────────────────────────────────────────────────
PROPERTY_TYPES = ["residential", "commercial", "land", "plot"]
PROPERTY_TYPE_LABELS = {
    "residential": "Residential",
    "commercial": "Commercial",
    "land": "Land",
    "plot": "Plot",
}

# ── Personal loan purposes ────────────────────────────────────────────────────
PERSONAL_LOAN_PURPOSES = [
    "Vehicle", "Medical", "Wedding", "Education", "Travel",
    "Home Renovation", "Consumer Goods", "Business", "Other"
]

# ── Security questions ────────────────────────────────────────────────────────
SECURITY_QUESTIONS = [
    "What is the name of your first school?",
    "What is your mother's maiden name?",
    "What was the name of your first pet?",
    "What is the name of the city where you were born?",
    "What was the make and model of your first car?",
    "What is your oldest sibling's middle name?",
    "What was the name of your childhood best friend?",
    "What street did you grow up on?",
    "What is your paternal grandmother's maiden name?",
    "What was the name of the hospital where you were born?",
]

# ── Settings keys ─────────────────────────────────────────────────────────────
SETTING_USD_RATE = "usd_to_inr_rate"
SETTING_GOLD_PRICE = "gold_price_per_gram_inr"
SETTING_THEME = "app_theme"
SETTING_GOLD_UPDATED = "gold_price_updated_at"

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_USD_RATE = 84.0
DEFAULT_GOLD_PRICE = 6500.0   # INR per gram (approximate, user must update)
DEFAULT_SGB_COUPON = 2.5

# ── UI Colors (used in charts and badges) ─────────────────────────────────────
COLOR_PF        = "#3b82f6"   # blue-500
COLOR_FD        = "#60a5fa"   # blue-400
COLOR_BONDS     = "#93c5fd"   # blue-300
COLOR_DEBT_MF   = "#bfdbfe"   # blue-200
COLOR_EQUITY_MF = "#10b981"   # emerald-500
COLOR_STOCKS    = "#34d399"   # emerald-400
COLOR_GOLD_MF   = "#f59e0b"   # amber-500
COLOR_SGB       = "#fbbf24"   # amber-400
COLOR_REAL_ESTATE = "#f97316" # orange-500
COLOR_LIABILITY = "#f43f5e"   # rose-500
COLOR_NET_WORTH = "#14b8a6"   # teal-500

ASSET_COLORS = {
    "PF": COLOR_PF,
    "Fixed Deposits": COLOR_FD,
    "Bonds": COLOR_BONDS,
    "Debt MF": COLOR_DEBT_MF,
    "Equity MF": COLOR_EQUITY_MF,
    "Stocks": COLOR_STOCKS,
    "Gold MF": COLOR_GOLD_MF,
    "SGB": COLOR_SGB,
    "Real Estate": COLOR_REAL_ESTATE,
}

# ── Asset type keys (used for goal tagging) ───────────────────────────────────
ASSET_TYPE_PF          = "pf"
ASSET_TYPE_FD          = "fd"
ASSET_TYPE_BONDS       = "bonds"
ASSET_TYPE_DEBT_MF     = "debt_mf"
ASSET_TYPE_EQUITY_MF   = "equity_mf"
ASSET_TYPE_STOCKS      = "stocks"
ASSET_TYPE_GOLD_MF     = "gold_mf"
ASSET_TYPE_SGB         = "sgb"
ASSET_TYPE_REAL_ESTATE = "real_estate"

ASSET_TYPE_LABELS = {
    ASSET_TYPE_PF:          "Provident Fund (PF)",
    ASSET_TYPE_FD:          "Fixed Deposits",
    ASSET_TYPE_BONDS:       "Bonds",
    ASSET_TYPE_DEBT_MF:     "Debt Mutual Funds",
    ASSET_TYPE_EQUITY_MF:   "Equity Mutual Funds",
    ASSET_TYPE_STOCKS:      "Stocks",
    ASSET_TYPE_GOLD_MF:     "Gold Mutual Funds",
    ASSET_TYPE_SGB:         "Sovereign Gold Bonds",
    ASSET_TYPE_REAL_ESTATE: "Real Estate",
}

# ── Goal colour palette ───────────────────────────────────────────────────────
GOAL_COLORS = [
    "#14b8a6",  # teal
    "#3b82f6",  # blue
    "#10b981",  # emerald
    "#f59e0b",  # amber
    "#f97316",  # orange
    "#a855f7",  # purple
    "#ec4899",  # pink
    "#f43f5e",  # rose
]

GOAL_ICONS = ["🎯", "🏠", "🚗", "✈️", "📚", "💍", "🏦", "🌱", "⭐", "🎓"]

"""
Main application window: sidebar navigation + stacked content area.
"""

import traceback

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTreeWidget, QTreeWidgetItem, QStackedWidget,
    QStatusBar, QPushButton, QLabel, QSizePolicy,
    QFrame,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon

from app.core.session import session
from app.core.constants import ICON_PATH

# NOTE: All page widget imports are deferred to _build_ui() so that an import
# failure in any single widget raises a visible error instead of silently
# crashing the app at login time.


class MainWindow(QMainWindow):
    logout_requested = None   # callback set by caller

    def __init__(self, on_logout=None, parent=None):
        super().__init__(parent)
        self.on_logout = on_logout
        self.setWindowTitle("Financial Tracker")
        self.setMinimumSize(1100, 700)
        try:
            self.setWindowIcon(QIcon(ICON_PATH))
        except Exception:
            pass

        self._build_ui()
        self._show_page("dashboard")

    def _build_ui(self):
        # ── Deferred widget imports (inside method to isolate import errors) ──
        from app.ui.dashboard import DashboardWidget
        from app.ui.debt.pf_widget import PFWidget
        from app.ui.debt.fd_widget import FDWidget
        from app.ui.debt.bonds_widget import BondsWidget
        from app.ui.debt.debt_mf_widget import DebtMFWidget
        from app.ui.equity.equity_mf_widget import EquityMFWidget
        from app.ui.equity.stocks_widget import StocksWidget
        from app.ui.gold.gold_mf_widget import GoldMFWidget
        from app.ui.gold.sgb_widget import SGBWidget
        from app.ui.real_estate.property_widget import PropertyWidget
        from app.ui.liabilities.liabilities_widget import LiabilitiesWidget
        from app.ui.reports.charts_widget import ChartsWidget
        from app.ui.reports.report_widget import ReportWidget
        from app.ui.import_export.import_wizard import ImportWizard
        from app.ui.settings.settings_widget import SettingsWidget
        from app.ui.goals.goals_widget import GoalsWidget
        from app.ui.records.records_widget import RecordsWidget

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        # App title / brand
        app_title = QLabel("  💼 Financial Tracker")
        app_title.setObjectName("sidebarTitle")
        app_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        app_title.setFixedHeight(56)
        sb_layout.addWidget(app_title)

        self.nav_tree = QTreeWidget()
        self.nav_tree.setObjectName("navTree")
        self.nav_tree.setHeaderHidden(True)
        self.nav_tree.setIndentation(14)
        self.nav_tree.setAnimated(True)
        self.nav_tree.clicked.connect(self._on_nav_click)
        sb_layout.addWidget(self.nav_tree)

        lock_btn = QPushButton("🔒  Lock App")
        lock_btn.setObjectName("lockButton")
        lock_btn.setMinimumHeight(44)
        lock_btn.clicked.connect(self._on_lock)
        sb_layout.addWidget(lock_btn)

        self._build_nav_tree()

        # ── Content area ──────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setObjectName("contentStack")

        self._pages: dict[str, QWidget] = {}

        # Safe page loader — if a widget fails to construct, show an error
        # placeholder instead of crashing the entire window.
        def _safe(key: str, factory):
            try:
                self._add_page(key, factory())
            except Exception:
                err_lbl = QLabel(
                    f"⚠  Failed to load '{key}'.\n\n"
                    + traceback.format_exc()
                )
                err_lbl.setWordWrap(True)
                err_lbl.setStyleSheet("color: #f43f5e; padding: 20px;")
                self._add_page(key, err_lbl)

        _safe("dashboard",   DashboardWidget)
        _safe("pf",          PFWidget)
        _safe("fd",          FDWidget)
        _safe("bonds",       BondsWidget)
        _safe("debt_mf",     DebtMFWidget)
        _safe("equity_mf",   EquityMFWidget)
        _safe("stocks",      StocksWidget)
        _safe("gold_mf",     GoldMFWidget)
        _safe("sgb",         SGBWidget)
        _safe("real_estate", PropertyWidget)
        _safe("liabilities", LiabilitiesWidget)
        _safe("goals",       GoalsWidget)
        _safe("records",     RecordsWidget)
        _safe("charts",      ChartsWidget)
        _safe("reports",     ReportWidget)
        _safe("import",      ImportWizard)
        _safe("settings",    SettingsWidget)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self._stack)

        # ── Status bar ────────────────────────────────────────────────────────
        self.status = QStatusBar()
        self.status.setObjectName("statusBar")
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

    def _add_page(self, key: str, widget: QWidget):
        self._pages[key] = widget
        self._stack.addWidget(widget)

    def _build_nav_tree(self):
        tree = self.nav_tree
        tree.clear()

        def add_section(label: str) -> QTreeWidgetItem:
            item = QTreeWidgetItem(tree, [label])
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item.setFont(0, QFont("Segoe UI", 7, QFont.Weight.Bold))
            return item

        def add_item(parent, label: str, page_key: str = None) -> QTreeWidgetItem:
            item = QTreeWidgetItem(parent, [label])
            if page_key:
                item.setData(0, Qt.ItemDataRole.UserRole, page_key)
            item.setFont(0, QFont("Segoe UI", 9))
            return item

        # ── Dashboard ─────────────────────────────────────────────────────────
        dash_item = QTreeWidgetItem(tree, ["📊  Dashboard"])
        dash_item.setData(0, Qt.ItemDataRole.UserRole, "dashboard")
        dash_item.setFont(0, QFont("Segoe UI", 9, QFont.Weight.Bold))

        # ── Assets ────────────────────────────────────────────────────────────
        assets = add_section("  ASSETS")

        debt = add_item(assets, "  Debt")
        add_item(debt, "    Provident Fund (PF)", "pf")
        add_item(debt, "    Fixed Deposits",      "fd")
        add_item(debt, "    Bonds",               "bonds")
        add_item(debt, "    Debt Mutual Funds",   "debt_mf")

        equity = add_item(assets, "  Equity")
        add_item(equity, "    Equity Mutual Funds", "equity_mf")
        add_item(equity, "    Stocks",              "stocks")

        gold = add_item(assets, "  Gold")
        add_item(gold, "    Gold Mutual Funds", "gold_mf")
        add_item(gold, "    SGB",               "sgb")

        re = add_item(assets, "  Real Estate")
        add_item(re, "    Properties", "real_estate")

        # ── Liabilities ───────────────────────────────────────────────────────
        liab = add_section("  LIABILITIES")
        add_item(liab, "  All Loans", "liabilities")

        # ── Goals ─────────────────────────────────────────────────────────────
        goals_sec = add_section("  GOALS")
        add_item(goals_sec, "  My Goals", "goals")

        # ── Records ───────────────────────────────────────────────────────────
        rec_sec = add_section("  RECORDS")
        add_item(rec_sec, "  Investments",          "records:0")
        add_item(rec_sec, "  Protection & Insur.",  "records:1")
        add_item(rec_sec, "  Contacts",             "records:2")

        # ── Reports ───────────────────────────────────────────────────────────
        rep = add_section("  REPORTS")
        add_item(rep, "  Charts & Graphs",  "charts")
        add_item(rep, "  Tabular Report",   "reports")

        # ── Tools ─────────────────────────────────────────────────────────────
        tools = add_section("  TOOLS")
        add_item(tools, "  Import Data", "import")
        add_item(tools, "  Settings",   "settings")

        # Start fully collapsed — top-level section headers are always visible
        tree.collapseAll()

    def _on_nav_click(self, index):
        item = self.nav_tree.currentItem()
        page_key = item.data(0, Qt.ItemDataRole.UserRole) if item else None
        if page_key:
            self._show_page(page_key)

    def _show_page(self, key: str):
        # Handle "records:N" — navigate to records page and switch to tab N
        if key.startswith("records:"):
            tab_idx = int(key.split(":")[1])
            widget = self._pages["records"]
            self._stack.setCurrentWidget(widget)
            widget._tabs.setCurrentIndex(tab_idx)
            if hasattr(widget, "refresh"):
                widget.refresh()
            tab_names = ["Investments", "Protection & Insurance", "Contacts"]
            self.status.showMessage(f"Records → {tab_names[tab_idx]}")
            return
        if key in self._pages:
            widget = self._pages[key]
            self._stack.setCurrentWidget(widget)
            # Refresh page data if it has a refresh method
            if hasattr(widget, "refresh"):
                widget.refresh()
            self.status.showMessage(f"Viewing: {key.replace('_', ' ').title()}")

    def _on_lock(self):
        session.logout()
        if self.on_logout:
            self.on_logout()

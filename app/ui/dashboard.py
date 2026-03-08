"""Dashboard: FinBoom-style hero net-worth display + KPI cards + charts."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QDialog, QTextEdit,
    QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import matplotlib
try:
    matplotlib.use("QtAgg")
except Exception:
    pass
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker

from app.services import networth_service as nw_svc
from app.services.formatters import format_inr, format_usd, format_foreign
from app.models import settings as settings_model
from app.ui.widgets import KPICard, title_label, separator
from app.core.constants import ASSET_COLORS, COLOR_LIABILITY, COLOR_NET_WORTH


class DashboardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboardWidget")
        self._values = {}
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        main = QVBoxLayout(content)
        main.setSpacing(20)
        main.setContentsMargins(24, 24, 24, 24)

        # ── Header row ────────────────────────────────────────────────────────
        header = QHBoxLayout()
        header.addWidget(title_label("Dashboard"))
        header.addStretch()
        self.btn_snapshot = QPushButton("📸  Take Snapshot")
        self.btn_snapshot.setObjectName("primaryButton")
        self.btn_snapshot.setFixedHeight(36)
        self.btn_snapshot.clicked.connect(self._take_snapshot)
        header.addWidget(self.btn_snapshot)
        main.addLayout(header)

        # ── Hero net worth card ───────────────────────────────────────────────
        hero = QFrame()
        hero.setObjectName("heroFrame")
        hero.setMinimumHeight(160)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(32, 24, 24, 24)
        hero_layout.setSpacing(4)

        top_row = QHBoxLayout()
        nw_col = QVBoxLayout()

        nw_title = QLabel("TOTAL NET WORTH")
        nw_title.setObjectName("heroLabel")
        self.hero_value = QLabel("₹0")
        self.hero_value.setObjectName("heroValue")
        self.hero_usd = QLabel("$0 equivalent")
        self.hero_usd.setObjectName("heroSub")

        nw_col.addWidget(nw_title)
        nw_col.addWidget(self.hero_value)
        nw_col.addWidget(self.hero_usd)
        top_row.addLayout(nw_col)
        top_row.addStretch()

        right_col = QVBoxLayout()
        right_col.setSpacing(0)

        def mini_stat(label, value_color="#94a3b8"):
            f = QFrame()
            f.setMinimumWidth(160)
            v = QVBoxLayout(f)
            v.setContentsMargins(16, 10, 16, 10)
            v.setSpacing(4)
            l = QLabel(label)
            l.setObjectName("heroLabel")
            l.setStyleSheet("font-size: 8.5pt; letter-spacing: 1.5px; background: transparent;")
            val = QLabel("₹0")
            val.setObjectName("heroSub")
            val.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
            val.setStyleSheet(f"color: {value_color}; font-size: 16pt; "
                              "font-weight: bold; background: transparent;")
            v.addWidget(l)
            v.addWidget(val)
            return f, val

        gross_frame, self.mini_gross = mini_stat("GROSS ASSETS",  "#64748b")
        liab_frame,  self.mini_liab  = mini_stat("LIABILITIES",   "#f43f5e")

        # Thin horizontal divider between the two mini stats
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background: #1e3a5f; max-height: 1px; margin: 0 16px;")

        right_col.addWidget(gross_frame)
        right_col.addWidget(divider)
        right_col.addWidget(liab_frame)
        top_row.addLayout(right_col)

        hero_layout.addLayout(top_row)
        main.addWidget(hero)

        # ── KPI Cards row ─────────────────────────────────────────────────────
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(14)

        self.card_debt   = KPICard("Debt Assets",      "₹0", "#3b82f6", "🏦")
        self.card_equity = KPICard("Equity Assets",    "₹0", "#10b981", "📈")
        self.card_gold   = KPICard("Gold Assets",      "₹0", "#f59e0b", "🥇")
        self.card_re     = KPICard("Real Estate",      "₹0", "#f97316", "🏠")

        for card in [self.card_debt, self.card_equity, self.card_gold, self.card_re]:
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            kpi_layout.addWidget(card)

        main.addLayout(kpi_layout)

        # ── Charts row ────────────────────────────────────────────────────────
        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)

        self.alloc_canvas = self._make_canvas(5, 4)
        charts_row.addWidget(self._framed(self.alloc_canvas, "Asset Allocation"), 1)

        self.gain_canvas = self._make_canvas(5, 4)
        charts_row.addWidget(self._framed(self.gain_canvas, "Category Breakdown"), 1)

        main.addLayout(charts_row)

        # ── Asset detail summary ──────────────────────────────────────────────
        self.detail_label = QLabel()
        self.detail_label.setObjectName("detailSummary")
        self.detail_label.setFont(QFont("Segoe UI", 9))
        self.detail_label.setWordWrap(True)
        main.addWidget(self.detail_label)

        main.addStretch()
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _make_canvas(self, w, h) -> FigureCanvas:
        fig = Figure(figsize=(w, h), dpi=96, tight_layout=True)
        canvas = FigureCanvas(fig)
        return canvas

    def _framed(self, widget: QWidget, title: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("chartFrame")
        layout = QVBoxLayout(frame)
        layout.setSpacing(6)
        lbl = QLabel(title.upper())
        lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl.setObjectName("chartTitle")
        layout.addWidget(lbl)
        layout.addWidget(widget)
        return frame

    def refresh(self):
        self._values = nw_svc.calculate_current_values()
        v = self._values
        c_code   = v.get("currency_code",   "USD")
        c_symbol = v.get("currency_symbol", "$")
        c_rate   = v.get("currency_rate",   v.get("usd_to_inr_rate", 84.0))

        # Hero card
        self.hero_value.setText(format_inr(v["net_worth"]))
        self.hero_usd.setText(
            f"{format_foreign(v['net_worth'], c_rate, c_symbol)}  {c_code} equivalent"
        )
        self.mini_gross.setText(format_inr(v["gross_assets"]))
        self.mini_liab.setText(format_inr(v["total_liabilities"]))

        # Category KPI cards
        self.card_debt.set_value(format_inr(v["total_debt_assets"]),   "#3b82f6")
        self.card_equity.set_value(format_inr(v["total_equity_assets"]), "#10b981")
        self.card_gold.set_value(format_inr(v["total_gold_assets"]),   "#f59e0b")
        self.card_re.set_value(format_inr(v["total_real_estate"]),     "#f97316")

        self._draw_allocation()
        self._draw_breakdown()
        self._update_details()

    def _draw_allocation(self):
        data = nw_svc.get_allocation_data(self._values)
        if not data:
            return

        labels  = [d[0] for d in data]
        amounts = [d[1] for d in data]
        colors  = [ASSET_COLORS.get(lbl, "#64748b") for lbl in labels]

        fig = self.alloc_canvas.figure
        fig.clear()
        ax = fig.add_subplot(111)

        wedges, texts, autotexts = ax.pie(
            amounts, labels=None, colors=colors,
            autopct=lambda p: f"{p:.1f}%" if p > 3 else "",
            startangle=90, pctdistance=0.80,
            wedgeprops={"width": 0.55, "edgecolor": "#0f172a", "linewidth": 1.5},
        )
        for t in autotexts:
            t.set_fontsize(7)
            t.set_color("white")
            t.set_fontweight("bold")

        net = self._values.get("net_worth", 0)
        ax.text(0, 0, f"Net Worth\n{format_inr(net)}", ha="center", va="center",
                fontsize=7.5, fontweight="bold", color="#f1f5f9")

        ax.legend(labels, loc="lower center", bbox_to_anchor=(0.5, -0.18),
                  ncol=3, fontsize=6.5, frameon=False,
                  labelcolor="#94a3b8")
        ax.set_facecolor("none")
        fig.patch.set_facecolor("none")
        self.alloc_canvas.draw()

    def _draw_breakdown(self):
        v = self._values
        categories = ["Debt", "Equity MF", "Stocks", "Gold", "Real Estate"]
        amounts = [
            v["total_debt_assets"],
            v["total_equity_mf"],
            v["total_stocks"],
            v["total_gold_assets"],
            v["total_real_estate"],
        ]
        colors = ["#3b82f6", "#10b981", "#34d399", "#f59e0b", "#f97316"]

        fig = self.gain_canvas.figure
        fig.clear()
        ax = fig.add_subplot(111)

        bars = ax.barh(categories, [abs(a) for a in amounts],
                       color=colors, height=0.55,
                       edgecolor="none")

        # Value labels on bars
        for bar, amt in zip(bars, amounts):
            w = bar.get_width()
            if w > 0:
                ax.text(w * 1.01, bar.get_y() + bar.get_height() / 2,
                        format_inr(amt),
                        va="center", ha="left", fontsize=6.5, color="#94a3b8")

        ax.set_xlabel("Amount (INR)", fontsize=7, color="#64748b")
        ax.xaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(
                lambda x, _: f"₹{x/1e7:.1f}Cr" if x >= 1e7
                else f"₹{x/1e5:.0f}L" if x >= 1e5
                else f"₹{x:,.0f}"
            )
        )
        ax.tick_params(axis="both", labelsize=7, colors="#64748b")
        ax.set_facecolor("none")
        fig.patch.set_facecolor("none")
        for spine in ax.spines.values():
            spine.set_edgecolor("#334155")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        self.gain_canvas.draw()

    def _update_details(self):
        v = self._values
        lines = [
            f"<b style='color:#3b82f6'>Debt</b> &nbsp;{format_inr(v['total_debt_assets'])} &nbsp;"
            f"<span style='color:#64748b'>PF: {format_inr(v['total_pf'])} &nbsp;|&nbsp; "
            f"FD: {format_inr(v['total_fd'])} &nbsp;|&nbsp; "
            f"Bonds: {format_inr(v['total_bonds'])} &nbsp;|&nbsp; "
            f"Debt MF: {format_inr(v['total_debt_mf'])}</span>",

            f"<b style='color:#10b981'>Equity</b> &nbsp;{format_inr(v['total_equity_assets'])} &nbsp;"
            f"<span style='color:#64748b'>Equity MF: {format_inr(v['total_equity_mf'])} &nbsp;|&nbsp; "
            f"Stocks: {format_inr(v['total_stocks'])}</span>",

            f"<b style='color:#f59e0b'>Gold</b> &nbsp;{format_inr(v['total_gold_assets'])} &nbsp;"
            f"<span style='color:#64748b'>Gold MF: {format_inr(v['total_gold_mf'])} &nbsp;|&nbsp; "
            f"SGB: {format_inr(v['total_sgb'])}</span>",

            f"<b style='color:#f97316'>Real Estate</b> &nbsp;{format_inr(v['total_real_estate'])}",

            f"<b style='color:#f43f5e'>Liabilities</b> &nbsp;{format_inr(v['total_liabilities'])} &nbsp;"
            f"<span style='color:#64748b'>Home: {format_inr(v['total_home_loans'])} &nbsp;|&nbsp; "
            f"Personal: {format_inr(v['total_personal_loans'])} &nbsp;|&nbsp; "
            f"Gold: {format_inr(v['total_gold_loans'])} &nbsp;|&nbsp; "
            f"MF: {format_inr(v['total_mf_loans'])}</span>",
        ]
        self.detail_label.setText("<br>".join(lines))

    def _take_snapshot(self):
        v = self._values or nw_svc.calculate_current_values()
        dlg = SnapshotPreviewDialog(v, self)
        if dlg.exec():
            notes = dlg.notes_edit.toPlainText()
            snapshot_id = nw_svc.save_snapshot(v, notes)
            from app.ui.widgets import info_dialog
            info_dialog(self, "Snapshot Saved",
                        f"Net worth snapshot saved (ID: {snapshot_id}).")


class SnapshotPreviewDialog(QDialog):
    def __init__(self, values: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Snapshot")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        layout.addWidget(QLabel("<b>Net Worth Snapshot Preview</b>"))
        layout.addWidget(separator())

        v = values
        text = (
            f"Gross Assets:      {format_inr(v['gross_assets'])}\n"
            f"Total Liabilities: {format_inr(v['total_liabilities'])}\n"
            f"Net Worth:         {format_inr(v['net_worth'])}\n"
            f"Gold Price/gram:   ₹{v['gold_price_per_gram']:,.0f}\n"
            f"{v.get('currency_code','USD')} Rate:      "
            f"₹{v.get('currency_rate', v.get('usd_to_inr_rate', 84.0)):.2f}\n"
        )
        lbl = QLabel(text)
        lbl.setFont(QFont("Consolas", 10))
        lbl.setStyleSheet("color: #94a3b8;")
        layout.addWidget(lbl)

        layout.addWidget(QLabel("Notes (optional):"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(60)
        layout.addWidget(self.notes_edit)

        btn_row = QHBoxLayout()
        btn_save = QPushButton("Save Snapshot")
        btn_save.setObjectName("primaryButton")
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

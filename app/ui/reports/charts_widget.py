"""Charts & Graphs widget using matplotlib embedded in PyQt6."""

import matplotlib
# Must set backend before any other matplotlib import.
# Wrapped in try/except so a backend mismatch warning never crashes the app.
try:
    matplotlib.use("QtAgg")
except Exception:
    pass
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTabWidget, QComboBox, QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.services import report_service
from app.services.formatters import format_inr
from app.core.constants import ASSET_COLORS


class ChartCanvas(FigureCanvas):
    def __init__(self, width=8, height=5, dpi=96):
        self.fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        self.fig.patch.set_facecolor("#1e1e2e")
        super().__init__(self.fig)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def clear(self):
        self.fig.clear()

    def draw_and_flush(self):
        self.draw()


def _style_ax(ax, title=""):
    ax.set_facecolor("#2a2a3e")
    ax.tick_params(colors="#aaa", labelsize=8)
    ax.xaxis.label.set_color("#aaa")
    ax.yaxis.label.set_color("#aaa")
    for spine in ax.spines.values():
        spine.set_edgecolor("#444")
    if title:
        ax.set_title(title, color="#ddd", fontsize=10)


INRLAKH = matplotlib.ticker.FuncFormatter(
    lambda x, _: f"₹{x/1e5:.0f}L" if abs(x) >= 1e5 else f"₹{x:,.0f}"
)


class ChartsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._period_months = 0
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header + filter buttons
        header = QHBoxLayout()
        header.addWidget(QLabel("Charts & Graphs"))
        header.addStretch()
        for label, months in [("1 Year", 12), ("3 Years", 36), ("5 Years", 60), ("All Time", 0)]:
            btn = QPushButton(label)
            btn.setObjectName("filterButton")
            btn.setCheckable(True)
            btn.setChecked(months == 0)
            btn.clicked.connect(lambda _, m=months: self._set_period(m))
            header.addWidget(btn)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("chartTabs")

        self._nw_canvas = ChartCanvas(10, 4)
        self._alloc_canvas = ChartCanvas(8, 4)
        self._stacked_canvas = ChartCanvas(10, 4)
        self._category_canvas = ChartCanvas(10, 4)

        self.tabs.addTab(self._nw_canvas, "Net Worth Growth")
        self.tabs.addTab(self._alloc_canvas, "Asset Allocation")
        self.tabs.addTab(self._stacked_canvas, "Category Stacked")
        self.tabs.addTab(self._category_canvas, "Category Trends")

        self.tabs.currentChanged.connect(self._draw_current_tab)
        layout.addWidget(self.tabs)

        self._data = {}

    def refresh(self):
        self._data = report_service.get_chart_data(self._period_months)
        self._draw_current_tab(self.tabs.currentIndex())

    def _set_period(self, months: int):
        self._period_months = months
        self.refresh()

    def _draw_current_tab(self, idx: int):
        if not self._data or not self._data.get("dates"):
            return
        if idx == 0:
            self._draw_networth()
        elif idx == 1:
            self._draw_allocation()
        elif idx == 2:
            self._draw_stacked()
        elif idx == 3:
            self._draw_category_trends()

    def _draw_networth(self):
        d = self._data
        canvas = self._nw_canvas
        canvas.clear()
        ax = canvas.fig.add_subplot(111)
        _style_ax(ax, "Net Worth Growth Over Time")

        dates = d["dates"]
        ax.plot(dates, d["gross"], label="Gross Assets", color="#4A90D9", linewidth=2)
        ax.plot(dates, d["net_worth"], label="Net Worth", color="#2ECC71", linewidth=2)
        ax.plot(dates, d["liabilities"], label="Liabilities", color="#E74C3C", linestyle="--", linewidth=1.5)

        ax.yaxis.set_major_formatter(INRLAKH)
        _rotate_dates(ax, dates)
        ax.legend(fontsize=8, facecolor="#2a2a3e", labelcolor="#ddd", edgecolor="#444")
        ax.grid(True, alpha=0.2, color="#666")
        canvas.draw_and_flush()

    def _draw_allocation(self):
        from app.services import networth_service as nw_svc
        values = nw_svc.calculate_current_values()
        alloc = nw_svc.get_allocation_data(values)
        if not alloc:
            return

        canvas = self._alloc_canvas
        canvas.clear()
        ax = canvas.fig.add_subplot(111)
        ax.set_facecolor("#2a2a3e")
        canvas.fig.patch.set_facecolor("#1e1e2e")

        labels = [a[0] for a in alloc]
        amounts = [a[1] for a in alloc]
        colors = [ASSET_COLORS.get(lbl, "#888") for lbl in labels]

        wedges, _, autotexts = ax.pie(
            amounts, labels=None, colors=colors, autopct=lambda p: f"{p:.1f}%" if p > 2 else "",
            startangle=90, pctdistance=0.80,
            wedgeprops={"width": 0.55, "edgecolor": "#1e1e2e", "linewidth": 1.5},
        )
        for t in autotexts:
            t.set_fontsize(8)
            t.set_color("white")

        net = values["net_worth"]
        ax.text(0, 0, f"Net Worth\n{format_inr(net)}", ha="center", va="center",
                fontsize=9, fontweight="bold", color="white")

        ax.legend(labels, loc="lower center", bbox_to_anchor=(0.5, -0.15),
                  ncol=3, fontsize=8, frameon=False, labelcolor="#ddd")
        ax.set_title("Current Asset Allocation", color="#ddd", fontsize=10)
        canvas.draw_and_flush()

    def _draw_stacked(self):
        d = self._data
        canvas = self._stacked_canvas
        canvas.clear()
        ax = canvas.fig.add_subplot(111)
        _style_ax(ax, "Portfolio Composition Over Time")

        dates = d["dates"]
        ax.stackplot(
            dates,
            d["debt"], d["equity"], d["gold"], d["real_estate"],
            labels=["Debt", "Equity", "Gold", "Real Estate"],
            colors=["#4A90D9", "#27AE60", "#F39C12", "#8B6914"],
            alpha=0.85,
        )
        ax.yaxis.set_major_formatter(INRLAKH)
        _rotate_dates(ax, dates)
        ax.legend(fontsize=8, facecolor="#2a2a3e", labelcolor="#ddd", edgecolor="#444", loc="upper left")
        ax.grid(True, alpha=0.2, color="#666")
        canvas.draw_and_flush()

    def _draw_category_trends(self):
        d = self._data
        canvas = self._category_canvas
        canvas.clear()
        ax = canvas.fig.add_subplot(111)
        _style_ax(ax, "Category Trends")

        dates = d["dates"]
        ax.plot(dates, d["debt"], label="Debt", color="#4A90D9", linewidth=1.8)
        ax.plot(dates, d["equity"], label="Equity", color="#27AE60", linewidth=1.8)
        ax.plot(dates, d["gold"], label="Gold", color="#F39C12", linewidth=1.8)
        ax.plot(dates, d["real_estate"], label="Real Estate", color="#8B6914", linewidth=1.8)

        ax.yaxis.set_major_formatter(INRLAKH)
        _rotate_dates(ax, dates)
        ax.legend(fontsize=8, facecolor="#2a2a3e", labelcolor="#ddd", edgecolor="#444")
        ax.grid(True, alpha=0.2, color="#666")
        canvas.draw_and_flush()


def _rotate_dates(ax, dates):
    """Show max 10 date labels to avoid crowding."""
    if len(dates) > 10:
        step = max(1, len(dates) // 10)
        ax.set_xticks(range(0, len(dates), step))
        ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], rotation=30, ha="right", fontsize=7)
    else:
        ax.set_xticks(range(len(dates)))
        ax.set_xticklabels(dates, rotation=30, ha="right", fontsize=7)

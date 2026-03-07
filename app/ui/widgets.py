"""Shared reusable PyQt6 widget helpers."""

from PyQt6.QtWidgets import (
    QLabel, QLineEdit, QComboBox, QPushButton, QFrame,
    QHBoxLayout, QVBoxLayout, QSizePolicy, QWidget,
    QDoubleSpinBox, QDateEdit, QTextEdit, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor


# ── Styled labels ─────────────────────────────────────────────────────────────

def title_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
    lbl.setObjectName("titleLabel")
    return lbl


def section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
    lbl.setObjectName("sectionLabel")
    return lbl


def field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", 9))
    lbl.setObjectName("fieldLabel")
    return lbl


# ── KPI Card ──────────────────────────────────────────────────────────────────

class KPICard(QFrame):
    """
    FinBoom-style metric card with:
      • coloured icon badge (top-left)
      • UPPERCASE muted title
      • large monospace value in accent colour
    """

    def __init__(self, title: str, value: str = "₹0",
                 color: str = "#14b8a6", icon: str = "◈", parent=None):
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(110)
        self.setMinimumWidth(180)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(16, 14, 16, 14)

        # ── Icon badge ────────────────────────────────────────────────────────
        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setFont(QFont("Segoe UI", 14))
        icon_lbl.setStyleSheet(
            f"background-color: {color}22; color: {color};"
            "border-radius: 8px; padding: 0px;"
        )

        # ── Title (muted, uppercase) ──────────────────────────────────────────
        self._title = QLabel(title.upper())
        self._title.setFont(QFont("Segoe UI", 8))
        self._title.setObjectName("kpiTitle")

        # ── Value (large, monospace, coloured) ────────────────────────────────
        self._value = QLabel(value)
        self._value.setFont(QFont("Consolas", 15, QFont.Weight.Bold))
        self._value.setObjectName("kpiValue")
        self._value.setStyleSheet(f"color: {color};")
        self._color = color

        layout.addWidget(icon_lbl)
        layout.addWidget(self._title)
        layout.addWidget(self._value)
        layout.addStretch()

    def set_value(self, value: str, color: str | None = None) -> None:
        self._value.setText(value)
        if color:
            self._color = color
            self._value.setStyleSheet(f"color: {color};")


# ── Goal Progress Bar ─────────────────────────────────────────────────────────

class GoalProgressBar(QFrame):
    """
    A horizontal progress bar styled like FinBoom's goal tracker.
    Shows: label (left), percentage (right), filled teal bar on gray track.
    """

    def __init__(self, current: float = 0, target: float = 1,
                 color: str = "#14b8a6", parent=None):
        super().__init__(parent)
        self._current = current
        self._target = target
        self._color = color
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 4, 0, 4)
        outer.setSpacing(4)

        # Row: percentage + amounts
        row = QHBoxLayout()
        pct = min((self._current / self._target * 100) if self._target > 0 else 0, 100)

        self._pct_lbl = QLabel(f"{pct:.1f}% achieved")
        self._pct_lbl.setObjectName("goalProgress")

        row.addWidget(self._pct_lbl)
        row.addStretch()
        outer.addLayout(row)

        # Track
        track = QFrame()
        track.setObjectName("progressTrack")
        track.setFixedHeight(8)
        track_layout = QHBoxLayout(track)
        track_layout.setContentsMargins(0, 0, 0, 0)
        track_layout.setSpacing(0)

        fill_width = max(int(pct), 2) if pct > 0 else 0
        if fill_width > 0:
            fill = QFrame()
            fill.setObjectName("progressFill")
            fill.setFixedHeight(8)
            fill.setStyleSheet(f"background-color: {self._color}; border-radius: 4px;")
            # Use stretch proportionally
            track_layout.addWidget(fill, fill_width)
            if fill_width < 100:
                spacer = QFrame()
                spacer.setFixedHeight(8)
                track_layout.addWidget(spacer, 100 - fill_width)

        outer.addWidget(track)

    def update_values(self, current: float, target: float):
        self._current = current
        self._target = target
        # Rebuild
        while self.layout().count():
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # Rebuild layout
        self._build()


# ── Form helpers ──────────────────────────────────────────────────────────────

def make_amount_spin(min_val: float = 0.0, max_val: float = 1e12,
                     decimals: int = 2, prefix: str = "₹ ") -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(min_val, max_val)
    spin.setDecimals(decimals)
    spin.setPrefix(prefix)
    spin.setSingleStep(1000)
    spin.setGroupSeparatorShown(True)
    return spin


def make_rate_spin(min_val: float = 0.0, max_val: float = 100.0) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(min_val, max_val)
    spin.setDecimals(2)
    spin.setSuffix(" %")
    spin.setSingleStep(0.25)
    return spin


def make_date_edit(default_today: bool = True) -> QDateEdit:
    de = QDateEdit()
    de.setCalendarPopup(True)
    de.setDisplayFormat("dd-MMM-yyyy")
    if default_today:
        de.setDate(QDate.currentDate())
    return de


def make_combo(options: list, labels: dict | None = None) -> QComboBox:
    cb = QComboBox()
    for opt in options:
        display = labels.get(opt, opt) if labels else opt
        cb.addItem(display, opt)
    return cb


# ── Standard table ────────────────────────────────────────────────────────────

def make_table(headers: list[str]) -> QTableWidget:
    tbl = QTableWidget()
    tbl.setColumnCount(len(headers))
    tbl.setHorizontalHeaderLabels(headers)
    tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    tbl.setAlternatingRowColors(True)
    tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    tbl.verticalHeader().setVisible(False)
    tbl.setObjectName("dataTable")
    return tbl


def table_item(text: str, align=Qt.AlignmentFlag.AlignLeft) -> QTableWidgetItem:
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
    return item


def table_item_right(text: str) -> QTableWidgetItem:
    return table_item(text, Qt.AlignmentFlag.AlignRight)


# ── Separator ─────────────────────────────────────────────────────────────────

def separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setObjectName("separator")
    return line


# ── Confirmation dialog ───────────────────────────────────────────────────────

def confirm_delete(parent, name: str) -> bool:
    reply = QMessageBox.question(
        parent, "Confirm Delete",
        f"Delete '{name}'? This cannot be undone.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes


def info_dialog(parent, title: str, message: str) -> None:
    QMessageBox.information(parent, title, message)


def error_dialog(parent, title: str, message: str) -> None:
    QMessageBox.critical(parent, title, message)

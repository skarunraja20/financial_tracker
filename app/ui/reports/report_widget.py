"""Tabular net worth report widget."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.services import report_service
from app.ui.widgets import make_table, table_item, table_item_right, title_label, separator
from app.services.formatters import format_inr
from app.models import networth as nw_model


class ReportWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(title_label("Tabular Report"))
        header.addStretch()

        self.period_combo = QComboBox()
        self.period_combo.addItems(["Monthly", "Quarterly", "Yearly"])
        self.period_combo.currentTextChanged.connect(self.refresh)
        header.addWidget(QLabel("Period:"))
        header.addWidget(self.period_combo)

        btn_export = QPushButton("Export CSV")
        btn_export.setObjectName("secondaryButton")
        btn_export.clicked.connect(self._export_csv)
        header.addWidget(btn_export)

        layout.addLayout(header)
        layout.addWidget(separator())

        self.table = make_table([
            "Period", "Gross Assets", "Liabilities", "Net Worth",
            "Debt", "Equity", "Gold", "Real Estate",
        ])
        layout.addWidget(self.table)

        # Snapshot history
        layout.addWidget(QLabel("All Snapshots (most recent first):"))
        self.snap_table = make_table(["Date", "Net Worth", "Gross Assets", "Liabilities", "Type", "Notes"])
        self.snap_table.setMaximumHeight(200)

        btn_del = QPushButton("Delete Selected Snapshot")
        btn_del.setObjectName("dangerButton")
        btn_del.clicked.connect(self._delete_snapshot)

        layout.addWidget(self.snap_table)
        layout.addWidget(btn_del, alignment=Qt.AlignmentFlag.AlignRight)

    def refresh(self):
        period = self.period_combo.currentText().lower()
        self._rows = report_service.get_tabular_report(period)

        self.table.setRowCount(0)
        for i, row in enumerate(self._rows):
            self.table.insertRow(i)
            self.table.setItem(i, 0, table_item(row["period"]))
            self.table.setItem(i, 1, table_item_right(format_inr(row["gross_assets"])))
            self.table.setItem(i, 2, table_item_right(format_inr(row["total_liabilities"])))
            self.table.setItem(i, 3, table_item_right(format_inr(row["net_worth"])))
            self.table.setItem(i, 4, table_item_right(format_inr(row["debt_assets"])))
            self.table.setItem(i, 5, table_item_right(format_inr(row["equity_assets"])))
            self.table.setItem(i, 6, table_item_right(format_inr(row["gold_assets"])))
            self.table.setItem(i, 7, table_item_right(format_inr(row["real_estate"])))

        # Refresh snapshot list
        snaps = nw_model.get_all_snapshots()
        self.snap_table.setRowCount(0)
        for i, s in enumerate(snaps):
            self.snap_table.insertRow(i)
            self.snap_table.setItem(i, 0, table_item(s["snapshot_date"]))
            self.snap_table.setItem(i, 1, table_item_right(format_inr(s["net_worth"])))
            self.snap_table.setItem(i, 2, table_item_right(format_inr(s["gross_assets"])))
            self.snap_table.setItem(i, 3, table_item_right(format_inr(s["total_liabilities"])))
            self.snap_table.setItem(i, 4, table_item(s.get("snapshot_type", "")))
            self.snap_table.setItem(i, 5, table_item(s.get("notes", "")))

        # Store snapshot IDs in hidden column via item data
        self._snapshots = snaps

    def _delete_snapshot(self):
        row = self.snap_table.currentRow()
        if row < 0 or row >= len(self._snapshots):
            return
        snap = self._snapshots[row]
        from app.ui.widgets import confirm_delete
        if confirm_delete(self, f"snapshot {snap['snapshot_date']}"):
            nw_model.delete_snapshot(snap["id"])
            self.refresh()

    def _export_csv(self):
        if not self._rows:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Report", "networth_report.csv", "CSV Files (*.csv)")
        if not path:
            return
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self._rows[0].keys())
            writer.writeheader()
            writer.writerows(self._rows)
        from app.ui.widgets import info_dialog
        info_dialog(self, "Exported", f"Report saved to:\n{path}")

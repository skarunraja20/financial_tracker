"""CSV/Excel import wizard dialog."""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QTextEdit, QWidget,
)
from PyQt6.QtCore import Qt

from app.services import import_service
from app.ui.widgets import title_label, separator, error_dialog, info_dialog
from app.core.constants import FUND_CATEGORY_DEBT, FUND_CATEGORY_EQUITY, FUND_CATEGORY_GOLD


ASSET_TYPE_OPTIONS = [
    ("Fixed Deposits", "fd", ""),
    ("Bonds", "bond", ""),
    ("Debt Mutual Funds", "mutual_fund", FUND_CATEGORY_DEBT),
    ("Equity Mutual Funds", "mutual_fund", FUND_CATEGORY_EQUITY),
    ("Gold Mutual Funds", "mutual_fund", FUND_CATEGORY_GOLD),
    ("Stocks (NSE/BSE)", "stock", ""),
    ("Sovereign Gold Bonds (SGB)", "sgb", ""),
]


class ImportWizard(QDialog):
    def __init__(self, asset_type: str = "", fund_category: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Data from CSV / Excel")
        self.setMinimumSize(720, 520)
        self._preselect_type = asset_type
        self._preselect_category = fund_category
        self._valid_rows = []
        self._filepath = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(title_label("Import Data"))
        layout.addWidget(separator())

        # Step 1: asset type + file
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Asset Type:"))
        self.type_combo = QComboBox()
        for label, atype, cat in ASSET_TYPE_OPTIONS:
            self.type_combo.addItem(label, (atype, cat))
        row1.addWidget(self.type_combo, 1)

        self.btn_browse = QPushButton("Browse File…")
        self.btn_browse.setObjectName("secondaryButton")
        self.btn_browse.clicked.connect(self._browse)
        row1.addWidget(self.btn_browse)
        layout.addLayout(row1)

        self.file_label = QLabel("No file selected.")
        self.file_label.setObjectName("hintLabel")
        layout.addWidget(self.file_label)
        layout.addWidget(separator())

        # Preview table
        layout.addWidget(QLabel("Preview (first 5 rows):"))
        self.preview_table = QTableWidget()
        self.preview_table.setMaximumHeight(160)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.preview_table)

        # Validation log
        layout.addWidget(QLabel("Validation Results:"))
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumHeight(120)
        layout.addWidget(self.log_edit)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_validate = QPushButton("Validate")
        self.btn_validate.setObjectName("secondaryButton")
        self.btn_validate.setEnabled(False)
        self.btn_validate.clicked.connect(self._validate)
        btn_row.addWidget(self.btn_validate)

        self.btn_import = QPushButton("Import")
        self.btn_import.setObjectName("primaryButton")
        self.btn_import.setEnabled(False)
        self.btn_import.clicked.connect(self._do_import)
        btn_row.addWidget(self.btn_import)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        # Pre-select type if provided
        if self._preselect_type:
            for i in range(self.type_combo.count()):
                atype, cat = self.type_combo.itemData(i)
                if atype == self._preselect_type and cat == self._preselect_category:
                    self.type_combo.setCurrentIndex(i)
                    break

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Import File", "",
            "CSV/Excel Files (*.csv *.xlsx *.xls)"
        )
        if not path:
            return
        self._filepath = path
        self.file_label.setText(f"File: {os.path.basename(path)}")
        self.btn_validate.setEnabled(True)
        self._show_preview(path)

    def _show_preview(self, path: str):
        try:
            df = import_service.read_file(path)
            preview = df.head(5)
            self.preview_table.setColumnCount(len(preview.columns))
            self.preview_table.setHorizontalHeaderLabels(list(preview.columns))
            self.preview_table.setRowCount(len(preview))
            for i, row in preview.iterrows():
                for j, val in enumerate(row):
                    self.preview_table.setItem(i, j, QTableWidgetItem(str(val)))
        except Exception as e:
            self.log_edit.setText(f"Error reading file: {e}")

    def _validate(self):
        if not self._filepath:
            return
        try:
            df = import_service.read_file(self._filepath)
            atype, cat = self.type_combo.currentData()
            valid, errors = import_service.validate(df, atype)
            self._valid_rows = valid

            log_lines = []
            if errors:
                log_lines.append(f"⚠ {len(errors)} error(s) found:")
                log_lines.extend(f"  • {e}" for e in errors[:20])
            if valid:
                log_lines.append(f"✓ {len(valid)} valid row(s) ready to import.")

            self.log_edit.setText("\n".join(log_lines))
            self.btn_import.setEnabled(bool(valid))
        except Exception as e:
            self.log_edit.setText(f"Validation error: {e}")

    def _do_import(self):
        if not self._valid_rows:
            return
        atype, cat = self.type_combo.currentData()
        label = self.type_combo.currentText()
        fname = os.path.basename(self._filepath)

        try:
            count = import_service.insert_rows(self._valid_rows, atype, cat)
            import_service.log_import(label, fname, count, 0, "success")
            info_dialog(self, "Import Complete",
                        f"Successfully imported {count} record(s) into {label}.")
            self.accept()
        except Exception as e:
            import_service.log_import(label, fname, 0, len(self._valid_rows), "failed", str(e))
            error_dialog(self, "Import Failed", str(e))

"""Base class for asset list widgets (table + add/edit/delete buttons)."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.ui.widgets import make_table, title_label, separator


class BaseAssetWidget(QWidget):
    """
    Provides a standard layout: title + action buttons (Add, Edit, Delete, Import)
    above a data table.

    Subclasses implement:
      - page_title() → str
      - table_headers() → list[str]
      - load_data() → list of row dicts
      - populate_row(table, row_idx, item_dict) → None
      - open_add_dialog() → None
      - open_edit_dialog(item_dict) → None
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        # Header row
        header = QHBoxLayout()
        header.addWidget(title_label(self.page_title()))
        header.addStretch()

        self.btn_add = QPushButton("+ Add")
        self.btn_add.setObjectName("primaryButton")
        self.btn_add.clicked.connect(self._on_add)
        header.addWidget(self.btn_add)

        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setObjectName("secondaryButton")
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._on_edit)
        header.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setObjectName("dangerButton")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._on_delete)
        header.addWidget(self.btn_delete)

        if self.supports_import():
            self.btn_import = QPushButton("Import CSV/Excel")
            self.btn_import.setObjectName("secondaryButton")
            self.btn_import.clicked.connect(self._on_import)
            header.addWidget(self.btn_import)

        layout.addLayout(header)
        layout.addWidget(separator())

        # Summary label
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("summaryLabel")
        layout.addWidget(self.summary_label)

        # Table
        self.table = make_table(self.table_headers())
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.table.doubleClicked.connect(self._on_edit)
        layout.addWidget(self.table)

    def refresh(self):
        self._items = self.load_data()
        self.table.setRowCount(0)
        for i, item in enumerate(self._items):
            self.table.insertRow(i)
            self.populate_row(self.table, i, item)
        self._on_selection_changed()
        self.update_summary()

    def update_summary(self):
        """Override to show a total / summary line above the table."""
        pass

    def _on_selection_changed(self):
        has_sel = bool(self.table.selectedItems())
        self.btn_edit.setEnabled(has_sel)
        self.btn_delete.setEnabled(has_sel)

    def _selected_item(self) -> dict | None:
        rows = self.table.selectedItems()
        if not rows:
            return None
        row_idx = self.table.currentRow()
        if row_idx < len(self._items):
            return self._items[row_idx]
        return None

    def _on_add(self):
        self.open_add_dialog()
        self.refresh()

    def _on_edit(self):
        item = self._selected_item()
        if item:
            self.open_edit_dialog(item)
            self.refresh()

    def _on_delete(self):
        item = self._selected_item()
        if item:
            from app.ui.widgets import confirm_delete
            name = item.get("bank_name") or item.get("fund_name") or item.get(
                "company_name") or item.get("property_name") or item.get(
                "series_name") or item.get("bond_name") or item.get("lender_name") or "this item"
            if confirm_delete(self, name):
                self.delete_item(item)
                self.refresh()

    def _on_import(self):
        from app.ui.import_export.import_wizard import ImportWizard
        wiz = ImportWizard(asset_type=self.import_asset_type(),
                           fund_category=self.import_fund_category(),
                           parent=self)
        wiz.exec()
        self.refresh()

    # ── Overrideable interface ────────────────────────────────────────────────

    def page_title(self) -> str:
        return "Assets"

    def table_headers(self) -> list[str]:
        return ["Name", "Value"]

    def load_data(self) -> list[dict]:
        return []

    def populate_row(self, table, row_idx: int, item: dict) -> None:
        pass

    def open_add_dialog(self) -> None:
        pass

    def open_edit_dialog(self, item: dict) -> None:
        pass

    def delete_item(self, item: dict) -> None:
        pass

    def supports_import(self) -> bool:
        return False

    def import_asset_type(self) -> str:
        return ""

    def import_fund_category(self) -> str:
        return ""

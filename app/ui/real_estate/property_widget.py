"""Real Estate properties widget."""

from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QCheckBox,
)

from app.models import real_estate as re_model
from app.ui.base_asset_widget import BaseAssetWidget
from app.ui.widgets import (
    make_amount_spin, make_date_edit, make_combo,
    table_item, table_item_right, error_dialog,
)
from app.services.formatters import format_inr, format_date
from app.core.constants import PROPERTY_TYPES, PROPERTY_TYPE_LABELS


class PropertyWidget(BaseAssetWidget):
    def page_title(self): return "Real Estate — Properties"

    def table_headers(self):
        return ["Property", "Type", "Location", "Purchase Price", "Purchase Date", "Current Value", "Gain", "Primary?"]

    def load_data(self):
        return re_model.get_all_properties()

    def populate_row(self, table, row_idx, item):
        gain = item["current_value"] - item["purchase_price"]
        table.setItem(row_idx, 0, table_item(item["property_name"]))
        table.setItem(row_idx, 1, table_item(PROPERTY_TYPE_LABELS.get(item["property_type"], item["property_type"])))
        table.setItem(row_idx, 2, table_item(item.get("location", "")))
        table.setItem(row_idx, 3, table_item_right(format_inr(item["purchase_price"])))
        table.setItem(row_idx, 4, table_item(format_date(item["purchase_date"])))
        table.setItem(row_idx, 5, table_item_right(format_inr(item["current_value"])))
        gain_item = table_item_right(format_inr(gain))
        from PyQt6.QtCore import Qt
        gain_item.setForeground(Qt.GlobalColor.green if gain >= 0 else Qt.GlobalColor.red)
        table.setItem(row_idx, 6, gain_item)
        table.setItem(row_idx, 7, table_item("Yes" if item["is_primary"] else "No"))

    def update_summary(self):
        total_purchase = sum(i["purchase_price"] for i in self._items)
        total_current = sum(i["current_value"] for i in self._items)
        gain = total_current - total_purchase
        self.summary_label.setText(
            f"Total Value: <b>{format_inr(total_current)}</b>  |  "
            f"Purchased at: {format_inr(total_purchase)}  |  "
            f"Appreciation: {format_inr(gain)}"
        )

    def open_add_dialog(self):
        dlg = PropertyDialog(parent=self)
        if dlg.exec():
            re_model.add_property(dlg.get_data())

    def open_edit_dialog(self, item):
        dlg = PropertyDialog(item, parent=self)
        if dlg.exec():
            re_model.update_property(item["id"], dlg.get_data())

    def delete_item(self, item):
        re_model.delete_property(item["id"])


class PropertyDialog(QDialog):
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Property")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name = QLineEdit(data["property_name"] if data else "")
        self.name.setPlaceholderText("e.g. Flat - Whitefield, Bengaluru")
        form.addRow("Property Name*:", self.name)

        self.prop_type = make_combo(PROPERTY_TYPES, PROPERTY_TYPE_LABELS)
        if data:
            idx = self.prop_type.findData(data["property_type"])
            if idx >= 0: self.prop_type.setCurrentIndex(idx)
        form.addRow("Type*:", self.prop_type)

        self.location = QLineEdit(data.get("location", "") if data else "")
        self.location.setPlaceholderText("City / Area")
        form.addRow("Location:", self.location)

        self.purchase_price = make_amount_spin()
        if data: self.purchase_price.setValue(data["purchase_price"])
        form.addRow("Purchase Price*:", self.purchase_price)

        self.purchase_date = make_date_edit()
        if data:
            from PyQt6.QtCore import QDate
            d = QDate.fromString(data["purchase_date"], "yyyy-MM-dd")
            if d.isValid(): self.purchase_date.setDate(d)
        form.addRow("Purchase Date*:", self.purchase_date)

        self.current_value = make_amount_spin()
        if data: self.current_value.setValue(data["current_value"])
        form.addRow("Current Market Value*:", self.current_value)

        self.area = make_amount_spin(prefix="")
        self.area.setDecimals(0)
        self.area.setSuffix(" sq.ft")
        if data and data.get("area_sqft"): self.area.setValue(data["area_sqft"])
        form.addRow("Area:", self.area)

        self.is_primary = QCheckBox("This is my primary residence")
        if data: self.is_primary.setChecked(bool(data.get("is_primary")))
        form.addRow("", self.is_primary)

        self.notes = QTextEdit(data.get("notes", "") if data else "")
        self.notes.setMaximumHeight(50)
        form.addRow("Notes:", self.notes)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Save")
        btn_save.setObjectName("primaryButton")
        btn_save.clicked.connect(self._on_save)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

    def _on_save(self):
        if not self.name.text().strip():
            error_dialog(self, "Validation", "Property name is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        area = self.area.value()
        return {
            "property_name": self.name.text().strip(),
            "property_type": self.prop_type.currentData(),
            "location": self.location.text().strip(),
            "purchase_price": self.purchase_price.value(),
            "purchase_date": self.purchase_date.date().toString("yyyy-MM-dd"),
            "current_value": self.current_value.value(),
            "area_sqft": area if area > 0 else None,
            "is_primary": 1 if self.is_primary.isChecked() else 0,
            "notes": self.notes.toPlainText().strip(),
        }

"""Bonds widget."""

from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit,
)

from app.models import debt as debt_model
from app.ui.base_asset_widget import BaseAssetWidget
from app.ui.widgets import (
    make_amount_spin, make_rate_spin, make_date_edit, make_combo,
    table_item, table_item_right, error_dialog,
)
from app.services.formatters import format_inr, format_date, format_rate
from app.core.constants import BOND_TYPES, BOND_TYPE_LABELS


class BondsWidget(BaseAssetWidget):
    def page_title(self): return "Bonds"

    def table_headers(self):
        return ["Bond Name", "Issuer", "Type", "Units", "Purchase Price", "Current Price", "Current Value", "Coupon"]

    def load_data(self):
        return debt_model.get_all_bonds()

    def populate_row(self, table, row_idx, item):
        price = item.get("current_price") or item["purchase_price"]
        current_val = price * item["units"]
        table.setItem(row_idx, 0, table_item(item["bond_name"]))
        table.setItem(row_idx, 1, table_item(item["issuer"]))
        table.setItem(row_idx, 2, table_item(BOND_TYPE_LABELS.get(item["bond_type"], item["bond_type"])))
        table.setItem(row_idx, 3, table_item_right(f"{item['units']:,.2f}"))
        table.setItem(row_idx, 4, table_item_right(format_inr(item["purchase_price"])))
        table.setItem(row_idx, 5, table_item_right(format_inr(price)))
        table.setItem(row_idx, 6, table_item_right(format_inr(current_val)))
        coupon = item.get("coupon_rate")
        table.setItem(row_idx, 7, table_item_right(f"{coupon:.2f}%" if coupon else "—"))

    def update_summary(self):
        total = sum(
            (i.get("current_price") or i["purchase_price"]) * i["units"]
            for i in self._items
        )
        self.summary_label.setText(f"Total Bond Value: <b>{format_inr(total)}</b>  ({len(self._items)} bonds)")

    def open_add_dialog(self):
        dlg = BondDialog(parent=self)
        if dlg.exec():
            debt_model.add_bond(dlg.get_data())

    def open_edit_dialog(self, item):
        dlg = BondDialog(item, parent=self)
        if dlg.exec():
            debt_model.update_bond(item["id"], dlg.get_data())

    def delete_item(self, item):
        debt_model.delete_bond(item["id"])

    def supports_import(self): return True
    def import_asset_type(self): return "bond"


class BondDialog(QDialog):
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bond")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name = QLineEdit(data["bond_name"] if data else "")
        self.name.setMaxLength(150)
        form.addRow("Bond Name*:", self.name)

        self.issuer = QLineEdit(data["issuer"] if data else "")
        self.issuer.setMaxLength(100)
        form.addRow("Issuer*:", self.issuer)

        self.bond_type = make_combo(BOND_TYPES, BOND_TYPE_LABELS)
        if data:
            idx = self.bond_type.findData(data["bond_type"])
            if idx >= 0: self.bond_type.setCurrentIndex(idx)
        form.addRow("Bond Type*:", self.bond_type)

        self.face_value = make_amount_spin()
        if data: self.face_value.setValue(data["face_value"])
        form.addRow("Face Value*:", self.face_value)

        self.units = make_amount_spin(prefix="")
        self.units.setDecimals(4)
        if data: self.units.setValue(data["units"])
        form.addRow("Units*:", self.units)

        self.purchase_price = make_amount_spin()
        if data: self.purchase_price.setValue(data["purchase_price"])
        form.addRow("Purchase Price (per unit)*:", self.purchase_price)

        self.coupon = make_rate_spin()
        if data and data.get("coupon_rate"): self.coupon.setValue(data["coupon_rate"])
        form.addRow("Coupon Rate (% p.a.):", self.coupon)

        self.purchase_date = make_date_edit()
        if data:
            from PyQt6.QtCore import QDate
            d = QDate.fromString(data["purchase_date"], "yyyy-MM-dd")
            if d.isValid(): self.purchase_date.setDate(d)
        form.addRow("Purchase Date*:", self.purchase_date)

        self.maturity_date = make_date_edit(default_today=False)
        if data and data.get("maturity_date"):
            from PyQt6.QtCore import QDate
            d = QDate.fromString(data["maturity_date"], "yyyy-MM-dd")
            if d.isValid(): self.maturity_date.setDate(d)
        form.addRow("Maturity Date:", self.maturity_date)

        self.current_price = make_amount_spin()
        if data and data.get("current_price"): self.current_price.setValue(data["current_price"])
        form.addRow("Current Price (per unit):", self.current_price)

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
        if not self.name.text().strip() or not self.issuer.text().strip():
            error_dialog(self, "Validation", "Bond name and issuer are required.")
            return
        self.accept()

    def get_data(self) -> dict:
        mat_date = self.maturity_date.date().toString("yyyy-MM-dd")
        cp = self.current_price.value()
        return {
            "bond_name": self.name.text().strip(),
            "issuer": self.issuer.text().strip(),
            "bond_type": self.bond_type.currentData(),
            "face_value": self.face_value.value(),
            "units": self.units.value(),
            "purchase_price": self.purchase_price.value(),
            "coupon_rate": self.coupon.value() or None,
            "purchase_date": self.purchase_date.date().toString("yyyy-MM-dd"),
            "maturity_date": mat_date if mat_date != "0001-01-01" else None,
            "current_price": cp if cp > 0 else None,
            "notes": self.notes.toPlainText().strip(),
        }

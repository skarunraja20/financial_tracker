"""Sovereign Gold Bonds (SGB) widget."""

from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QLabel,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.models import gold as gold_model
from app.models import settings as settings_model
from app.ui.base_asset_widget import BaseAssetWidget
from app.ui.widgets import (
    make_amount_spin, make_rate_spin, make_date_edit,
    table_item, table_item_right, error_dialog, separator,
)
from app.services.formatters import format_inr, format_date


class SGBWidget(BaseAssetWidget):
    def page_title(self): return "Sovereign Gold Bonds (SGB)"

    def table_headers(self):
        return ["Series", "Units (grams)", "Issue Price", "Purchase Date", "Maturity", "Gold Price/gm", "Current Value", "Coupon %"]

    def load_data(self):
        return gold_model.get_all_sgb()

    def populate_row(self, table, row_idx, item):
        gold_price = settings_model.get_gold_price()
        current_val = item["units"] * gold_price
        table.setItem(row_idx, 0, table_item(item["series_name"]))
        table.setItem(row_idx, 1, table_item_right(f"{item['units']:,.4f}"))
        table.setItem(row_idx, 2, table_item_right(f"₹{item['issue_price']:,.2f}"))
        table.setItem(row_idx, 3, table_item(format_date(item["purchase_date"])))
        table.setItem(row_idx, 4, table_item(format_date(item["maturity_date"])))
        table.setItem(row_idx, 5, table_item_right(f"₹{gold_price:,.2f}"))
        table.setItem(row_idx, 6, table_item_right(format_inr(current_val)))
        table.setItem(row_idx, 7, table_item_right(f"{item['coupon_rate']:.2f}%"))

    def update_summary(self):
        gold_price = settings_model.get_gold_price()
        total_units = sum(i["units"] for i in self._items)
        total_val = total_units * gold_price
        cost = sum(i["units"] * i["issue_price"] for i in self._items)

        # Gold price staleness warning
        last_updated = settings_model.get_gold_last_updated()
        warn = ""
        if last_updated:
            from datetime import datetime
            try:
                last_dt = datetime.fromisoformat(last_updated)
                days_old = (datetime.now() - last_dt).days
                if days_old > 30:
                    warn = f"  ⚠ Gold price last updated {days_old} days ago — please update in Settings."
            except Exception:
                pass

        self.summary_label.setText(
            f"Total SGB Value: <b>{format_inr(total_val)}</b>  |  "
            f"Total Units: {total_units:.4f} grams  |  "
            f"Gold Price: ₹{gold_price:,.2f}/gm{warn}"
        )

    def open_add_dialog(self):
        dlg = SGBDialog(parent=self)
        if dlg.exec():
            gold_model.add_sgb(dlg.get_data())

    def open_edit_dialog(self, item):
        dlg = SGBDialog(item, parent=self)
        if dlg.exec():
            gold_model.update_sgb(item["id"], dlg.get_data())

    def delete_item(self, item):
        gold_model.delete_sgb(item["id"])

    def supports_import(self): return True
    def import_asset_type(self): return "sgb"


class SGBDialog(QDialog):
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sovereign Gold Bond")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        hint = QLabel("1 SGB unit = 1 gram of gold. Current value = units × gold price per gram (set in Settings).")
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.series = QLineEdit(data["series_name"] if data else "")
        self.series.setPlaceholderText("e.g. SGB 2021-22 Series VIII")
        self.series.setMaxLength(100)
        form.addRow("Series Name*:", self.series)

        self.units = make_amount_spin(prefix="")
        self.units.setDecimals(4)
        if data: self.units.setValue(data["units"])
        form.addRow("Units (grams)*:", self.units)

        self.issue_price = make_amount_spin()
        if data: self.issue_price.setValue(data["issue_price"])
        form.addRow("Issue Price (per gram)*:", self.issue_price)

        self.purchase_date = make_date_edit()
        if data:
            from PyQt6.QtCore import QDate
            d = QDate.fromString(data["purchase_date"], "yyyy-MM-dd")
            if d.isValid(): self.purchase_date.setDate(d)
        form.addRow("Purchase Date*:", self.purchase_date)

        self.maturity_date = make_date_edit(default_today=False)
        if data:
            from PyQt6.QtCore import QDate
            d = QDate.fromString(data["maturity_date"], "yyyy-MM-dd")
            if d.isValid(): self.maturity_date.setDate(d)
        form.addRow("Maturity Date*:", self.maturity_date)

        self.coupon = make_rate_spin()
        self.coupon.setValue(data["coupon_rate"] if data else 2.5)
        form.addRow("Coupon Rate (% p.a.):", self.coupon)

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
        if not self.series.text().strip():
            error_dialog(self, "Validation", "Series name is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "series_name": self.series.text().strip(),
            "units": self.units.value(),
            "issue_price": self.issue_price.value(),
            "purchase_date": self.purchase_date.date().toString("yyyy-MM-dd"),
            "maturity_date": self.maturity_date.date().toString("yyyy-MM-dd"),
            "coupon_rate": self.coupon.value(),
            "notes": self.notes.toPlainText().strip(),
        }

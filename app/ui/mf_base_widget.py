"""Shared base widget for all mutual fund categories (debt, equity, gold)."""

from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QInputDialog,
)
from PyQt6.QtCore import Qt

from app.models import mutual_fund as mf_model
from app.ui.base_asset_widget import BaseAssetWidget
from app.ui.widgets import (
    make_amount_spin, make_date_edit,
    table_item, table_item_right, error_dialog,
)
from app.services.formatters import format_inr, format_date, format_gain


class MFBaseWidget(BaseAssetWidget):
    """Reused by DebtMFWidget, EquityMFWidget, GoldMFWidget."""

    def fund_category(self) -> str:
        return "debt"

    def table_headers(self):
        return ["Fund Name", "Folio", "Units", "Avg NAV", "Invested", "Current NAV", "Current Value", "Gain/Loss"]

    def load_data(self):
        return mf_model.get_by_category(self.fund_category())

    def populate_row(self, table, row_idx, item):
        current_val = item["units"] * item["current_nav"]
        table.setItem(row_idx, 0, table_item(item["fund_name"]))
        table.setItem(row_idx, 1, table_item(item.get("folio_number", "")))
        table.setItem(row_idx, 2, table_item_right(f"{item['units']:,.4f}"))
        table.setItem(row_idx, 3, table_item_right(f"₹{item['avg_nav']:,.4f}"))
        table.setItem(row_idx, 4, table_item_right(format_inr(item["purchase_value"])))
        table.setItem(row_idx, 5, table_item_right(f"₹{item['current_nav']:,.4f}"))
        table.setItem(row_idx, 6, table_item_right(format_inr(current_val)))
        gain_str = format_gain(current_val, item["purchase_value"])
        gain_item = table_item_right(gain_str)
        if current_val >= item["purchase_value"]:
            gain_item.setForeground(Qt.GlobalColor.green)
        else:
            gain_item.setForeground(Qt.GlobalColor.red)
        table.setItem(row_idx, 7, gain_item)

    def update_summary(self):
        total_invested = sum(i["purchase_value"] for i in self._items)
        total_current = sum(i["units"] * i["current_nav"] for i in self._items)
        gain_str = format_gain(total_current, total_invested) if total_invested else "₹0"
        self.summary_label.setText(
            f"Total Value: <b>{format_inr(total_current)}</b>  |  "
            f"Invested: {format_inr(total_invested)}  |  Gain/Loss: {gain_str}"
        )

    def open_add_dialog(self):
        dlg = MFDialog(fund_category=self.fund_category(), parent=self)
        if dlg.exec():
            mf_model.add(dlg.get_data())

    def open_edit_dialog(self, item):
        dlg = MFDialog(data=item, fund_category=self.fund_category(), parent=self)
        if dlg.exec():
            mf_model.update(item["id"], dlg.get_data())

    def delete_item(self, item):
        mf_model.delete(item["id"])

    def _on_edit(self):
        """Allow double-click to quick-edit NAV."""
        item = self._selected_item()
        if item:
            new_nav, ok = QInputDialog.getDouble(
                self, "Update NAV",
                f"Current NAV for {item['fund_name']}:",
                item["current_nav"], 0.0, 1e9, 4,
            )
            if ok:
                mf_model.update_nav(item["id"], new_nav)
                self.refresh()
            else:
                # Fall back to full edit dialog
                self.open_edit_dialog(item)
                self.refresh()


class MFDialog(QDialog):
    def __init__(self, data=None, fund_category="debt", parent=None):
        super().__init__(parent)
        self.fund_category = fund_category
        self.setWindowTitle("Mutual Fund")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name = QLineEdit(data["fund_name"] if data else "")
        self.name.setPlaceholderText("e.g. Parag Parikh Flexi Cap Fund")
        self.name.setMaxLength(200)
        form.addRow("Fund Name*:", self.name)

        self.amfi = QLineEdit(data.get("amfi_code", "") if data else "")
        self.amfi.setPlaceholderText("Optional AMFI code")
        self.amfi.setMaxLength(20)
        form.addRow("AMFI Code:", self.amfi)

        self.folio = QLineEdit(data.get("folio_number", "") if data else "")
        self.folio.setMaxLength(30)
        form.addRow("Folio Number:", self.folio)

        self.units = make_amount_spin(prefix="")
        self.units.setDecimals(4)
        if data: self.units.setValue(data["units"])
        form.addRow("Units*:", self.units)

        self.avg_nav = make_amount_spin(prefix="₹ ", max_val=1e6)
        self.avg_nav.setDecimals(4)
        if data: self.avg_nav.setValue(data["avg_nav"])
        form.addRow("Average NAV*:", self.avg_nav)

        # Total Invested is auto-calculated from Units × Avg NAV.
        # It is shown read-only so there's never an inconsistency between
        # the three values (the old bug: user typed 2,00,000 with units=100
        # and avg_nav=200, getting a false loss).
        self.purchase_value = make_amount_spin()
        self.purchase_value.setReadOnly(True)
        self.purchase_value.setButtonSymbols(
            self.purchase_value.ButtonSymbols.NoButtons
        )
        self.purchase_value.setStyleSheet("color: #94a3b8;")   # dimmed = calculated
        if data:
            self.purchase_value.setValue(data["purchase_value"])
        else:
            self.purchase_value.setValue(0.0)
        form.addRow("Total Invested (auto):", self.purchase_value)

        # Wire up auto-calculation
        self.units.valueChanged.connect(self._recalc_invested)
        self.avg_nav.valueChanged.connect(self._recalc_invested)
        self._recalc_invested()   # run once on open

        self.current_nav = make_amount_spin(prefix="₹ ", max_val=1e6)
        self.current_nav.setDecimals(4)
        if data: self.current_nav.setValue(data["current_nav"])
        form.addRow("Current NAV*:", self.current_nav)

        self.purchase_date = make_date_edit()
        if data:
            from PyQt6.QtCore import QDate
            d = QDate.fromString(data["purchase_date"], "yyyy-MM-dd")
            if d.isValid(): self.purchase_date.setDate(d)
        form.addRow("Purchase Date*:", self.purchase_date)

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

    def _recalc_invested(self):
        """Keep Total Invested = Units × Avg NAV in sync automatically."""
        self.purchase_value.setValue(self.units.value() * self.avg_nav.value())

    def _on_save(self):
        if not self.name.text().strip():
            error_dialog(self, "Validation", "Fund name is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "fund_name": self.name.text().strip(),
            "amfi_code": self.amfi.text().strip(),
            "folio_number": self.folio.text().strip(),
            "fund_category": self.fund_category,
            "units": self.units.value(),
            "avg_nav": self.avg_nav.value(),
            # Always derived — never an independent user input
            "purchase_value": self.units.value() * self.avg_nav.value(),
            "current_nav": self.current_nav.value(),
            "purchase_date": self.purchase_date.date().toString("yyyy-MM-dd"),
            "notes": self.notes.toPlainText().strip(),
        }

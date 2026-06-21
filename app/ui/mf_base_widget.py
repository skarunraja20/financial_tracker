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


def _effective_current_value(item: dict) -> float:
    cv = item.get("current_value")
    if cv is not None and cv > 0:
        return cv
    return item["units"] * item["current_nav"]


class MFBaseWidget(BaseAssetWidget):
    """Reused by DebtMFWidget, EquityMFWidget, GoldMFWidget."""

    def fund_category(self) -> str:
        return "debt"

    def table_headers(self):
        return ["Fund Name", "Folio", "Units", "Avg NAV", "Invested", "Current NAV", "Current Value", "Gain/Loss"]

    def load_data(self):
        return mf_model.get_by_category(self.fund_category())

    def populate_row(self, table, row_idx, item):
        current_val = _effective_current_value(item)
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
        total_current = sum(_effective_current_value(i) for i in self._items)
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
        self._manual_invested = False
        self._manual_current_value = False
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
        form.addRow("Units:", self.units)

        self.avg_nav = make_amount_spin(prefix="₹ ", max_val=1e6)
        self.avg_nav.setDecimals(4)
        if data: self.avg_nav.setValue(data["avg_nav"])
        form.addRow("Average NAV:", self.avg_nav)

        self.purchase_value = make_amount_spin()
        if data:
            self.purchase_value.setValue(data["purchase_value"])
        else:
            self.purchase_value.setValue(0.0)
        form.addRow("Total Invested:", self.purchase_value)

        self.units.valueChanged.connect(self._recalc_invested)
        self.avg_nav.valueChanged.connect(self._recalc_invested)
        self.purchase_value.valueChanged.connect(self._on_invested_changed)

        self.current_nav = make_amount_spin(prefix="₹ ", max_val=1e6)
        self.current_nav.setDecimals(4)
        if data: self.current_nav.setValue(data["current_nav"])
        form.addRow("Current NAV:", self.current_nav)

        self.current_value = make_amount_spin()
        existing_cv = data.get("current_value") if data else None
        if existing_cv is not None and existing_cv > 0:
            self.current_value.setValue(existing_cv)
            self._manual_current_value = True
        else:
            self._recalc_current_value()
        form.addRow("Current Value:", self.current_value)

        self.current_nav.valueChanged.connect(self._recalc_current_value)
        self.units.valueChanged.connect(self._recalc_current_value)
        self.current_value.valueChanged.connect(self._on_current_value_changed)

        self.purchase_date = make_date_edit()
        if data:
            from PyQt6.QtCore import QDate
            d = QDate.fromString(data["purchase_date"], "yyyy-MM-dd")
            if d.isValid(): self.purchase_date.setDate(d)
        form.addRow("Purchase Date:", self.purchase_date)

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
        if self._manual_invested:
            return
        self.purchase_value.blockSignals(True)
        self.purchase_value.setValue(self.units.value() * self.avg_nav.value())
        self.purchase_value.blockSignals(False)

    def _on_invested_changed(self):
        calculated = self.units.value() * self.avg_nav.value()
        if abs(self.purchase_value.value() - calculated) > 0.01:
            self._manual_invested = True

    def _recalc_current_value(self):
        if self._manual_current_value:
            return
        self.current_value.blockSignals(True)
        self.current_value.setValue(self.units.value() * self.current_nav.value())
        self.current_value.blockSignals(False)

    def _on_current_value_changed(self):
        calculated = self.units.value() * self.current_nav.value()
        if abs(self.current_value.value() - calculated) > 0.01:
            self._manual_current_value = True

    def _on_save(self):
        if not self.name.text().strip():
            error_dialog(self, "Validation", "Fund name is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        invested = self.purchase_value.value()
        if not self._manual_invested and self.units.value() > 0 and self.avg_nav.value() > 0:
            invested = self.units.value() * self.avg_nav.value()

        cv = self.current_value.value()
        current_value_to_store = None
        if self._manual_current_value and cv > 0:
            current_value_to_store = cv

        return {
            "fund_name": self.name.text().strip(),
            "amfi_code": self.amfi.text().strip(),
            "folio_number": self.folio.text().strip(),
            "fund_category": self.fund_category,
            "units": self.units.value(),
            "avg_nav": self.avg_nav.value(),
            "purchase_value": invested,
            "current_nav": self.current_nav.value(),
            "current_value": current_value_to_store,
            "purchase_date": self.purchase_date.date().toString("yyyy-MM-dd"),
            "notes": self.notes.toPlainText().strip(),
        }

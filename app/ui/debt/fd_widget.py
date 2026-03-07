"""Fixed Deposits widget."""

from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QLabel,
)
from PyQt6.QtCore import Qt

from app.models import debt as debt_model
from app.ui.base_asset_widget import BaseAssetWidget
from app.ui.widgets import (
    make_amount_spin, make_rate_spin, make_date_edit, make_combo,
    table_item, table_item_right, error_dialog,
)
from app.services.formatters import format_inr, format_date, format_rate
from app.core.constants import COMPOUNDING_OPTIONS, COMPOUNDING_LABELS


class FDWidget(BaseAssetWidget):
    def page_title(self): return "Fixed Deposits"

    def table_headers(self):
        return ["Bank", "Principal", "Rate", "Compounding", "Start", "Maturity", "Current Value", "Status"]

    def load_data(self):
        return debt_model.get_all_fds(active_only=True)

    def populate_row(self, table, row_idx, item):
        current_val = item.get("current_value") or debt_model.calculate_fd_value(
            item["principal"], item["interest_rate"], item["compounding"], item["start_date"]
        )
        table.setItem(row_idx, 0, table_item(item["bank_name"]))
        table.setItem(row_idx, 1, table_item_right(format_inr(item["principal"])))
        table.setItem(row_idx, 2, table_item_right(format_rate(item["interest_rate"])))
        table.setItem(row_idx, 3, table_item(COMPOUNDING_LABELS.get(item["compounding"], item["compounding"])))
        table.setItem(row_idx, 4, table_item(format_date(item["start_date"])))
        table.setItem(row_idx, 5, table_item(format_date(item["maturity_date"])))
        table.setItem(row_idx, 6, table_item_right(format_inr(current_val)))
        table.setItem(row_idx, 7, table_item("Active" if item["is_active"] else "Closed"))

    def update_summary(self):
        total = sum(
            i.get("current_value") or debt_model.calculate_fd_value(
                i["principal"], i["interest_rate"], i["compounding"], i["start_date"]
            )
            for i in self._items
        )
        self.summary_label.setText(f"Total FD Value: <b>{format_inr(total)}</b>  ({len(self._items)} FDs)")

    def open_add_dialog(self):
        dlg = FDDialog(parent=self)
        if dlg.exec():
            debt_model.add_fd(dlg.get_data())

    def open_edit_dialog(self, item):
        dlg = FDDialog(item, parent=self)
        if dlg.exec():
            debt_model.update_fd(item["id"], dlg.get_data())

    def delete_item(self, item):
        debt_model.delete_fd(item["id"])

    def supports_import(self): return True
    def import_asset_type(self): return "fd"


class FDDialog(QDialog):
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fixed Deposit")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.bank = QLineEdit(data["bank_name"] if data else "")
        self.bank.setPlaceholderText("e.g. HDFC Bank")
        form.addRow("Bank Name*:", self.bank)

        self.fd_no = QLineEdit(data.get("fd_number", "") if data else "")
        self.fd_no.setPlaceholderText("Optional")
        form.addRow("FD Number:", self.fd_no)

        self.principal = make_amount_spin()
        if data: self.principal.setValue(data["principal"])
        form.addRow("Principal*:", self.principal)

        self.rate = make_rate_spin()
        if data: self.rate.setValue(data["interest_rate"])
        form.addRow("Interest Rate (% p.a.)*:", self.rate)

        self.compounding = make_combo(COMPOUNDING_OPTIONS, COMPOUNDING_LABELS)
        if data:
            idx = self.compounding.findData(data["compounding"])
            if idx >= 0: self.compounding.setCurrentIndex(idx)
        form.addRow("Compounding*:", self.compounding)

        self.start_date = make_date_edit()
        if data:
            from PyQt6.QtCore import QDate
            d = QDate.fromString(data["start_date"], "yyyy-MM-dd")
            if d.isValid(): self.start_date.setDate(d)
        form.addRow("Start Date*:", self.start_date)

        self.maturity_date = make_date_edit(default_today=False)
        if data:
            from PyQt6.QtCore import QDate
            d = QDate.fromString(data["maturity_date"], "yyyy-MM-dd")
            if d.isValid(): self.maturity_date.setDate(d)
        form.addRow("Maturity Date*:", self.maturity_date)

        self.maturity_amount = make_amount_spin()
        if data and data.get("maturity_amount"):
            self.maturity_amount.setValue(data["maturity_amount"])
        form.addRow("Maturity Amount (optional):", self.maturity_amount)

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
        if not self.bank.text().strip():
            error_dialog(self, "Validation", "Bank name is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        mat_amt = self.maturity_amount.value()
        return {
            "bank_name": self.bank.text().strip(),
            "fd_number": self.fd_no.text().strip(),
            "principal": self.principal.value(),
            "interest_rate": self.rate.value(),
            "compounding": self.compounding.currentData(),
            "start_date": self.start_date.date().toString("yyyy-MM-dd"),
            "maturity_date": self.maturity_date.date().toString("yyyy-MM-dd"),
            "maturity_amount": mat_amt if mat_amt > 0 else None,
            "notes": self.notes.toPlainText().strip(),
        }

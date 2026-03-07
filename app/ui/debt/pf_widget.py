"""Provident Fund widget — single record edit form."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QPushButton,
    QLabel, QLineEdit, QTextEdit, QFrame, QHBoxLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.models import debt as debt_model
from app.ui.widgets import (
    title_label, field_label, section_label, separator,
    make_amount_spin, make_date_edit, info_dialog, error_dialog,
)
from app.services.formatters import format_inr, format_date


class PFWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(title_label("Provident Fund (PF)"))

        hint = QLabel("PF balance is tracked as a single total figure. Update it periodically from your EPFO passbook.")
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addWidget(separator())

        # Current balance display
        self.balance_display = QLabel("Current Balance: ₹0")
        self.balance_display.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.balance_display.setObjectName("bigValue")
        layout.addWidget(self.balance_display)

        self.date_display = QLabel("As of: —")
        self.date_display.setObjectName("subValue")
        layout.addWidget(self.date_display)

        layout.addWidget(separator())
        layout.addWidget(section_label("Update Balance"))

        form = QFormLayout()
        form.setSpacing(10)

        self.balance_spin = make_amount_spin()
        form.addRow("Total PF Balance:", self.balance_spin)

        self.date_edit = make_date_edit()
        form.addRow("As of Date:", self.date_edit)

        self.acct_edit = QLineEdit()
        self.acct_edit.setPlaceholderText("Optional — account number (masked)")
        form.addRow("Account Number:", self.acct_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(60)
        self.notes_edit.setPlaceholderText("Optional notes")
        form.addRow("Notes:", self.notes_edit)

        layout.addLayout(form)

        btn_save = QPushButton("Save")
        btn_save.setObjectName("primaryButton")
        btn_save.setMaximumWidth(120)
        btn_save.clicked.connect(self._save)
        layout.addWidget(btn_save)

        layout.addStretch()

    def refresh(self):
        pf = debt_model.get_pf()
        if pf:
            self.balance_display.setText(f"Current Balance: {format_inr(pf['total_balance'])}")
            self.date_display.setText(f"As of: {format_date(pf['as_of_date'])}")
            self.balance_spin.setValue(pf["total_balance"])
            self.acct_edit.setText(pf.get("account_number", ""))
            self.notes_edit.setPlainText(pf.get("notes", ""))
            from PyQt6.QtCore import QDate
            d = QDate.fromString(pf["as_of_date"], "yyyy-MM-dd")
            if d.isValid():
                self.date_edit.setDate(d)

    def _save(self):
        balance = self.balance_spin.value()
        as_of = self.date_edit.date().toString("yyyy-MM-dd")
        acct = self.acct_edit.text().strip()
        notes = self.notes_edit.toPlainText().strip()
        debt_model.save_pf(balance, as_of, acct, notes)
        self.refresh()
        info_dialog(self, "Saved", "PF balance updated.")

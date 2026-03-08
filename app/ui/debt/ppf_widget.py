"""Public Provident Fund (PPF) widget — single-record edit form."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QPushButton,
    QLabel, QLineEdit, QTextEdit, QHBoxLayout,
    QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.models import debt as debt_model
from app.ui.widgets import (
    title_label, section_label, separator,
    make_amount_spin, make_date_edit, info_dialog, error_dialog,
)
from app.services.formatters import format_inr, format_date, format_rate

_INPUT_H = 34   # minimum height for all input controls


class PPFWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        # ── Scroll area wraps all content ────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # ── Title + hint ──────────────────────────────────────────────────────
        layout.addWidget(title_label("Public Provident Fund (PPF)"))

        hint = QLabel(
            "PPF is a government-backed, 15-year savings scheme. "
            "Update your balance periodically from your bank passbook or statement."
        )
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addWidget(separator())

        # ── Summary display ───────────────────────────────────────────────────
        self.balance_display = QLabel("Current Balance: ₹0")
        self.balance_display.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.balance_display.setObjectName("bigValue")
        layout.addWidget(self.balance_display)

        info_row = QHBoxLayout()
        self.date_display = QLabel("As of: —")
        self.date_display.setObjectName("subValue")
        self.rate_display = QLabel("Interest Rate: —")
        self.rate_display.setObjectName("subValue")
        self.maturity_display = QLabel("Maturity: —")
        self.maturity_display.setObjectName("subValue")
        info_row.addWidget(self.date_display)
        info_row.addWidget(QLabel("  |  "))
        info_row.addWidget(self.rate_display)
        info_row.addWidget(QLabel("  |  "))
        info_row.addWidget(self.maturity_display)
        info_row.addStretch()
        layout.addLayout(info_row)

        layout.addWidget(separator())
        layout.addWidget(section_label("Update Details"))

        # ── Form ──────────────────────────────────────────────────────────────
        form = QFormLayout()
        form.setSpacing(10)

        self.balance_spin = make_amount_spin()
        self.balance_spin.setMinimumHeight(_INPUT_H)
        form.addRow("Current Balance (₹):", self.balance_spin)

        self.as_of_date_edit = make_date_edit()
        self.as_of_date_edit.setMinimumHeight(_INPUT_H)
        form.addRow("As of Date:", self.as_of_date_edit)

        self.annual_spin = make_amount_spin(max_val=150000)
        self.annual_spin.setMinimumHeight(_INPUT_H)
        form.addRow("Annual Contribution (₹):", self.annual_spin)

        self.rate_spin = make_amount_spin(min_val=0.0, max_val=20.0, prefix="")
        self.rate_spin.setDecimals(2)
        self.rate_spin.setSuffix(" %")
        self.rate_spin.setValue(7.1)
        self.rate_spin.setMinimumHeight(_INPUT_H)
        form.addRow("Interest Rate (%):", self.rate_spin)

        self.acct_edit = QLineEdit()
        self.acct_edit.setPlaceholderText("e.g. 0012345678 (optional)")
        self.acct_edit.setMinimumHeight(_INPUT_H)
        form.addRow("Account Number:", self.acct_edit)

        self.bank_edit = QLineEdit()
        self.bank_edit.setPlaceholderText("e.g. SBI, Post Office, HDFC")
        self.bank_edit.setMinimumHeight(_INPUT_H)
        form.addRow("Bank / Post Office:", self.bank_edit)

        self.opening_date_edit = make_date_edit()
        self.opening_date_edit.setMinimumHeight(_INPUT_H)
        form.addRow("Opening Date:", self.opening_date_edit)

        self.maturity_date_edit = make_date_edit()
        self.maturity_date_edit.setMinimumHeight(_INPUT_H)
        form.addRow("Maturity Date:", self.maturity_date_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(70)
        self.notes_edit.setPlaceholderText("Optional notes")
        form.addRow("Notes:", self.notes_edit)

        layout.addLayout(form)

        btn_save = QPushButton("Save")
        btn_save.setObjectName("primaryButton")
        btn_save.setMaximumWidth(120)
        btn_save.clicked.connect(self._save)
        layout.addWidget(btn_save)

        layout.addStretch()

        # ── Wire scroll area ──────────────────────────────────────────────────
        scroll.setWidget(content)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def refresh(self):
        ppf = debt_model.get_ppf()
        if ppf:
            self.balance_display.setText(
                f"Current Balance: {format_inr(ppf['current_balance'])}"
            )
            self.date_display.setText(f"As of: {format_date(ppf['as_of_date'])}")
            self.rate_display.setText(f"Interest Rate: {format_rate(ppf['interest_rate'])}")
            self.maturity_display.setText(
                f"Maturity: {format_date(ppf['maturity_date']) if ppf.get('maturity_date') else '—'}"
            )
            self.balance_spin.setValue(ppf["current_balance"])
            self.annual_spin.setValue(ppf.get("annual_contribution", 0.0))
            self.rate_spin.setValue(ppf.get("interest_rate", 7.1))
            self.acct_edit.setText(ppf.get("account_number", ""))
            self.bank_edit.setText(ppf.get("bank_name", ""))
            self.notes_edit.setPlainText(ppf.get("notes", ""))

            from PyQt6.QtCore import QDate
            for date_str, widget in [
                (ppf["as_of_date"], self.as_of_date_edit),
                (ppf.get("opening_date", ""), self.opening_date_edit),
                (ppf.get("maturity_date", ""), self.maturity_date_edit),
            ]:
                if date_str:
                    d = QDate.fromString(date_str, "yyyy-MM-dd")
                    if d.isValid():
                        widget.setDate(d)

    def _save(self):
        balance = self.balance_spin.value()
        as_of = self.as_of_date_edit.date().toString("yyyy-MM-dd")
        debt_model.save_ppf(
            current_balance=balance,
            as_of_date=as_of,
            account_number=self.acct_edit.text().strip(),
            bank_name=self.bank_edit.text().strip(),
            opening_date=self.opening_date_edit.date().toString("yyyy-MM-dd"),
            maturity_date=self.maturity_date_edit.date().toString("yyyy-MM-dd"),
            annual_contribution=self.annual_spin.value(),
            interest_rate=self.rate_spin.value(),
            notes=self.notes_edit.toPlainText().strip(),
        )
        self.refresh()
        info_dialog(self, "Saved", "PPF account updated.")

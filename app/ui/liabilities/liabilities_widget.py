"""Liabilities widget: Home Loan, Personal Loan, Gold Loan, MF Loan."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QDialog, QFormLayout, QPushButton, QLineEdit,
    QTextEdit, QLabel, QComboBox, QCheckBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.models import liabilities as liab_model
from app.models import real_estate as re_model
from app.models import mutual_fund as mf_model
from app.ui.base_asset_widget import BaseAssetWidget
from app.ui.widgets import (
    make_amount_spin, make_rate_spin, make_date_edit, make_combo,
    table_item, table_item_right, title_label, separator, error_dialog,
)
from app.services.formatters import format_inr, format_date, format_rate
from app.core.constants import (
    LOAN_HOME, LOAN_PERSONAL, LOAN_GOLD, LOAN_MF, LOAN_TYPE_LABELS,
    PERSONAL_LOAN_PURPOSES,
)


class LiabilitiesWidget(QWidget):
    """Tab-based view for all liability types."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(title_label("Liabilities"))
        header.addStretch()
        self.total_label = QLabel("")
        self.total_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.total_label.setObjectName("totalLabel")
        header.addWidget(self.total_label)
        layout.addLayout(header)
        layout.addWidget(separator())

        self.tabs = QTabWidget()
        self.tabs.setObjectName("liabTabs")

        self.home_tab = LiabilitySectionWidget(LOAN_HOME)
        self.personal_tab = LiabilitySectionWidget(LOAN_PERSONAL)
        self.gold_tab = LiabilitySectionWidget(LOAN_GOLD)
        self.mf_tab = LiabilitySectionWidget(LOAN_MF)

        self.tabs.addTab(self.home_tab, "Home Loans")
        self.tabs.addTab(self.personal_tab, "Personal Loans")
        self.tabs.addTab(self.gold_tab, "Gold Loans")
        self.tabs.addTab(self.mf_tab, "MF Loans")

        layout.addWidget(self.tabs)

    def refresh(self):
        self.home_tab.refresh()
        self.personal_tab.refresh()
        self.gold_tab.refresh()
        self.mf_tab.refresh()

        totals = liab_model.get_totals_by_type()
        grand_total = sum(totals.values())
        self.total_label.setText(f"Total Outstanding: {format_inr(grand_total)}")


class LiabilitySectionWidget(BaseAssetWidget):
    def __init__(self, loan_type: str, parent=None):
        self._loan_type = loan_type
        super().__init__(parent)

    def page_title(self):
        return LOAN_TYPE_LABELS.get(self._loan_type, self._loan_type)

    def table_headers(self):
        return ["Lender", "Original Amount", "Outstanding", "Rate", "EMI", "Sanction Date", "End Date", "Linked Asset"]

    def load_data(self):
        return liab_model.get_all(active_only=True, loan_type=self._loan_type)

    def populate_row(self, table, row_idx, item):
        linked = ""
        if self._loan_type == LOAN_HOME and item.get("property_name"):
            linked = item["property_name"]
        elif self._loan_type == LOAN_MF and item.get("fund_name"):
            linked = item["fund_name"]
        elif self._loan_type == LOAN_GOLD and item.get("gold_weight_grams"):
            linked = f"{item['gold_weight_grams']:.2f}g pledged"

        table.setItem(row_idx, 0, table_item(item["lender_name"]))
        table.setItem(row_idx, 1, table_item_right(format_inr(item["original_amount"])))
        table.setItem(row_idx, 2, table_item_right(format_inr(item["outstanding_amount"])))
        table.setItem(row_idx, 3, table_item_right(format_rate(item["interest_rate"])))
        emi = item.get("emi_amount")
        table.setItem(row_idx, 4, table_item_right(format_inr(emi) if emi else "—"))
        table.setItem(row_idx, 5, table_item(format_date(item["sanction_date"])))
        table.setItem(row_idx, 6, table_item(format_date(item.get("loan_end_date", "")) if item.get("loan_end_date") else "—"))
        table.setItem(row_idx, 7, table_item(linked))

    def update_summary(self):
        total_outstanding = sum(i["outstanding_amount"] for i in self._items)
        total_original = sum(i["original_amount"] for i in self._items)
        self.summary_label.setText(
            f"Outstanding: <b>{format_inr(total_outstanding)}</b>  |  "
            f"Original: {format_inr(total_original)}  |  "
            f"Count: {len(self._items)}"
        )

    def open_add_dialog(self):
        dlg = LiabilityDialog(loan_type=self._loan_type, parent=self)
        if dlg.exec():
            liab_model.add(dlg.get_data())

    def open_edit_dialog(self, item):
        dlg = LiabilityDialog(loan_type=self._loan_type, data=item, parent=self)
        if dlg.exec():
            liab_model.update(item["id"], dlg.get_data())

    def delete_item(self, item):
        liab_model.delete(item["id"])


class LiabilityDialog(QDialog):
    def __init__(self, loan_type: str, data=None, parent=None):
        super().__init__(parent)
        self.loan_type = loan_type
        self.setWindowTitle(f"{LOAN_TYPE_LABELS.get(loan_type, loan_type)}")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.lender = QLineEdit(data["lender_name"] if data else "")
        self.lender.setPlaceholderText("e.g. SBI, HDFC, Bajaj Finance")
        form.addRow("Lender Name*:", self.lender)

        self.loan_acct = QLineEdit(data.get("loan_account", "") if data else "")
        self.loan_acct.setPlaceholderText("Optional")
        form.addRow("Loan Account:", self.loan_acct)

        self.original = make_amount_spin()
        if data: self.original.setValue(data["original_amount"])
        form.addRow("Original Amount*:", self.original)

        self.outstanding = make_amount_spin()
        if data: self.outstanding.setValue(data["outstanding_amount"])
        form.addRow("Outstanding Amount*:", self.outstanding)

        self.rate = make_rate_spin()
        if data: self.rate.setValue(data["interest_rate"])
        form.addRow("Interest Rate (% p.a.)*:", self.rate)

        self.emi = make_amount_spin()
        if data and data.get("emi_amount"): self.emi.setValue(data["emi_amount"])
        form.addRow("EMI Amount:", self.emi)

        self.sanction_date = make_date_edit()
        if data:
            from PyQt6.QtCore import QDate
            d = QDate.fromString(data["sanction_date"], "yyyy-MM-dd")
            if d.isValid(): self.sanction_date.setDate(d)
        form.addRow("Sanction Date*:", self.sanction_date)

        self.end_date = make_date_edit(default_today=False)
        if data and data.get("loan_end_date"):
            from PyQt6.QtCore import QDate
            d = QDate.fromString(data["loan_end_date"], "yyyy-MM-dd")
            if d.isValid(): self.end_date.setDate(d)
        form.addRow("Loan End Date:", self.end_date)

        # Type-specific fields
        self.linked_property_combo = None
        self.linked_fund_combo = None
        self.gold_weight = None
        self.purpose_combo = None

        if loan_type == LOAN_HOME:
            self.linked_property_combo = QComboBox()
            self.linked_property_combo.addItem("— None —", None)
            properties = re_model.get_property_choices()
            for pid, pname in properties:
                self.linked_property_combo.addItem(pname, pid)
            if data and data.get("linked_property_id"):
                idx = self.linked_property_combo.findData(data["linked_property_id"])
                if idx >= 0: self.linked_property_combo.setCurrentIndex(idx)
            form.addRow("Linked Property:", self.linked_property_combo)

        elif loan_type == LOAN_GOLD:
            self.gold_weight = make_amount_spin(prefix="")
            self.gold_weight.setSuffix(" grams")
            self.gold_weight.setDecimals(3)
            if data and data.get("gold_weight_grams"):
                self.gold_weight.setValue(data["gold_weight_grams"])
            form.addRow("Gold Pledged:", self.gold_weight)

        elif loan_type == LOAN_PERSONAL:
            self.purpose_combo = make_combo(PERSONAL_LOAN_PURPOSES)
            if data and data.get("purpose"):
                idx = self.purpose_combo.findText(data["purpose"])
                if idx >= 0: self.purpose_combo.setCurrentIndex(idx)
            form.addRow("Purpose:", self.purpose_combo)

        elif loan_type == LOAN_MF:
            self.linked_fund_combo = QComboBox()
            self.linked_fund_combo.addItem("— None —", None)
            funds = mf_model.get_all_active()
            for f in funds:
                self.linked_fund_combo.addItem(f["fund_name"], f["id"])
            if data and data.get("linked_fund_id"):
                idx = self.linked_fund_combo.findData(data["linked_fund_id"])
                if idx >= 0: self.linked_fund_combo.setCurrentIndex(idx)
            form.addRow("Pledged MF:", self.linked_fund_combo)

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
        if not self.lender.text().strip():
            error_dialog(self, "Validation", "Lender name is required.")
            return
        self.accept()

    def get_data(self) -> dict:
        end = self.end_date.date().toString("yyyy-MM-dd")
        emi = self.emi.value()
        d = {
            "loan_type": self.loan_type,
            "lender_name": self.lender.text().strip(),
            "loan_account": self.loan_acct.text().strip(),
            "original_amount": self.original.value(),
            "outstanding_amount": self.outstanding.value(),
            "interest_rate": self.rate.value(),
            "emi_amount": emi if emi > 0 else None,
            "sanction_date": self.sanction_date.date().toString("yyyy-MM-dd"),
            "loan_end_date": end if end != "0001-01-01" else None,
            "linked_property_id": None,
            "linked_fund_id": None,
            "gold_weight_grams": None,
            "purpose": None,
            "notes": self.notes.toPlainText().strip(),
        }
        if self.linked_property_combo:
            d["linked_property_id"] = self.linked_property_combo.currentData()
        if self.linked_fund_combo:
            d["linked_fund_id"] = self.linked_fund_combo.currentData()
        if self.gold_weight:
            d["gold_weight_grams"] = self.gold_weight.value() or None
        if self.purpose_combo:
            d["purpose"] = self.purpose_combo.currentText()
        return d

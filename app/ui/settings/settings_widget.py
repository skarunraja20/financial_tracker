"""Settings widget: exchange rate, gold price, security, backup, theme."""

import os
import shutil
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QComboBox,
    QFrame, QScrollArea, QDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.models import settings as settings_model
from app.models import auth as auth_model
from app.core.constants import (
    DB_PATH, BACKUP_DIR, SECURITY_QUESTIONS, MAX_PASSWORD_LENGTH,
    CURRENCIES, TEMPLATES_DIR,
)
from app.core import security as sec
from app.ui.widgets import (
    make_amount_spin, make_rate_spin, title_label, separator,
    field_label, section_label, info_dialog, error_dialog,
)
from app.services import import_service


class SettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    # ── Section card helper ────────────────────────────────────────────────────
    def _make_section_card(self, title: str):
        """Returns (outer_wrapper_widget, card_inner_layout).

        Uses a plain QLabel for the title instead of QGroupBox::title subcontrol,
        which is unreliable in PyQt6 and clips at the margin-top boundary.
        """
        outer = QWidget()
        vbox = QVBoxLayout(outer)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(8)

        # Fully visible title label — no floating subcontrol tricks needed
        lbl = QLabel(title)
        lbl.setObjectName("settingsCardTitle")
        vbox.addWidget(lbl)

        # Bordered card frame
        card = QFrame()
        card.setObjectName("settingsCard")
        inner = QVBoxLayout(card)
        inner.setContentsMargins(18, 16, 18, 16)
        inner.setSpacing(10)
        vbox.addWidget(card)

        return outer, inner

    # ── Build UI ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        layout.addWidget(title_label("Settings"))
        layout.addWidget(separator())

        layout.addWidget(self._build_rates_section())
        layout.addWidget(self._build_security_section())
        layout.addWidget(self._build_backup_section())
        layout.addWidget(self._build_templates_section())
        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── Section builders ───────────────────────────────────────────────────────
    def _build_rates_section(self) -> QWidget:
        outer, inner = self._make_section_card("Rates & Prices")

        form = QFormLayout()
        form.setSpacing(10)

        # ── Currency selector ─────────────────────────────────────────────────
        self.currency_combo = QComboBox()
        self.currency_combo.setMinimumHeight(36)
        saved_code = settings_model.get_currency()
        saved_idx  = 0
        for i, (code, meta) in enumerate(CURRENCIES.items()):
            self.currency_combo.addItem(
                f"{code}  —  {meta['name']}  ({meta['symbol']})", userData=code
            )
            if code == saved_code:
                saved_idx = i
        self.currency_combo.setCurrentIndex(saved_idx)
        form.addRow("Display Currency:", self.currency_combo)

        # Rate field — label and value update when currency changes
        self._rate_lbl = QLabel(f"1 {saved_code} = ₹")
        self.currency_rate_spin = make_amount_spin(min_val=0.001, max_val=1e6, prefix="₹ ")
        self.currency_rate_spin.setDecimals(4)
        self.currency_rate_spin.setValue(settings_model.get_currency_rate(saved_code))
        form.addRow(self._rate_lbl, self.currency_rate_spin)

        hint = QLabel("Enter the current market rate manually (no internet used).")
        hint.setObjectName("hintLabel")
        form.addRow("", hint)

        btn_save_rate = QPushButton("Save Currency & Rate")
        btn_save_rate.setObjectName("secondaryButton")
        btn_save_rate.clicked.connect(self._save_currency_rate)
        form.addRow("", btn_save_rate)

        # Wire up combo → rate field update
        self.currency_combo.currentIndexChanged.connect(self._on_currency_changed)

        form.addRow("", separator())

        # ── Gold price ────────────────────────────────────────────────────────
        self.gold_spin = make_amount_spin(min_val=1, max_val=1e7)
        self.gold_spin.setValue(settings_model.get_gold_price())
        self.gold_spin.setSuffix(" / gram")
        form.addRow("Gold Price (INR per gram):", self.gold_spin)

        last_upd = settings_model.get_gold_last_updated()
        if last_upd:
            try:
                dt = datetime.fromisoformat(last_upd)
                self.gold_last_lbl = QLabel(f"Last updated: {dt.strftime('%d-%b-%Y %H:%M')}")
            except Exception:
                self.gold_last_lbl = QLabel("")
        else:
            self.gold_last_lbl = QLabel("Not yet set")
        self.gold_last_lbl.setObjectName("hintLabel")
        form.addRow("", self.gold_last_lbl)

        btn_save_gold = QPushButton("Save Gold Price")
        btn_save_gold.setObjectName("secondaryButton")
        btn_save_gold.clicked.connect(self._save_gold_price)
        form.addRow("", btn_save_gold)

        inner.addLayout(form)
        return outer

    def _build_security_section(self) -> QWidget:
        outer, inner = self._make_section_card("Security")

        btn_pwd = QPushButton("Change Password")
        btn_pwd.setObjectName("secondaryButton")
        btn_pwd.clicked.connect(self._change_password)
        inner.addWidget(btn_pwd)

        btn_qs = QPushButton("Update Security Questions")
        btn_qs.setObjectName("secondaryButton")
        btn_qs.clicked.connect(self._update_questions)
        inner.addWidget(btn_qs)

        return outer

    def _build_backup_section(self) -> QWidget:
        outer, inner = self._make_section_card("Backup")

        lbl = QLabel(f"Database location: {DB_PATH}")
        lbl.setObjectName("hintLabel")
        lbl.setWordWrap(True)
        inner.addWidget(lbl)

        btn_backup = QPushButton("Backup Database Now")
        btn_backup.setObjectName("primaryButton")
        btn_backup.clicked.connect(self._backup)
        inner.addWidget(btn_backup)

        return outer

    def _build_templates_section(self) -> QWidget:
        outer, inner = self._make_section_card("Download Import Templates")

        lbl = QLabel("Download CSV templates to fill in and then import.")
        lbl.setObjectName("hintLabel")
        inner.addWidget(lbl)

        for label, filename in [
            ("Fixed Deposits Template", "fd_template.csv"),
            ("Bonds Template", "bonds_template.csv"),
            ("Mutual Funds Template", "mf_template.csv"),
            ("Stocks Template", "stocks_template.csv"),
            ("SGB Template", "sgb_template.csv"),
        ]:
            btn = QPushButton(f"Save {label}")
            btn.setObjectName("secondaryButton")
            btn.clicked.connect(lambda _, fn=filename: self._save_template(fn))
            inner.addWidget(btn)

        return outer

    # ── Refresh ────────────────────────────────────────────────────────────────
    def refresh(self):
        code = settings_model.get_currency()
        # Sync combo to saved currency
        for i in range(self.currency_combo.count()):
            if self.currency_combo.itemData(i) == code:
                self.currency_combo.setCurrentIndex(i)
                break
        self.currency_rate_spin.setValue(settings_model.get_currency_rate(code))
        self.gold_spin.setValue(settings_model.get_gold_price())

    # ── Handlers ───────────────────────────────────────────────────────────────
    def _on_currency_changed(self, _index: int):
        """When user picks a different currency, load its saved rate."""
        code = self.currency_combo.currentData()
        if not code:
            return
        self._rate_lbl.setText(f"1 {code} = ₹")
        self.currency_rate_spin.setValue(settings_model.get_currency_rate(code))

    def _save_currency_rate(self):
        code = self.currency_combo.currentData()
        rate = self.currency_rate_spin.value()
        settings_model.set_currency(code)
        settings_model.set_currency_rate(code, rate)
        meta = CURRENCIES.get(code, {})
        info_dialog(
            self, "Saved",
            f"Display currency set to {code} — {meta.get('name','')}.\n"
            f"Rate: 1 {code} = ₹{rate:,.4f}"
        )

    def _save_gold_price(self):
        settings_model.set_gold_price(self.gold_spin.value())
        self.gold_last_lbl.setText(f"Last updated: {datetime.now().strftime('%d-%b-%Y %H:%M')}")
        info_dialog(self, "Saved", "Gold price updated.")

    def _backup(self):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(BACKUP_DIR, f"financial_app_{ts}.db")
        shutil.copy2(DB_PATH, dest)
        info_dialog(self, "Backup Complete", f"Database backed up to:\n{dest}")

    def _change_password(self):
        dlg = ChangePasswordDialog(self)
        dlg.exec()

    def _update_questions(self):
        dlg = UpdateQuestionsDialog(self)
        dlg.exec()

    def _save_template(self, filename: str):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Save Template", filename, "CSV Files (*.csv)")
        if not path:
            return
        templates = {
            "fd_template.csv": "bank_name,fd_number,principal,interest_rate,compounding,start_date,maturity_date,maturity_amount,notes\nHDFC Bank,FD-001,100000,7.5,quarterly,2024-01-01,2026-01-01,,\n",
            "bonds_template.csv": "bond_name,issuer,bond_type,face_value,units,purchase_price,coupon_rate,purchase_date,maturity_date,current_price,notes\n7.1% Govt Bond,RBI,government,1000,10,1000,7.1,2023-06-01,2033-06-01,,\n",
            "mf_template.csv": "fund_name,amfi_code,folio_number,units,avg_nav,purchase_value,current_nav,purchase_date,notes\nParag Parikh Flexi Cap,119068,12345678,250.543,45.23,11325,68.15,2021-06-15,\n",
            "stocks_template.csv": "company_name,ticker_symbol,exchange,quantity,avg_buy_price,purchase_value,current_price,purchase_date,demat_account,notes\nReliance Industries,RELIANCE,NSE,10,2340.50,23405,2985.60,2022-01-15,,\n",
            "sgb_template.csv": "series_name,units,issue_price,purchase_date,maturity_date,coupon_rate,notes\nSGB 2021-22 Series VIII,5,4791,2021-11-12,2029-11-12,2.5,\n",
        }
        content = templates.get(filename, "")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        info_dialog(self, "Template Saved", f"Template saved to:\n{path}")


# ── Change Password Dialog ─────────────────────────────────────────────────────
class ChangePasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Change Password")
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.current = QLineEdit()
        self.current.setEchoMode(QLineEdit.EchoMode.Password)
        self.current.setMaxLength(MAX_PASSWORD_LENGTH)
        form.addRow("Current Password:", self.current)

        self.new_pwd = QLineEdit()
        self.new_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pwd.setMaxLength(MAX_PASSWORD_LENGTH)
        form.addRow("New Password:", self.new_pwd)

        self.confirm = QLineEdit()
        self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm.setMaxLength(MAX_PASSWORD_LENGTH)
        form.addRow("Confirm New Password:", self.confirm)

        layout.addLayout(form)

        self.status = QLabel("")
        self.status.setObjectName("errorLabel")
        layout.addWidget(self.status)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Change Password")
        btn_save.setObjectName("primaryButton")
        btn_save.clicked.connect(self._on_save)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

    def _on_save(self):
        if not auth_model.verify_password(self.current.text()):
            self.status.setText("Current password is incorrect.")
            self.status.setStyleSheet("color: #E74C3C;")
            return
        if len(self.new_pwd.text()) < 8:
            self.status.setText("New password must be at least 8 characters.")
            self.status.setStyleSheet("color: #E74C3C;")
            return
        if self.new_pwd.text() != self.confirm.text():
            self.status.setText("Passwords do not match.")
            self.status.setStyleSheet("color: #E74C3C;")
            return
        auth_model.change_password(self.new_pwd.text())
        info_dialog(self, "Password Changed", "Your password has been updated. Please log in again.")
        self.accept()


# ── Update Security Questions Dialog ──────────────────────────────────────────
class UpdateQuestionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update Security Questions")
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)

        lbl = QLabel("Enter your current password to update security questions.")
        lbl.setObjectName("hintLabel")
        layout.addWidget(lbl)

        form = QFormLayout()
        self.current_pwd = QLineEdit()
        self.current_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_pwd.setMaxLength(MAX_PASSWORD_LENGTH)
        form.addRow("Current Password:", self.current_pwd)
        layout.addLayout(form)
        layout.addWidget(separator())

        self.q_combos = []
        self.a_edits = []
        for i in range(3):
            lbl2 = QLabel(f"Question {i + 1}:")
            layout.addWidget(lbl2)
            cb = QComboBox()
            for q in SECURITY_QUESTIONS:
                cb.addItem(q)
            cb.setCurrentIndex(i)
            self.q_combos.append(cb)
            layout.addWidget(cb)

            ae = QLineEdit()
            ae.setPlaceholderText("Answer")
            self.a_edits.append(ae)
            layout.addWidget(ae)

        self.status = QLabel("")
        self.status.setObjectName("errorLabel")
        layout.addWidget(self.status)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Update Questions")
        btn_save.setObjectName("primaryButton")
        btn_save.clicked.connect(self._on_save)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

    def _on_save(self):
        if not auth_model.verify_password(self.current_pwd.text()):
            self.status.setText("Incorrect password.")
            self.status.setStyleSheet("color: #E74C3C;")
            return
        questions = []
        seen = set()
        for i in range(3):
            qtext = self.q_combos[i].currentText()
            ans = self.a_edits[i].text().strip()
            if not ans:
                self.status.setText(f"Answer {i + 1} is required.")
                self.status.setStyleSheet("color: #E74C3C;")
                return
            if qtext in seen:
                self.status.setText("Choose different questions.")
                self.status.setStyleSheet("color: #E74C3C;")
                return
            seen.add(qtext)
            questions.append({"question_text": qtext, "answer": ans})
        auth_model.update_security_questions(questions)
        info_dialog(self, "Updated", "Security questions have been updated.")
        self.accept()


def separator():
    from app.ui.widgets import separator as _sep
    return _sep()

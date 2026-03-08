"""National Pension System (NPS) widget — single-record edit form."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QPushButton,
    QLabel, QLineEdit, QTextEdit, QComboBox, QHBoxLayout,
    QFrame, QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.models import debt as debt_model
from app.ui.widgets import (
    title_label, section_label, separator,
    make_amount_spin, make_date_edit, info_dialog,
)
from app.services.formatters import format_inr, format_date


NPS_PFM_OPTIONS = [
    "HDFC Pension Fund",
    "ICICI Prudential Pension Fund",
    "SBI Pension Fund",
    "UTI Retirement Solutions",
    "LIC Pension Fund",
    "Kotak Pension Fund",
    "Aditya Birla Sun Life Pension Fund",
    "DSP Pension Fund",
    "Max Life Pension Fund",
    "Tata Pension Fund",
    "Other",
]

_INPUT_H = 34   # minimum height for all input controls


def _section_card(title: str):
    """Return (outer QWidget, inner QFormLayout).

    Title label sits above the bordered card frame — matches the settings widget
    pattern that avoids QGroupBox::title subcontrol clipping issues.
    """
    outer = QWidget()
    vbox = QVBoxLayout(outer)
    vbox.setContentsMargins(0, 0, 0, 0)
    vbox.setSpacing(6)

    lbl = QLabel(title)
    lbl.setObjectName("settingsCardTitle")
    vbox.addWidget(lbl)

    card = QFrame()
    card.setObjectName("settingsCard")
    inner_vbox = QVBoxLayout(card)
    inner_vbox.setContentsMargins(18, 14, 18, 14)
    inner_vbox.setSpacing(0)
    vbox.addWidget(card)

    form = QFormLayout()
    form.setSpacing(10)
    inner_vbox.addLayout(form)

    return outer, form


class NPSWidget(QWidget):
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
        layout.setSpacing(16)

        # ── Title + hint ──────────────────────────────────────────────────────
        layout.addWidget(title_label("National Pension System (NPS)"))

        hint = QLabel(
            "NPS is a government-sponsored retirement savings scheme. "
            "Tier I is the mandatory pension account; Tier II is an optional savings account. "
            "Update your corpus from the CRA (NSDL/Karvy) portal periodically."
        )
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addWidget(separator())

        # ── Summary display ───────────────────────────────────────────────────
        self.total_display = QLabel("Total Corpus: ₹0")
        self.total_display.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.total_display.setObjectName("bigValue")
        layout.addWidget(self.total_display)

        tier_row = QHBoxLayout()
        self.tier1_display = QLabel("Tier I: ₹0")
        self.tier1_display.setObjectName("subValue")
        self.tier2_display = QLabel("Tier II: ₹0")
        self.tier2_display.setObjectName("subValue")
        self.alloc_display = QLabel("Allocation: —")
        self.alloc_display.setObjectName("subValue")
        tier_row.addWidget(self.tier1_display)
        tier_row.addWidget(QLabel("  |  "))
        tier_row.addWidget(self.tier2_display)
        tier_row.addWidget(QLabel("  |  "))
        tier_row.addWidget(self.alloc_display)
        tier_row.addStretch()
        layout.addLayout(tier_row)

        layout.addWidget(separator())

        # ── Account info card ─────────────────────────────────────────────────
        acct_outer, acct_form = _section_card("Account Details")
        acct_form.setSpacing(10)

        self.pran_edit = QLineEdit()
        self.pran_edit.setPlaceholderText("e.g. 110012345678 (optional)")
        self.pran_edit.setMinimumHeight(_INPUT_H)
        acct_form.addRow("PRAN Number:", self.pran_edit)

        self.pfm_combo = QComboBox()
        self.pfm_combo.addItems(NPS_PFM_OPTIONS)
        self.pfm_combo.setMinimumHeight(_INPUT_H)
        acct_form.addRow("Pension Fund Manager:", self.pfm_combo)

        self.as_of_date_edit = make_date_edit()
        self.as_of_date_edit.setMinimumHeight(_INPUT_H)
        acct_form.addRow("As of Date:", self.as_of_date_edit)

        layout.addWidget(acct_outer)

        # ── Tier I card ───────────────────────────────────────────────────────
        tier1_outer, tier1_form = _section_card("Tier I  —  Mandatory Pension Account")

        self.tier1_corpus_spin = make_amount_spin()
        self.tier1_corpus_spin.setMinimumHeight(_INPUT_H)
        tier1_form.addRow("Current Corpus (₹):", self.tier1_corpus_spin)

        self.tier1_contrib_spin = make_amount_spin()
        self.tier1_contrib_spin.setMinimumHeight(_INPUT_H)
        tier1_form.addRow("Total Contributions (₹):", self.tier1_contrib_spin)

        layout.addWidget(tier1_outer)

        # ── Tier II card ──────────────────────────────────────────────────────
        tier2_outer, tier2_form = _section_card("Tier II  —  Optional Savings Account")

        self.tier2_corpus_spin = make_amount_spin()
        self.tier2_corpus_spin.setMinimumHeight(_INPUT_H)
        tier2_form.addRow("Current Corpus (₹):", self.tier2_corpus_spin)

        self.tier2_contrib_spin = make_amount_spin()
        self.tier2_contrib_spin.setMinimumHeight(_INPUT_H)
        tier2_form.addRow("Total Contributions (₹):", self.tier2_contrib_spin)

        layout.addWidget(tier2_outer)

        # ── Asset allocation card ─────────────────────────────────────────────
        alloc_outer, alloc_form = _section_card("Asset Allocation  —  Active Choice %")

        def _pct_spin():
            s = make_amount_spin(min_val=0.0, max_val=100.0, prefix="")
            s.setDecimals(1)
            s.setSuffix(" %")
            s.setMinimumHeight(_INPUT_H)
            return s

        self.equity_spin = _pct_spin()
        alloc_form.addRow("Equity (E):", self.equity_spin)

        self.govt_spin = _pct_spin()
        alloc_form.addRow("Govt. Securities (G):", self.govt_spin)

        self.corp_spin = _pct_spin()
        alloc_form.addRow("Corporate Bonds (C):", self.corp_spin)

        layout.addWidget(alloc_outer)

        # ── Notes + Save ──────────────────────────────────────────────────────
        notes_form = QFormLayout()
        notes_form.setSpacing(10)
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(70)
        self.notes_edit.setPlaceholderText("Optional notes")
        notes_form.addRow("Notes:", self.notes_edit)
        layout.addLayout(notes_form)

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
        nps = debt_model.get_nps()
        if nps:
            tier1 = nps.get("tier1_corpus", 0.0)
            tier2 = nps.get("tier2_corpus", 0.0)
            total = tier1 + tier2
            eq = nps.get("equity_pct", 0.0)
            g  = nps.get("govt_pct", 0.0)
            c  = nps.get("corp_pct", 0.0)

            self.total_display.setText(f"Total Corpus: {format_inr(total)}")
            self.tier1_display.setText(f"Tier I: {format_inr(tier1)}")
            self.tier2_display.setText(f"Tier II: {format_inr(tier2)}")
            self.alloc_display.setText(f"E:{eq:.0f}%  G:{g:.0f}%  C:{c:.0f}%")

            self.pran_edit.setText(nps.get("pran_number", ""))
            pfm = nps.get("pfm_name", "")
            idx = self.pfm_combo.findText(pfm)
            if idx >= 0:
                self.pfm_combo.setCurrentIndex(idx)

            self.tier1_corpus_spin.setValue(tier1)
            self.tier1_contrib_spin.setValue(nps.get("tier1_contributions", 0.0))
            self.tier2_corpus_spin.setValue(tier2)
            self.tier2_contrib_spin.setValue(nps.get("tier2_contributions", 0.0))
            self.equity_spin.setValue(eq)
            self.govt_spin.setValue(g)
            self.corp_spin.setValue(c)
            self.notes_edit.setPlainText(nps.get("notes", ""))

            from PyQt6.QtCore import QDate
            d = QDate.fromString(nps["as_of_date"], "yyyy-MM-dd")
            if d.isValid():
                self.as_of_date_edit.setDate(d)

    def _save(self):
        debt_model.save_nps(
            tier1_corpus=self.tier1_corpus_spin.value(),
            as_of_date=self.as_of_date_edit.date().toString("yyyy-MM-dd"),
            pran_number=self.pran_edit.text().strip(),
            pfm_name=self.pfm_combo.currentText(),
            tier1_contributions=self.tier1_contrib_spin.value(),
            tier2_corpus=self.tier2_corpus_spin.value(),
            tier2_contributions=self.tier2_contrib_spin.value(),
            equity_pct=self.equity_spin.value(),
            govt_pct=self.govt_spin.value(),
            corp_pct=self.corp_spin.value(),
            notes=self.notes_edit.toPlainText().strip(),
        )
        self.refresh()
        info_dialog(self, "Saved", "NPS account updated.")

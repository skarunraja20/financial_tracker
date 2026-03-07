"""
Records widget — captures the complete financial life record of a person.

Three tabs:
  1. Investments  — all portfolio assets with holder + nominee details
  2. Protection   — health/term/life insurance, emergency fund, will, etc.
  3. Contacts     — emergency contacts, advocate, CA, doctor, banker, etc.

Top-right: Export to Excel (3-sheet workbook).
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTextEdit,
    QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QTabWidget, QDoubleSpinBox,
    QSizePolicy, QFrame, QMessageBox, QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.models.records import (
    PROTECTION_TYPES, PREMIUM_FREQUENCIES, CONTACT_TYPES,
    get_all_investment_records, upsert_investment_record,
    get_all_protection_records, add_protection_record,
    update_protection_record, delete_protection_record,
    get_all_contact_records, add_contact_record,
    update_contact_record, delete_contact_record,
    export_records_to_excel,
)
from app.ui.widgets import title_label, separator, info_dialog, error_dialog


# ══════════════════════════════════════════════════════════════════════════════
#  Helper — build a read-only, styled table
# ══════════════════════════════════════════════════════════════════════════════
def _make_table(column_headers: list[str]) -> QTableWidget:
    tbl = QTableWidget()
    tbl.setObjectName("dataTable")
    tbl.setColumnCount(len(column_headers))
    tbl.setHorizontalHeaderLabels(column_headers)
    tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    tbl.setAlternatingRowColors(True)
    tbl.verticalHeader().setVisible(False)
    tbl.horizontalHeader().setStretchLastSection(False)
    tbl.setShowGrid(False)
    tbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return tbl


def _cell(text: str,
          align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft) -> QTableWidgetItem:
    item = QTableWidgetItem(text if text else "—")
    item.setTextAlignment(int(align | Qt.AlignmentFlag.AlignVCenter))
    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
    return item


def _btn_cell(table: QTableWidget, row: int, col: int,
              buttons: list[QPushButton]):
    """Place one or more buttons inside a table cell."""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(4, 2, 4, 2)
    layout.setSpacing(6)
    for btn in buttons:
        layout.addWidget(btn)
    layout.addStretch()
    table.setCellWidget(row, col, container)


# ══════════════════════════════════════════════════════════════════════════════
#  Main Records Widget
# ══════════════════════════════════════════════════════════════════════════════
class RecordsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 16)
        root.setSpacing(10)

        # Header row
        hdr = QHBoxLayout()
        hdr.addWidget(title_label("Records"))
        hdr.addStretch()
        export_btn = QPushButton("📥  Export to Excel")
        export_btn.setObjectName("primaryButton")
        export_btn.setMinimumHeight(36)
        export_btn.clicked.connect(self._export_excel)
        hdr.addWidget(export_btn)
        root.addLayout(hdr)
        root.addWidget(separator())

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        root.addWidget(self._tabs)

        self._build_investments_tab()
        self._build_protection_tab()
        self._build_contacts_tab()

    # ─────────────────────────────────────────────────────────────────────────
    #  TAB 1: Investments
    # ─────────────────────────────────────────────────────────────────────────
    def _build_investments_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(8)

        # Info banner
        info = QLabel(
            "💡  Assets are automatically loaded from your portfolio.  "
            "Click  ✏️ Edit  on any row to fill in account/folio numbers, "
            "joint holders and nominee details."
        )
        info.setObjectName("hintLabel")
        info.setWordWrap(True)
        info.setContentsMargins(6, 0, 6, 0)
        layout.addWidget(info)

        # Table: 10 data cols + Notes + Actions = 12 columns
        #   0  Asset Name        5  Nominee 1      10  Notes
        #   1  Asset Class       6  1 %            11  Actions
        #   2  Account/Folio     7  Nominee 2
        #   3  1st Holder        8  2 %
        #   4  2nd Holder        9  Goals Tagged
        self._inv_tbl = _make_table([
            "Asset Name", "Asset Class", "Account / Folio No.",
            "1st Holder", "2nd Holder",
            "Nominee 1", "1 %",
            "Nominee 2", "2 %",
            "Goals Tagged", "Notes", "Actions",
        ])
        hdr = self._inv_tbl.horizontalHeader()
        hdr.setSectionResizeMode(0,  QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(1,  QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(2,  QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(3,  QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(4,  QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(5,  QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(6,  QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(7,  QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(8,  QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(9,  QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(10, QHeaderView.ResizeMode.Interactive)  # Notes — user-resizable
        hdr.setSectionResizeMode(11, QHeaderView.ResizeMode.Fixed)         # Actions fixed
        self._inv_tbl.setColumnWidth(6,  48)
        self._inv_tbl.setColumnWidth(8,  48)
        self._inv_tbl.setColumnWidth(10, 220)   # ~35 chars visible at 9pt
        self._inv_tbl.setColumnWidth(11, 90)
        layout.addWidget(self._inv_tbl)

        self._tabs.addTab(page, "📋  Investments")

    def _populate_investments(self):
        records = get_all_investment_records()
        tbl = self._inv_tbl
        tbl.setRowCount(len(records))
        tbl.setUpdatesEnabled(False)
        try:
            for row, r in enumerate(records):
                tbl.setItem(row, 0,  _cell(r["asset_name"]))
                tbl.setItem(row, 1,  _cell(r["asset_class"]))
                tbl.setItem(row, 2,  _cell(r["account_folio_number"]))
                tbl.setItem(row, 3,  _cell(r["first_holder"]))
                tbl.setItem(row, 4,  _cell(r["second_holder"]))
                tbl.setItem(row, 5,  _cell(r["nominee_1_name"]))
                pct1 = f"{int(r['nominee_1_pct'])}%" if r["nominee_1_pct"] else "—"
                tbl.setItem(row, 6,  _cell(pct1,  Qt.AlignmentFlag.AlignCenter))
                tbl.setItem(row, 7,  _cell(r["nominee_2_name"]))
                pct2 = f"{int(r['nominee_2_pct'])}%" if r["nominee_2_pct"] else "—"
                tbl.setItem(row, 8,  _cell(pct2,  Qt.AlignmentFlag.AlignCenter))
                tbl.setItem(row, 9,  _cell(r["goals"]))

                # Notes — truncate long text for the cell display
                notes_txt = r.get("notes") or ""
                notes_display = (notes_txt[:77] + "…") if len(notes_txt) > 80 else notes_txt
                notes_item = _cell(notes_display)
                notes_item.setToolTip(notes_txt)   # full text on hover
                tbl.setItem(row, 10, notes_item)

                edit_btn = QPushButton("✏️ Edit")
                edit_btn.setObjectName("secondaryButton")
                edit_btn.setFixedHeight(26)
                edit_btn.clicked.connect(lambda _, d=r: self._edit_investment(d))
                _btn_cell(tbl, row, 11, [edit_btn])   # Actions now at col 11

                tbl.setRowHeight(row, 34)
        finally:
            tbl.setUpdatesEnabled(True)

        # Reasonable initial widths
        tbl.setColumnWidth(0, 180)
        tbl.setColumnWidth(1, 155)
        tbl.setColumnWidth(2, 145)
        tbl.setColumnWidth(3, 120)
        tbl.setColumnWidth(4, 120)
        tbl.setColumnWidth(5, 120)
        tbl.setColumnWidth(7, 120)
        tbl.setColumnWidth(9, 120)   # Goals

    def _edit_investment(self, data: dict):
        dlg = InvestmentEditDialog(data, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            upsert_investment_record(
                data["asset_type"], data["asset_id"], **dlg.result_data
            )
            self._populate_investments()

    # ─────────────────────────────────────────────────────────────────────────
    #  TAB 2: Protection & Insurance
    # ─────────────────────────────────────────────────────────────────────────
    def _build_protection_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.addStretch()
        add_btn = QPushButton("＋  Add Record")
        add_btn.setObjectName("primaryButton")
        add_btn.setMinimumHeight(34)
        add_btn.clicked.connect(self._add_protection)
        toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        # Table (10 data cols + 1 actions = 11)
        self._prot_tbl = _make_table([
            "Type", "Provider", "Policy / Account No.",
            "Coverage (₹)", "Premium (₹)", "Frequency",
            "Start Date", "End / Renewal", "Nominee", "Notes", "Actions",
        ])
        hdr = self._prot_tbl.horizontalHeader()
        for col in range(10):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(10, QHeaderView.ResizeMode.Fixed)
        self._prot_tbl.setColumnWidth(10, 170)
        layout.addWidget(self._prot_tbl)

        self._tabs.addTab(page, "🛡️  Protection & Insurance")

    def _populate_protection(self):
        records = get_all_protection_records()
        tbl = self._prot_tbl
        tbl.setRowCount(len(records))
        tbl.setUpdatesEnabled(False)
        try:
            for row, r in enumerate(records):
                tbl.setItem(row, 0,  _cell(PROTECTION_TYPES.get(r["record_type"], r["record_type"])))
                tbl.setItem(row, 1,  _cell(r.get("provider") or ""))
                tbl.setItem(row, 2,  _cell(r.get("policy_number") or ""))
                cov = f"₹{r['coverage_amount']:,.0f}" if r.get("coverage_amount") else "—"
                tbl.setItem(row, 3,  _cell(cov, Qt.AlignmentFlag.AlignRight))
                pre = f"₹{r['premium_amount']:,.0f}" if r.get("premium_amount") else "—"
                tbl.setItem(row, 4,  _cell(pre, Qt.AlignmentFlag.AlignRight))
                tbl.setItem(row, 5,  _cell(PREMIUM_FREQUENCIES.get(r.get("premium_frequency", ""), "")))
                tbl.setItem(row, 6,  _cell(r.get("start_date") or ""))
                tbl.setItem(row, 7,  _cell(r.get("end_date") or ""))
                tbl.setItem(row, 8,  _cell(r.get("nominee") or ""))
                tbl.setItem(row, 9,  _cell(r.get("notes") or ""))

                edit_btn = QPushButton("✏️  Edit")
                edit_btn.setObjectName("secondaryButton")
                edit_btn.setMinimumWidth(72)
                edit_btn.setFixedHeight(26)
                edit_btn.clicked.connect(lambda _, d=dict(r): self._edit_protection(d))

                del_btn = QPushButton("🗑  Del")
                del_btn.setObjectName("dangerButton")
                del_btn.setMinimumWidth(66)
                del_btn.setFixedHeight(26)
                del_btn.clicked.connect(lambda _, rid=r["id"]: self._delete_protection(rid))

                _btn_cell(tbl, row, 10, [edit_btn, del_btn])
                tbl.setRowHeight(row, 34)
        finally:
            tbl.setUpdatesEnabled(True)

        tbl.setColumnWidth(0,  145)
        tbl.setColumnWidth(1,  155)
        tbl.setColumnWidth(2,  150)
        tbl.setColumnWidth(3,  110)
        tbl.setColumnWidth(4,  100)
        tbl.setColumnWidth(5,   95)
        tbl.setColumnWidth(6,   90)
        tbl.setColumnWidth(7,  120)
        tbl.setColumnWidth(8,  120)
        tbl.setColumnWidth(9,  160)

    def _add_protection(self):
        dlg = ProtectionDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            add_protection_record(**dlg.result_data)
            self._populate_protection()

    def _edit_protection(self, data: dict):
        dlg = ProtectionDialog(data=data, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            update_protection_record(data["id"], **dlg.result_data)
            self._populate_protection()

    def _delete_protection(self, rec_id: int):
        msg = QMessageBox(self)
        msg.setWindowTitle("Delete Record")
        msg.setText("Delete this protection record?")
        msg.setInformativeText("The record will be archived and won't appear in the list.")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            delete_protection_record(rec_id)
            self._populate_protection()

    # ─────────────────────────────────────────────────────────────────────────
    #  TAB 3: Contacts
    # ─────────────────────────────────────────────────────────────────────────
    def _build_contacts_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.addStretch()
        add_btn = QPushButton("＋  Add Contact")
        add_btn.setObjectName("primaryButton")
        add_btn.setMinimumHeight(34)
        add_btn.clicked.connect(self._add_contact)
        toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        # Table (7 data cols + 1 actions = 8)
        self._cont_tbl = _make_table([
            "Type", "Name", "Relationship",
            "Phone", "Email", "Address", "Notes", "Actions",
        ])
        hdr = self._cont_tbl.horizontalHeader()
        for col in range(7):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self._cont_tbl.setColumnWidth(7, 170)
        layout.addWidget(self._cont_tbl)

        self._tabs.addTab(page, "📞  Contacts")

    def _populate_contacts(self):
        records = get_all_contact_records()
        tbl = self._cont_tbl
        tbl.setRowCount(len(records))
        tbl.setUpdatesEnabled(False)
        try:
            for row, r in enumerate(records):
                tbl.setItem(row, 0, _cell(CONTACT_TYPES.get(r["contact_type"], r["contact_type"])))
                tbl.setItem(row, 1, _cell(r.get("name") or ""))
                tbl.setItem(row, 2, _cell(r.get("relationship") or ""))
                tbl.setItem(row, 3, _cell(r.get("phone") or ""))
                tbl.setItem(row, 4, _cell(r.get("email") or ""))
                tbl.setItem(row, 5, _cell(r.get("address") or ""))
                tbl.setItem(row, 6, _cell(r.get("notes") or ""))

                edit_btn = QPushButton("✏️  Edit")
                edit_btn.setObjectName("secondaryButton")
                edit_btn.setMinimumWidth(72)
                edit_btn.setFixedHeight(26)
                edit_btn.clicked.connect(lambda _, d=dict(r): self._edit_contact(d))

                del_btn = QPushButton("🗑  Del")
                del_btn.setObjectName("dangerButton")
                del_btn.setMinimumWidth(66)
                del_btn.setFixedHeight(26)
                del_btn.clicked.connect(lambda _, rid=r["id"]: self._delete_contact(rid))

                _btn_cell(tbl, row, 7, [edit_btn, del_btn])
                tbl.setRowHeight(row, 34)
        finally:
            tbl.setUpdatesEnabled(True)

        tbl.setColumnWidth(0, 140)
        tbl.setColumnWidth(1, 160)
        tbl.setColumnWidth(2, 120)
        tbl.setColumnWidth(3, 120)
        tbl.setColumnWidth(4, 175)
        tbl.setColumnWidth(5, 175)
        tbl.setColumnWidth(6, 180)

    def _add_contact(self):
        dlg = ContactDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            add_contact_record(**dlg.result_data)
            self._populate_contacts()

    def _edit_contact(self, data: dict):
        dlg = ContactDialog(data=data, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            update_contact_record(data["id"], **dlg.result_data)
            self._populate_contacts()

    def _delete_contact(self, rec_id: int):
        msg = QMessageBox(self)
        msg.setWindowTitle("Delete Contact")
        msg.setText("Delete this contact record? This cannot be undone.")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            delete_contact_record(rec_id)
            self._populate_contacts()

    # ─────────────────────────────────────────────────────────────────────────
    #  Excel export
    # ─────────────────────────────────────────────────────────────────────────
    def _export_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Records to Excel",
            "Financial_Records.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not path:
            return
        try:
            export_records_to_excel(path)
            info_dialog(self, "Export Successful",
                        f"Records exported to:\n{path}\n\n"
                        "The workbook contains 3 sheets:\n"
                        "  • Investments\n"
                        "  • Protection & Insurance\n"
                        "  • Contacts")
        except Exception as exc:
            error_dialog(self, "Export Failed", str(exc))

    # ─────────────────────────────────────────────────────────────────────────
    #  Refresh (called by main_window when tab is selected)
    # ─────────────────────────────────────────────────────────────────────────
    def refresh(self):
        self._populate_investments()
        self._populate_protection()
        self._populate_contacts()


# ══════════════════════════════════════════════════════════════════════════════
#  Dialog 1 — Edit Investment Record
# ══════════════════════════════════════════════════════════════════════════════
class InvestmentEditDialog(QDialog):
    """Fill in / edit holder and nominee details for a single investment."""

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self._data = data
        self.result_data: dict = {}
        self.setWindowTitle("Edit Investment Record")
        self.setMinimumWidth(500)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)

        # ── Asset header card ─────────────────────────────────────────────────
        asset_frame = QFrame()
        asset_frame.setObjectName("settingsCard")
        frame_lay = QVBoxLayout(asset_frame)
        frame_lay.setContentsMargins(14, 10, 14, 10)
        frame_lay.setSpacing(2)
        name_lbl = QLabel(self._data["asset_name"])
        name_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        name_lbl.setObjectName("sectionLabel")
        cls_lbl = QLabel(self._data["asset_class"])
        cls_lbl.setObjectName("hintLabel")
        frame_lay.addWidget(name_lbl)
        frame_lay.addWidget(cls_lbl)
        root.addWidget(asset_frame)

        # ── Section 1: Account & Holders ──────────────────────────────────────
        form1 = QFormLayout()
        form1.setSpacing(10)
        form1.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._acct = QLineEdit(self._data.get("account_folio_number") or "")
        self._acct.setPlaceholderText("e.g. 12345678 / FOLIO-001")
        form1.addRow("Account / Folio No.:", self._acct)

        self._h1 = QLineEdit(self._data.get("first_holder") or "")
        self._h1.setPlaceholderText("Primary account holder name")
        form1.addRow("1st Holder:", self._h1)

        self._h2 = QLineEdit(self._data.get("second_holder") or "")
        self._h2.setPlaceholderText("Joint holder name (if any)")
        form1.addRow("2nd Holder:", self._h2)

        root.addLayout(form1)
        root.addWidget(separator())

        # ── Section 2: Nominees ───────────────────────────────────────────────
        form2 = QFormLayout()
        form2.setSpacing(10)
        form2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._n1name = QLineEdit(self._data.get("nominee_1_name") or "")
        self._n1name.setPlaceholderText("Full name")
        form2.addRow("Nominee 1:", self._n1name)

        self._n1pct = QDoubleSpinBox()
        self._n1pct.setRange(0, 100)
        self._n1pct.setDecimals(0)
        self._n1pct.setSuffix("  %")
        self._n1pct.setValue(self._data.get("nominee_1_pct") or 0)
        form2.addRow("Nominee 1 Share:", self._n1pct)

        self._n2name = QLineEdit(self._data.get("nominee_2_name") or "")
        self._n2name.setPlaceholderText("Full name (optional)")
        form2.addRow("Nominee 2:", self._n2name)

        self._n2pct = QDoubleSpinBox()
        self._n2pct.setRange(0, 100)
        self._n2pct.setDecimals(0)
        self._n2pct.setSuffix("  %")
        self._n2pct.setValue(self._data.get("nominee_2_pct") or 0)
        form2.addRow("Nominee 2 Share:", self._n2pct)

        root.addLayout(form2)

        # Percentage hint (live total below nominee rows)
        self._pct_hint = QLabel("")
        self._pct_hint.setObjectName("hintLabel")
        self._n1pct.valueChanged.connect(self._update_pct_hint)
        self._n2pct.valueChanged.connect(self._update_pct_hint)
        self._update_pct_hint()
        root.addWidget(self._pct_hint)

        root.addWidget(separator())

        # ── Notes ─────────────────────────────────────────────────────────────
        notes_lbl = QLabel("Notes")
        notes_lbl.setObjectName("settingsCardTitle")
        root.addWidget(notes_lbl)

        self._notes = QTextEdit()
        self._notes.setPlaceholderText(
            "Any additional notes (e.g. maturity instructions, physical document location…)"
        )
        self._notes.setMaximumHeight(80)
        self._notes.setPlainText(self._data.get("notes") or "")
        root.addWidget(self._notes)

        self._notes_counter = QLabel("0 / 500")
        self._notes_counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        root.addWidget(self._notes_counter)
        _attach_char_counter(self._notes, self._notes_counter)

        # ── Buttons ───────────────────────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryButton")
        root.addWidget(btns)

    def _update_pct_hint(self):
        total = self._n1pct.value() + self._n2pct.value()
        if total > 100:
            self._pct_hint.setText(f"⚠️  Total nominee share = {int(total)}% (exceeds 100%)")
            self._pct_hint.setStyleSheet("color: #f43f5e;")
        elif total == 100:
            self._pct_hint.setText(f"✅  Total nominee share = {int(total)}%")
            self._pct_hint.setStyleSheet("color: #10b981;")
        elif total > 0:
            self._pct_hint.setText(f"ℹ️  Total nominee share = {int(total)}%  (remaining {int(100 - total)}% unallocated)")
            self._pct_hint.setStyleSheet("color: #64748b;")
        else:
            self._pct_hint.setText("")

    def _on_save(self):
        n1pct = self._n1pct.value()
        n2pct = self._n2pct.value()
        if n1pct + n2pct > 100:
            QMessageBox.warning(self, "Validation Error",
                                "Combined nominee share cannot exceed 100%.")
            return
        # If a nominee percentage is given, a name is required
        if n1pct > 0 and not self._n1name.text().strip():
            QMessageBox.warning(self, "Validation Error",
                                "Please enter a name for Nominee 1.")
            return
        if n2pct > 0 and not self._n2name.text().strip():
            QMessageBox.warning(self, "Validation Error",
                                "Please enter a name for Nominee 2.")
            return

        self.result_data = {
            "account_folio_number": self._acct.text().strip(),
            "first_holder":         self._h1.text().strip(),
            "second_holder":        self._h2.text().strip(),
            "nominee_1_name":       self._n1name.text().strip(),
            "nominee_1_pct":        n1pct,
            "nominee_2_name":       self._n2name.text().strip(),
            "nominee_2_pct":        n2pct,
            "notes":                self._notes.toPlainText().strip(),
        }
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
#  Dialog 2 — Add / Edit Protection Record
# ══════════════════════════════════════════════════════════════════════════════
class ProtectionDialog(QDialog):
    def __init__(self, data: dict | None = None, parent=None):
        super().__init__(parent)
        self._data = data or {}
        self.result_data: dict = {}
        self.setWindowTitle("Edit Protection Record" if data else "Add Protection Record")
        self.setMinimumWidth(480)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Type
        self._type_cb = QComboBox()
        for key, label in PROTECTION_TYPES.items():
            self._type_cb.addItem(label, key)
        current_type = self._data.get("record_type", "health_insurance")
        idx = list(PROTECTION_TYPES.keys()).index(current_type) \
              if current_type in PROTECTION_TYPES else 0
        self._type_cb.setCurrentIndex(idx)
        form.addRow("Type:", self._type_cb)

        self._provider = QLineEdit(self._data.get("provider") or "")
        self._provider.setPlaceholderText("e.g. LIC, HDFC Ergo, SBI, Max Life…")
        form.addRow("Provider / Institution:", self._provider)

        self._policy_no = QLineEdit(self._data.get("policy_number") or "")
        self._policy_no.setPlaceholderText("Policy / account number")
        form.addRow("Policy / Account No.:", self._policy_no)

        root.addWidget(separator())

        # Amounts
        self._coverage = _make_amount_field(
            self._data.get("coverage_amount"), "e.g. 5000000"
        )
        form.addRow("Coverage Amount (₹):", self._coverage)

        self._premium = _make_amount_field(
            self._data.get("premium_amount"), "e.g. 12000"
        )
        form.addRow("Premium Amount (₹):", self._premium)

        self._freq_cb = QComboBox()
        for key, label in PREMIUM_FREQUENCIES.items():
            self._freq_cb.addItem(label, key)
        current_freq = self._data.get("premium_frequency", "annual")
        fidx = list(PREMIUM_FREQUENCIES.keys()).index(current_freq) \
               if current_freq in PREMIUM_FREQUENCIES else 3  # annual
        self._freq_cb.setCurrentIndex(fidx)
        form.addRow("Premium Frequency:", self._freq_cb)

        root.addWidget(separator())

        # Dates
        self._start = QLineEdit(self._data.get("start_date") or "")
        self._start.setPlaceholderText("YYYY-MM-DD")
        form.addRow("Start Date:", self._start)

        self._end = QLineEdit(self._data.get("end_date") or "")
        self._end.setPlaceholderText("YYYY-MM-DD  (renewal / expiry)")
        form.addRow("End / Renewal Date:", self._end)

        # Nominee
        self._nominee = QLineEdit(self._data.get("nominee") or "")
        self._nominee.setPlaceholderText("Nominee name")
        form.addRow("Nominee:", self._nominee)

        root.addLayout(form)

        # Notes
        notes_lbl = QLabel("Notes")
        notes_lbl.setObjectName("settingsCardTitle")
        root.addWidget(notes_lbl)
        self._notes = QTextEdit()
        self._notes.setMaximumHeight(80)
        self._notes.setPlainText(self._data.get("notes") or "")
        self._notes.setPlaceholderText(
            "e.g. Claim process, agent contact, document location…"
        )
        root.addWidget(self._notes)

        # 500-char counter below the notes box
        self._notes_counter = QLabel("0 / 500")
        self._notes_counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        root.addWidget(self._notes_counter)
        _attach_char_counter(self._notes, self._notes_counter)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryButton")
        root.addWidget(btns)

    def _on_save(self):
        self.result_data = {
            "record_type":      self._type_cb.currentData(),
            "provider":         self._provider.text().strip(),
            "policy_number":    self._policy_no.text().strip(),
            "coverage_amount":  _parse_amount(self._coverage.text()),
            "premium_amount":   _parse_amount(self._premium.text()),
            "premium_frequency": self._freq_cb.currentData(),
            "start_date":       self._start.text().strip(),
            "end_date":         self._end.text().strip(),
            "nominee":          self._nominee.text().strip(),
            "notes":            self._notes.toPlainText().strip(),
        }
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
#  Dialog 3 — Add / Edit Contact
# ══════════════════════════════════════════════════════════════════════════════
class ContactDialog(QDialog):
    def __init__(self, data: dict | None = None, parent=None):
        super().__init__(parent)
        self._data = data or {}
        self.result_data: dict = {}
        self.setWindowTitle("Edit Contact" if data else "Add Contact")
        self.setMinimumWidth(460)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Type
        self._type_cb = QComboBox()
        for key, label in CONTACT_TYPES.items():
            self._type_cb.addItem(label, key)
        current_type = self._data.get("contact_type", "emergency")
        tidx = list(CONTACT_TYPES.keys()).index(current_type) \
               if current_type in CONTACT_TYPES else 0
        self._type_cb.setCurrentIndex(tidx)
        form.addRow("Contact Type:", self._type_cb)

        self._name = QLineEdit(self._data.get("name") or "")
        self._name.setPlaceholderText("Full name")
        form.addRow("Name:*", self._name)

        self._rel = QLineEdit(self._data.get("relationship") or "")
        self._rel.setPlaceholderText("e.g. Spouse, Son, Colleague, Firm name…")
        form.addRow("Relationship:", self._rel)

        root.addWidget(separator())

        self._phone = QLineEdit(self._data.get("phone") or "")
        self._phone.setPlaceholderText("+91 98xxx xxxxx")
        form.addRow("Phone:", self._phone)

        self._email = QLineEdit(self._data.get("email") or "")
        self._email.setPlaceholderText("email@example.com")
        form.addRow("Email:", self._email)

        root.addLayout(form)

        # Address
        addr_lbl = QLabel("Address")
        addr_lbl.setObjectName("settingsCardTitle")
        root.addWidget(addr_lbl)
        self._address = QTextEdit()
        self._address.setMaximumHeight(70)
        self._address.setPlainText(self._data.get("address") or "")
        self._address.setPlaceholderText("Office / home address")
        root.addWidget(self._address)

        # Notes
        notes_lbl = QLabel("Notes")
        notes_lbl.setObjectName("settingsCardTitle")
        root.addWidget(notes_lbl)
        self._notes = QTextEdit()
        self._notes.setMaximumHeight(70)
        self._notes.setPlainText(self._data.get("notes") or "")
        self._notes.setPlaceholderText(
            "e.g. available hours, specialisation, Bar Council No., ICAI membership…"
        )
        root.addWidget(self._notes)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryButton")
        root.addWidget(btns)

    def _on_save(self):
        if not self._name.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required.")
            return
        self.result_data = {
            "contact_type": self._type_cb.currentData(),
            "name":         self._name.text().strip(),
            "relationship": self._rel.text().strip(),
            "phone":        self._phone.text().strip(),
            "email":        self._email.text().strip(),
            "address":      self._address.toPlainText().strip(),
            "notes":        self._notes.toPlainText().strip(),
        }
        self.accept()


# ── Small helpers ──────────────────────────────────────────────────────────────

_NOTES_MAX = 500  # character limit for every notes field


def _attach_char_counter(editor: QTextEdit, counter_lbl: QLabel) -> None:
    """
    Enforce a 500-character limit on *editor* and keep *counter_lbl* updated.
    Counter turns amber at 85 % and red at 100 %.
    """
    def _on_change():
        text = editor.toPlainText()
        if len(text) > _NOTES_MAX:
            editor.blockSignals(True)
            cursor = editor.textCursor()
            pos = min(cursor.position(), _NOTES_MAX)
            editor.setPlainText(text[:_NOTES_MAX])
            cursor.setPosition(pos)
            editor.setTextCursor(cursor)
            editor.blockSignals(False)
            text = editor.toPlainText()
        count = len(text)
        counter_lbl.setText(f"{count} / {_NOTES_MAX}")
        if count >= _NOTES_MAX:
            counter_lbl.setStyleSheet("color: #f43f5e; font-size: 8pt;")
        elif count >= int(_NOTES_MAX * 0.85):
            counter_lbl.setStyleSheet("color: #f59e0b; font-size: 8pt;")
        else:
            counter_lbl.setStyleSheet("color: #475569; font-size: 8pt;")

    editor.textChanged.connect(_on_change)
    _on_change()   # initialise label immediately


def _make_amount_field(value, placeholder: str = "") -> QLineEdit:
    le = QLineEdit()
    le.setPlaceholderText(placeholder)
    if value is not None:
        le.setText(str(int(value)) if float(value) == int(float(value)) else str(value))
    return le


def _parse_amount(text: str):
    text = text.strip().replace(",", "")
    try:
        return float(text) if text else None
    except ValueError:
        return None

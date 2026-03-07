"""First-run setup screen: create master password and 3 security questions."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QLinearGradient, QColor, QBrush

from app.core.constants import SECURITY_QUESTIONS, MAX_PASSWORD_LENGTH
from app.core import security as sec
from app.models import auth as auth_model
from app.ui.widgets import separator


# ── Local label / input helpers (mirror login screen styling exactly) ─────────

def _section_lbl(text: str) -> QLabel:
    """Teal uppercase section header — matches the login-screen section style."""
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    lbl.setStyleSheet(
        "color: #14b8a6; background: transparent; letter-spacing: 0.6px;"
    )
    return lbl


def _field_lbl(text: str) -> QLabel:
    """Muted slate field label — same as login screen."""
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", 9))
    lbl.setStyleSheet("color: #64748b; background: transparent;")
    return lbl


def _input_field(placeholder: str,
                 password: bool = False,
                 max_len: int = 0) -> QLineEdit:
    """Standard 46-px tall text input — same height as login's password field."""
    le = QLineEdit()
    le.setPlaceholderText(placeholder)
    le.setMinimumHeight(46)
    le.setFont(QFont("Segoe UI", 10))
    if password:
        le.setEchoMode(QLineEdit.EchoMode.Password)
    if max_len:
        le.setMaxLength(max_len)
    return le


def _question_combo() -> QComboBox:
    """46-px tall combo box for security questions."""
    cb = QComboBox()
    cb.setMinimumHeight(46)
    cb.setFont(QFont("Segoe UI", 10))
    cb.setMaxVisibleItems(10)
    # Let the popup be as wide as its content
    cb.setSizeAdjustPolicy(
        QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
    )
    return cb


# ══════════════════════════════════════════════════════════════════════════════
class SetupScreen(QWidget):
    """Shown on first launch to create master password and security questions."""

    setup_complete = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("setupScreen")
        self._build_ui()

    # ── Painted background — identical deep-navy mesh gradient to login ───────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.00, QColor("#0c0e32"))
        grad.setColorAt(0.30, QColor("#0a1545"))
        grad.setColorAt(0.65, QColor("#0d0e2e"))
        grad.setColorAt(1.00, QColor("#071a40"))
        painter.fillRect(self.rect(), QBrush(grad))
        painter.end()

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Outer layout holds a full-screen scroll area so the card is never
        # clipped on small / low-resolution displays.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Scope to QScrollArea only — prevents cascade to child widgets
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        outer.addWidget(scroll)

        # Inner widget: vertically centres the card
        inner = QWidget()
        inner.setObjectName("setupScrollInner")
        # Scoped selector — only targets this widget, NOT its children (prevents
        # "background: transparent" from cascading to the button inside authCard)
        inner.setStyleSheet("QWidget#setupScrollInner { background: transparent; }")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner_layout.setContentsMargins(20, 32, 20, 32)
        scroll.setWidget(inner)

        # ── Auth card (glassmorphism — same objectName as login) ──────────────
        card = QFrame()
        card.setObjectName("authCard")
        card.setFixedWidth(580)      # wider than login (500) to fit question text

        layout = QVBoxLayout(card)
        layout.setSpacing(0)
        layout.setContentsMargins(48, 40, 48, 44)

        # ── Header ────────────────────────────────────────────────────────────
        icon_lbl = QLabel("💼")
        icon_lbl.setFont(QFont("Segoe UI", 26))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setFixedHeight(56)
        layout.addWidget(icon_lbl)

        layout.addSpacing(6)

        title = QLabel("Create Your Account")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #f1f5f9; background: transparent;")
        layout.addWidget(title)

        layout.addSpacing(6)

        sub = QLabel("Set a master password and choose 3 security questions")
        sub.setFont(QFont("Segoe UI", 10))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #475569; background: transparent;")
        layout.addWidget(sub)

        layout.addSpacing(28)
        layout.addWidget(separator())
        layout.addSpacing(22)

        # ── Section 1: Master Password ────────────────────────────────────────
        layout.addWidget(_section_lbl("MASTER PASSWORD"))
        layout.addSpacing(12)

        layout.addWidget(_field_lbl("Password  (min 8 characters, max 64)"))
        layout.addSpacing(5)
        self.pwd_edit = _input_field(
            "Enter your master password",
            password=True,
            max_len=MAX_PASSWORD_LENGTH,
        )
        self.pwd_edit.returnPressed.connect(self._on_create)
        layout.addWidget(self.pwd_edit)

        layout.addSpacing(14)

        layout.addWidget(_field_lbl("Confirm Password"))
        layout.addSpacing(5)
        self.pwd_confirm = _input_field(
            "Re-enter your password",
            password=True,
            max_len=MAX_PASSWORD_LENGTH,
        )
        self.pwd_confirm.returnPressed.connect(self._on_create)
        layout.addWidget(self.pwd_confirm)

        layout.addSpacing(26)
        layout.addWidget(separator())
        layout.addSpacing(22)

        # ── Section 2: Security Questions ─────────────────────────────────────
        layout.addWidget(_section_lbl("SECURITY QUESTIONS  —  used for password reset"))
        layout.addSpacing(6)

        hint = QLabel(
            "Pick 3 different questions. Answers are case-insensitive and saved securely."
        )
        hint.setFont(QFont("Segoe UI", 9))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #475569; background: transparent;")
        layout.addWidget(hint)

        self.q_combos: list[QComboBox] = []
        self.a_edits:  list[QLineEdit] = []

        for i in range(3):
            layout.addSpacing(18)

            # Thin divider between question blocks (after the first)
            if i > 0:
                div = QFrame()
                div.setFrameShape(QFrame.Shape.HLine)
                div.setStyleSheet("color: #1e3a5f; background: #1e3a5f;")
                div.setFixedHeight(1)
                layout.addWidget(div)
                layout.addSpacing(14)

            layout.addWidget(_field_lbl(f"Question {i + 1}"))
            layout.addSpacing(5)

            cb = _question_combo()
            for idx, q in enumerate(SECURITY_QUESTIONS):
                cb.addItem(q, idx)
            cb.setCurrentIndex(i)          # pre-select a different Q for each
            self.q_combos.append(cb)
            layout.addWidget(cb)

            layout.addSpacing(12)

            layout.addWidget(_field_lbl(f"Answer {i + 1}  (case-insensitive)"))
            layout.addSpacing(5)

            ae = _input_field("Type your answer…")
            self.a_edits.append(ae)
            layout.addWidget(ae)

        layout.addSpacing(28)
        layout.addWidget(separator())
        layout.addSpacing(20)

        # ── Create Account button ─────────────────────────────────────────────
        self.btn_create = QPushButton("Create Account")
        self.btn_create.setObjectName("primaryButton")
        self.btn_create.setMinimumHeight(48)
        self.btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_create.clicked.connect(self._on_create)
        layout.addWidget(self.btn_create)

        layout.addSpacing(10)

        # Status / error message
        self.status_label = QLabel("")
        self.status_label.setObjectName("errorLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setMinimumHeight(20)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        inner_layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    # ── Validation & persistence ───────────────────────────────────────────────
    def _on_create(self):
        pwd     = self.pwd_edit.text()
        confirm = self.pwd_confirm.text()

        if len(pwd) < 8:
            self._error("Password must be at least 8 characters.")
            return
        if pwd != confirm:
            self._error("Passwords do not match. Please re-enter.")
            return

        questions = []
        seen_q: set[str] = set()
        for i in range(3):
            q_text = self.q_combos[i].currentText()
            answer = self.a_edits[i].text().strip()
            if not answer:
                self._error(f"Answer {i + 1} cannot be empty.")
                return
            if q_text in seen_q:
                self._error(
                    f"Question {i + 1} is already used. "
                    "Please choose 3 different questions."
                )
                return
            seen_q.add(q_text)
            questions.append({"question_text": q_text, "answer": answer})

        self.btn_create.setEnabled(False)
        self.btn_create.setText("Setting up…")
        self.status_label.setText("")
        try:
            salt = sec.generate_salt()
            auth_model.setup_password(pwd, salt, questions)
            self.setup_complete.emit()
        except Exception as e:
            self._error(f"Setup failed: {e}")
            self.btn_create.setEnabled(True)
            self.btn_create.setText("Create Account")

    def _error(self, msg: str):
        self.status_label.setText(msg)
        self.status_label.setStyleSheet("color: #f43f5e; background: transparent;")

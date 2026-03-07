"""Login screen — 2025-style gradient background, glassmorphism card."""

import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPainter, QLinearGradient, QColor, QBrush

from app.core.constants import MAX_PASSWORD_LENGTH, MAX_LOGIN_ATTEMPTS, LOCKOUT_SECONDS
from app.core import security as sec
from app.core.session import session
from app.models import auth as auth_model
from app.ui.widgets import separator


class LoginScreen(QWidget):
    login_success   = pyqtSignal()
    forgot_password = pyqtSignal()
    # Thread-safe: emitted from worker thread, connected to main-thread slots
    _auth_ok   = pyqtSignal(bytes)
    _auth_fail = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("loginScreen")
        self._auth_ok.connect(self._on_success)
        self._auth_fail.connect(self._on_failure)
        self._build_ui()

    # ── Painted gradient background (mesh gradient) ───────────────────────────
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
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.setContentsMargins(20, 20, 20, 20)

        # ── Card (glassmorphism-style) ─────────────────────────────────────────
        card = QFrame()
        card.setObjectName("authCard")
        card.setFixedWidth(420)

        layout = QVBoxLayout(card)
        layout.setSpacing(0)
        layout.setContentsMargins(44, 40, 44, 44)

        # App icon
        icon_lbl = QLabel("💼")
        icon_lbl.setFont(QFont("Segoe UI", 26))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setFixedHeight(56)
        layout.addWidget(icon_lbl)

        layout.addSpacing(6)

        # "Welcome Back" headline
        title = QLabel("Welcome Back")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #f1f5f9; background: transparent;")
        layout.addWidget(title)

        layout.addSpacing(6)

        # Subtitle
        sub = QLabel("Sign in to your financial dashboard")
        sub.setFont(QFont("Segoe UI", 10))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #475569; background: transparent;")
        layout.addWidget(sub)

        layout.addSpacing(28)
        layout.addWidget(separator())
        layout.addSpacing(24)

        # Row: "Password" label  ·  "Forgot password?" link
        pwd_row = QHBoxLayout()
        pwd_lbl = QLabel("Password")
        pwd_lbl.setFont(QFont("Segoe UI", 9))
        pwd_lbl.setStyleSheet("color: #64748b; background: transparent;")
        pwd_row.addWidget(pwd_lbl)
        pwd_row.addStretch()

        self.btn_forgot = QPushButton("Forgot password?")
        self.btn_forgot.setObjectName("linkButton")
        self.btn_forgot.setFlat(True)
        self.btn_forgot.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_forgot.clicked.connect(self.forgot_password.emit)
        pwd_row.addWidget(self.btn_forgot)
        layout.addLayout(pwd_row)

        layout.addSpacing(6)

        # Password input — full border, 12px radius (ring focus in QSS)
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_edit.setPlaceholderText("Enter your password")
        self.pwd_edit.setMaxLength(MAX_PASSWORD_LENGTH)
        self.pwd_edit.setMinimumHeight(46)
        self.pwd_edit.setFont(QFont("Segoe UI", 10))
        self.pwd_edit.returnPressed.connect(self._on_login)
        layout.addWidget(self.pwd_edit)

        layout.addSpacing(22)

        # Sign In — full-width gradient button
        self.btn_login = QPushButton("Sign In")
        self.btn_login.setObjectName("primaryButton")
        self.btn_login.setMinimumHeight(48)
        self.btn_login.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.clicked.connect(self._on_login)
        layout.addWidget(self.btn_login)

        layout.addSpacing(10)

        # Status / error label
        self.status_label = QLabel("")
        self.status_label.setObjectName("errorLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setMinimumHeight(20)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        outer.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

        # Lockout timer
        self._lockout_timer = QTimer(self)
        self._lockout_timer.setInterval(1000)
        self._lockout_timer.timeout.connect(self._update_lockout)

    # ── Login logic ───────────────────────────────────────────────────────────
    def _on_login(self):
        if session.is_locked_out():
            return

        password = self.pwd_edit.text()
        if not password:
            self.status_label.setText("Please enter your password.")
            self.status_label.setStyleSheet("color: #f43f5e; background: transparent;")
            return

        self.btn_login.setEnabled(False)
        self.btn_login.setText("Verifying…")
        self.status_label.setText("")

        def _verify():
            ok = auth_model.verify_password(password)
            if ok:
                config  = auth_model.get_config()
                aes_key = sec.derive_aes_key(password, config["salt"])
                self._auth_ok.emit(aes_key)
            else:
                self._auth_fail.emit()

        threading.Thread(target=_verify, daemon=True).start()

    def _on_success(self, aes_key: bytes):
        session.login(aes_key)
        self.status_label.setText("")
        self.btn_login.setEnabled(True)
        self.btn_login.setText("Sign In")
        self.pwd_edit.clear()
        self.login_success.emit()

    def _on_failure(self):
        locked = session.record_failed_attempt(MAX_LOGIN_ATTEMPTS, LOCKOUT_SECONDS)
        self.pwd_edit.clear()
        self.btn_login.setEnabled(True)
        self.btn_login.setText("Sign In")
        if locked:
            self.btn_login.setEnabled(False)
            self._lockout_timer.start()
            self._update_lockout()
        else:
            remaining = MAX_LOGIN_ATTEMPTS - session._login_attempts
            self.status_label.setText(
                f"Incorrect password. {remaining} attempt(s) left."
            )
            self.status_label.setStyleSheet("color: #f43f5e; background: transparent;")

    def _update_lockout(self):
        if session.is_locked_out():
            secs = session.seconds_remaining()
            self.status_label.setText(f"Too many attempts. Locked for {secs}s.")
            self.status_label.setStyleSheet("color: #f43f5e; background: transparent;")
        else:
            self._lockout_timer.stop()
            self.btn_login.setEnabled(True)
            self.btn_login.setText("Sign In")
            self.status_label.setText("You may try again.")
            self.status_label.setStyleSheet("color: #10b981; background: transparent;")

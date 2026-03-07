"""Password reset via 3 security questions."""

import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QStackedWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from app.core.constants import MAX_PASSWORD_LENGTH
from app.core import security as sec
from app.models import auth as auth_model
from app.ui.widgets import title_label, field_label, section_label, separator


class ResetScreen(QWidget):
    reset_done = pyqtSignal()
    back_to_login = pyqtSignal()
    _verify_ok_sig = pyqtSignal()
    _verify_fail_sig = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("resetScreen")
        self._verify_ok_sig.connect(self._on_verify_ok)
        self._verify_fail_sig.connect(self._on_verify_fail)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._stack = QStackedWidget()
        self._stack.setFixedWidth(460)

        self._stack.addWidget(self._build_verify_page())
        self._stack.addWidget(self._build_new_pwd_page())

        outer.addWidget(self._stack, alignment=Qt.AlignmentFlag.AlignCenter)

    # ── Step 1: verify security answers ──────────────────────────────────────

    def _build_verify_page(self) -> QWidget:
        page = QFrame()
        page.setObjectName("authCard")
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 32, 32, 32)

        layout.addWidget(title_label("Reset Password"))
        sub = QLabel("Answer your 3 security questions")
        sub.setFont(QFont("Segoe UI", 10))
        sub.setObjectName("subtitle")
        layout.addWidget(sub)
        layout.addWidget(separator())

        # Load questions
        questions = auth_model.get_security_questions()
        self.answer_edits: list[QLineEdit] = []

        for q in questions:
            layout.addWidget(field_label(q["question_text"]))
            ae = QLineEdit()
            ae.setPlaceholderText("Your answer")
            self.answer_edits.append(ae)
            layout.addWidget(ae)

        layout.addWidget(separator())

        self.verify_status = QLabel("")
        self.verify_status.setObjectName("errorLabel")
        self.verify_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.verify_status)

        btn_verify = QPushButton("Verify Answers")
        btn_verify.setObjectName("primaryButton")
        btn_verify.setMinimumHeight(40)
        btn_verify.clicked.connect(self._on_verify)
        layout.addWidget(btn_verify)

        btn_back = QPushButton("Back to Login")
        btn_back.setObjectName("linkButton")
        btn_back.setFlat(True)
        btn_back.clicked.connect(self.back_to_login.emit)
        layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignCenter)

        return page

    def _on_verify(self):
        answers = [e.text() for e in self.answer_edits]
        if any(not a.strip() for a in answers):
            self.verify_status.setText("All answers are required.")
            self.verify_status.setStyleSheet("color: #E74C3C;")
            return

        self.verify_status.setText("Verifying…")

        def _check():
            ok = auth_model.verify_security_answers(answers)
            if ok:
                self._verify_ok_sig.emit()
            else:
                self._verify_fail_sig.emit()

        threading.Thread(target=_check, daemon=True).start()

    def _on_verify_ok(self):
        self._stack.setCurrentIndex(1)

    def _on_verify_fail(self):
        self.verify_status.setText("Answers do not match. Please try again.")
        self.verify_status.setStyleSheet("color: #E74C3C;")
        for e in self.answer_edits:
            e.clear()

    # ── Step 2: set new password ──────────────────────────────────────────────

    def _build_new_pwd_page(self) -> QWidget:
        page = QFrame()
        page.setObjectName("authCard")
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 32, 32, 32)

        layout.addWidget(title_label("New Password"))
        layout.addWidget(separator())

        layout.addWidget(field_label("New Password (min 8 chars):"))
        self.new_pwd = QLineEdit()
        self.new_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pwd.setMaxLength(MAX_PASSWORD_LENGTH)
        layout.addWidget(self.new_pwd)

        layout.addWidget(field_label("Confirm New Password:"))
        self.confirm_pwd = QLineEdit()
        self.confirm_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pwd.setMaxLength(MAX_PASSWORD_LENGTH)
        layout.addWidget(self.confirm_pwd)

        self.pwd_status = QLabel("")
        self.pwd_status.setObjectName("errorLabel")
        self.pwd_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.pwd_status)

        btn_save = QPushButton("Update Password")
        btn_save.setObjectName("primaryButton")
        btn_save.setMinimumHeight(40)
        btn_save.clicked.connect(self._on_save_password)
        layout.addWidget(btn_save)

        return page

    def _on_save_password(self):
        pwd = self.new_pwd.text()
        confirm = self.confirm_pwd.text()

        if len(pwd) < 8:
            self.pwd_status.setText("Password must be at least 8 characters.")
            self.pwd_status.setStyleSheet("color: #E74C3C;")
            return
        if pwd != confirm:
            self.pwd_status.setText("Passwords do not match.")
            self.pwd_status.setStyleSheet("color: #E74C3C;")
            return

        auth_model.change_password(pwd)
        self.pwd_status.setText("Password updated!")
        self.pwd_status.setStyleSheet("color: #2ECC71;")
        self.reset_done.emit()

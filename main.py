"""
Financial Tracker — Entry Point
Run via: run.bat  OR  python main.py
"""

import sys
import os
import traceback
import datetime

# ── Crash log (packaged build only) ───────────────────────────────────────────
# When frozen (PyInstaller), stderr is gone.  Write every unhandled exception
# to crash.log next to the .exe so the user can report it.
if getattr(sys, "frozen", False):
    _LOG_PATH = os.path.join(os.path.dirname(sys.executable), "crash.log")

    def _log_exception(exc_type, exc_value, exc_tb):
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n{datetime.datetime.now()}\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
        # Also try to show a Qt message box if QApplication exists
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            if QApplication.instance():
                msg = QMessageBox()
                msg.setWindowTitle("Unexpected Error")
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setText(
                    "An unexpected error occurred.\n\n"
                    f"Details have been saved to:\n{_LOG_PATH}"
                )
                msg.exec()
        except Exception:
            pass

    sys.excepthook = _log_exception

# ── Thread exception logging (Python 3.8+) ────────────────────────────────────
def _thread_excepthook(args):
    if getattr(sys, "frozen", False):
        _log_exception(args.exc_type, args.exc_value, args.exc_traceback)
    else:
        traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback)

import threading
threading.excepthook = _thread_excepthook

# Ensure the app directory is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from app.core.database import initialize_database, is_first_run
from app.core.constants import ICON_PATH, QSS_PATH
from app.core.session import session


def load_stylesheet(app: QApplication) -> None:
    try:
        with open(QSS_PATH, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass  # run without theme if QSS is missing


class AppController:
    """
    Manages screen transitions:
      setup → login → main_window (loop back to login on lock)
    """

    def __init__(self, app: QApplication):
        self.app = app
        self.window = QMainWindow()
        self.window.setWindowTitle("Financial Tracker")
        self.window.setMinimumSize(1100, 700)
        try:
            self.window.setWindowIcon(QIcon(ICON_PATH))
        except Exception:
            pass

        self.stack = QStackedWidget()
        self.window.setCentralWidget(self.stack)

        self._pages = {}
        self._show_initial()

    def _show_initial(self):
        if is_first_run():
            self._goto_setup()
        else:
            self._goto_login()

    def _goto_setup(self):
        if "setup" not in self._pages:
            from app.ui.setup_screen import SetupScreen
            p = SetupScreen()
            p.setup_complete.connect(self._goto_login)
            self._pages["setup"] = p
            self.stack.addWidget(p)
        self._show("setup")

    def _goto_login(self):
        # Rebuild login page each time (clears password field state)
        if "login" in self._pages:
            self.stack.removeWidget(self._pages["login"])
            self._pages["login"].deleteLater()
            del self._pages["login"]

        from app.ui.login_screen import LoginScreen
        p = LoginScreen()
        p.login_success.connect(self._goto_main)
        p.forgot_password.connect(self._goto_reset)
        self._pages["login"] = p
        self.stack.addWidget(p)
        self._show("login")

    def _goto_reset(self):
        if "reset" in self._pages:
            self.stack.removeWidget(self._pages["reset"])
            self._pages["reset"].deleteLater()
            del self._pages["reset"]

        from app.ui.reset_screen import ResetScreen
        p = ResetScreen()
        p.reset_done.connect(self._goto_login)
        p.back_to_login.connect(self._goto_login)
        self._pages["reset"] = p
        self.stack.addWidget(p)
        self._show("reset")

    def _goto_main(self):
        # Rebuild main window each time (fresh state after login)
        if "main" in self._pages:
            self.stack.removeWidget(self._pages["main"])
            self._pages["main"].deleteLater()
            del self._pages["main"]

        from app.ui.main_window import MainWindow
        p = MainWindow(on_logout=self._goto_login)
        self._pages["main"] = p
        self.stack.addWidget(p)
        self._show("main")

    def _show(self, key: str):
        self.stack.setCurrentWidget(self._pages[key])

    def show(self):
        self.window.show()


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Financial Tracker")
    app.setOrganizationName("Personal")

    # Load dark theme
    load_stylesheet(app)

    # Initialise database (creates tables if needed)
    initialize_database()

    # Start app controller
    controller = AppController(app)
    controller.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

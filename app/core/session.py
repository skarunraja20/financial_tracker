"""In-memory session state. Never persisted to disk."""

from datetime import datetime, timedelta
from typing import Optional


class AppSession:
    """Holds runtime authentication state. Cleared on logout/lock."""

    def __init__(self):
        self.is_authenticated: bool = False
        self.aes_key: Optional[bytes] = None       # 32-byte AES key, derived at login
        self._login_attempts: int = 0
        self._locked_until: Optional[datetime] = None

    # ── Lockout logic ─────────────────────────────────────────────────────────
    def record_failed_attempt(self, max_attempts: int, lockout_seconds: int) -> bool:
        """Record a failed login. Returns True if now locked out."""
        self._login_attempts += 1
        if self._login_attempts >= max_attempts:
            self._locked_until = datetime.now() + timedelta(seconds=lockout_seconds)
            return True
        return False

    def is_locked_out(self) -> bool:
        if self._locked_until is None:
            return False
        if datetime.now() >= self._locked_until:
            self._locked_until = None
            self._login_attempts = 0
            return False
        return True

    def seconds_remaining(self) -> int:
        if self._locked_until is None:
            return 0
        remaining = (self._locked_until - datetime.now()).total_seconds()
        return max(0, int(remaining))

    # ── Auth ──────────────────────────────────────────────────────────────────
    def login(self, aes_key: bytes) -> None:
        self.is_authenticated = True
        # Store as mutable bytearray so we can zero it in-place on logout.
        # bytearray is accepted by AESGCM and all cryptography APIs.
        self.aes_key = bytearray(aes_key)
        self._login_attempts = 0
        self._locked_until = None

    def logout(self) -> None:
        self.is_authenticated = False
        if self.aes_key:
            # Zero the mutable bytearray in-place before dereferencing.
            # This minimises the window during which the raw key material
            # could be recovered from a memory dump.
            for i in range(len(self.aes_key)):
                self.aes_key[i] = 0
        self.aes_key = None
        self._login_attempts = 0
        self._locked_until = None


# Singleton instance shared across the app
session = AppSession()

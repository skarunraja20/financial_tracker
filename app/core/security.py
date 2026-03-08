"""
Security utilities: bcrypt password hashing + AES-256-GCM encryption.
The AES key is derived from the master password and NEVER stored on disk.
"""

import os
import base64
import bcrypt

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.constants import BCRYPT_ROUNDS, PBKDF2_ITERATIONS


# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt. Returns the hash as a string."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS))
    return hashed.decode("utf-8")


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except Exception:
        return False


# ── Security question hashing ─────────────────────────────────────────────────

def hash_answer(answer: str) -> str:
    """Normalize and hash a security question answer."""
    normalized = answer.strip().lower()
    hashed = bcrypt.hashpw(normalized.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS))
    return hashed.decode("utf-8")


def verify_answer(answer: str, stored_hash: str) -> bool:
    """Verify a security question answer against its stored hash."""
    try:
        normalized = answer.strip().lower()
        return bcrypt.checkpw(normalized.encode("utf-8"), stored_hash.encode("utf-8"))
    except Exception:
        return False


# ── AES-256 key derivation ────────────────────────────────────────────────────

def generate_salt() -> str:
    """Generate a random 32-byte salt and return as base64 string for storage."""
    return base64.b64encode(os.urandom(32)).decode("utf-8")


def derive_aes_key(password: str, salt_b64: str) -> bytes:
    """
    Derive a 32-byte AES-256 key from password + salt using PBKDF2-HMAC-SHA256.
    The derived key is NEVER stored — only held in memory during the session.
    """
    salt = base64.b64decode(salt_b64.encode("utf-8"))
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


# ── AES-256-GCM field encryption ──────────────────────────────────────────────

def encrypt_field(plaintext: str, key: bytes) -> str:
    """
    Encrypt a string field using AES-256-GCM.
    Returns a base64-encoded string: nonce(12) + ciphertext + tag(16).
    """
    if not plaintext:
        return ""
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    combined = nonce + ciphertext
    return base64.b64encode(combined).decode("utf-8")


def decrypt_field(encrypted_b64: str, key: bytes) -> str:
    """
    Decrypt a field encrypted with encrypt_field.
    Returns the original plaintext, or "[encrypted]" on failure.

    Security: only specific, expected exceptions are caught.
    - InvalidTag  → GCM authentication failed (wrong key or data tampering).
    - ValueError  → malformed base64 or encoding issues.
    Unexpected exceptions are intentionally re-raised so they are not silently lost.
    """
    if not encrypted_b64:
        return ""
    try:
        combined = base64.b64decode(encrypted_b64.encode("utf-8"))
    except (ValueError, Exception):
        # Malformed base64 — treat as unreadable but do not crash
        return "[encrypted]"

    if len(combined) < 28:
        # Minimum valid payload: 12-byte nonce + 16-byte GCM tag = 28 bytes
        return "[encrypted]"

    nonce = combined[:12]
    ciphertext = combined[12:]
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    except InvalidTag:
        # Authentication tag mismatch — wrong key or data was tampered with
        return "[encrypted]"

    return plaintext.decode("utf-8")


def safe_decrypt_field(value: str, key: bytes) -> str:
    """
    Decrypt a sensitive field, falling back to the raw value when decryption
    fails (backward-compatible: handles plaintext values stored before
    field-level encryption was wired up).
    """
    if not value or not key:
        return value
    result = decrypt_field(value, key)
    if result == "[encrypted]":
        # Could not decrypt — value was likely stored as plaintext before
        # encryption was enabled.  Return as-is so no data is lost.
        return value
    return result

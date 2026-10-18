"""Data Protection API (DPAPI) credential encryption for Ravaan.

Encrypts sync tokens and sensitive credentials on Windows using the logged-in
user's DPAPI credentials via ctypes. Non-Windows environments use a safe
reversible fallback for CI test compatibility.
"""

from __future__ import annotations

import base64
import ctypes
import logging
import sys

log = logging.getLogger(__name__)

DPAPI_PREFIX = "dpapi:"
MOCK_PREFIX = "mock-dpapi:"


def _is_windows() -> bool:
    return sys.platform == "win32"


if _is_windows():
    from ctypes import wintypes

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]


def protect_secret(plain: str) -> str:
    """Encrypt a sensitive string using Windows DPAPI (or mock fallback on non-Windows)."""
    if not plain:
        return ""
    if plain.startswith(DPAPI_PREFIX) or plain.startswith(MOCK_PREFIX):
        return plain

    raw = plain.encode("utf-8")
    if not _is_windows():
        return MOCK_PREFIX + base64.b64encode(raw).decode("ascii")

    try:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        in_blob = _DATA_BLOB(
            len(raw),
            ctypes.cast(ctypes.create_string_buffer(raw), ctypes.POINTER(ctypes.c_char)),
        )
        out_blob = _DATA_BLOB()
        if not crypt32.CryptProtectData(
            ctypes.byref(in_blob),
            "RavaanSyncSecret",
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob),
        ):
            log.warning("CryptProtectData failed; falling back to mock")
            return MOCK_PREFIX + base64.b64encode(raw).decode("ascii")

        try:
            cipher = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            return DPAPI_PREFIX + base64.b64encode(cipher).decode("ascii")
        finally:
            kernel32.LocalFree(out_blob.pbData)
    except Exception as exc:  # noqa: BLE001
        log.warning("DPAPI encryption error: %s", exc)
        return MOCK_PREFIX + base64.b64encode(raw).decode("ascii")


def unprotect_secret(cipher: str) -> tuple[str, bool]:
    """Decrypt a DPAPI string.

    Returns:
        (plain_text, was_migrated)
        was_migrated is True if the input was plaintext and needs encryption on save.
    """
    if not cipher:
        return "", False

    if cipher.startswith(MOCK_PREFIX):
        try:
            dec = base64.b64decode(cipher[len(MOCK_PREFIX) :]).decode("utf-8")
            return dec, False
        except Exception:  # noqa: BLE001
            return cipher, False

    if not cipher.startswith(DPAPI_PREFIX):
        # Input is unencrypted legacy plaintext token
        return cipher, True

    if not _is_windows():
        # Running on non-windows runner reading a DPAPI string
        return cipher, False

    try:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        raw_cipher = base64.b64decode(cipher[len(DPAPI_PREFIX) :])
        in_blob = _DATA_BLOB(
            len(raw_cipher),
            ctypes.cast(ctypes.create_string_buffer(raw_cipher), ctypes.POINTER(ctypes.c_char)),
        )
        out_blob = _DATA_BLOB()
        if not crypt32.CryptUnprotectData(
            ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
        ):
            log.warning("CryptUnprotectData failed")
            return "", False

        try:
            plain_bytes = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            return plain_bytes.decode("utf-8"), False
        finally:
            kernel32.LocalFree(out_blob.pbData)
    except Exception as exc:  # noqa: BLE001
        log.warning("DPAPI decryption error: %s", exc)
        return "", False

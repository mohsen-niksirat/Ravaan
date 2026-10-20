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


CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2

WINCRED_PREFIX = "wincred:"
CRED_TARGET_GIST = "Ravaan/GitHubGistToken"
CRED_TARGET_WEBDAV = "Ravaan/WebDAVPassword"
CRED_TARGET_AI = "Ravaan/AIApiKey"

_MOCK_CREDENTIAL_STORE: dict[str, str] = {}


if _is_windows():
    from ctypes import wintypes

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    class _CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.c_char_p),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
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
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p

        raw_buf = ctypes.create_string_buffer(raw)
        in_blob = _DATA_BLOB(
            len(raw),
            ctypes.cast(raw_buf, ctypes.POINTER(ctypes.c_char)),
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
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p

        raw_cipher = base64.b64decode(cipher[len(DPAPI_PREFIX) :])
        raw_cipher_buf = ctypes.create_string_buffer(raw_cipher)
        in_blob = _DATA_BLOB(
            len(raw_cipher),
            ctypes.cast(raw_cipher_buf, ctypes.POINTER(ctypes.c_char)),
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


def encrypt_secret(plain: str) -> str:
    """Convenience alias for protect_secret."""
    return protect_secret(plain)


def decrypt_secret(cipher: str) -> str:
    """Convenience decrypt returning plain string."""
    plain, _ = unprotect_secret(cipher)
    return plain


def save_credential(target: str, secret: str, user_name: str = "Ravaan") -> bool:
    """Save a secret string to Windows Credential Manager (or mock store on non-Windows)."""
    if not target:
        return False
    if not secret:
        delete_credential(target)
        return True

    if not _is_windows():
        _MOCK_CREDENTIAL_STORE[target] = secret
        return True

    try:
        advapi32 = ctypes.windll.advapi32
        secret_bytes = secret.encode("utf-8")
        cred = _CREDENTIALW()
        cred.Flags = 0
        cred.Type = CRED_TYPE_GENERIC
        cred.TargetName = target
        cred.CredentialBlobSize = len(secret_bytes)
        cred.CredentialBlob = secret_bytes
        cred.Persist = CRED_PERSIST_LOCAL_MACHINE
        cred.UserName = user_name
        res = advapi32.CredWriteW(ctypes.byref(cred), 0)
        if not res:
            log.warning("CredWriteW failed for target %s; falling back to mock", target)
            _MOCK_CREDENTIAL_STORE[target] = secret
            return False
        _MOCK_CREDENTIAL_STORE[target] = secret
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("Windows Credential Manager save error for %s: %s", target, exc)
        _MOCK_CREDENTIAL_STORE[target] = secret
        return False


def get_credential(target: str) -> str:
    """Retrieve a secret string from Windows Credential Manager (or mock store)."""
    if not target:
        return ""

    if not _is_windows():
        return _MOCK_CREDENTIAL_STORE.get(target, "")

    try:
        advapi32 = ctypes.windll.advapi32
        pcred = ctypes.POINTER(_CREDENTIALW)()
        res = advapi32.CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(pcred))
        if not res or not pcred:
            return _MOCK_CREDENTIAL_STORE.get(target, "")
        try:
            raw_blob = ctypes.string_at(
                pcred.contents.CredentialBlob, pcred.contents.CredentialBlobSize
            )
            val = raw_blob.decode("utf-8")
            _MOCK_CREDENTIAL_STORE[target] = val
            return val
        finally:
            advapi32.CredFree(pcred)
    except Exception as exc:  # noqa: BLE001
        log.warning("Windows Credential Manager read error for %s: %s", target, exc)
        return _MOCK_CREDENTIAL_STORE.get(target, "")


def delete_credential(target: str) -> bool:
    """Delete a credential from Windows Credential Manager (and mock store)."""
    _MOCK_CREDENTIAL_STORE.pop(target, None)
    if not _is_windows():
        return True

    try:
        advapi32 = ctypes.windll.advapi32
        res = advapi32.CredDeleteW(target, CRED_TYPE_GENERIC, 0)
        return bool(res)
    except Exception as exc:  # noqa: BLE001
        log.warning("Windows Credential Manager delete error for %s: %s", target, exc)
        return False


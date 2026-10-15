"""Keyboard language detection."""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes

from ravan.core.events import LanguageInfo

from . import winapi as w

log = logging.getLogger(__name__)

_PRIMARY = {
    0x29: ("fa", "Persian"),
    0x09: ("en", "English"),
    0x01: ("ar", "Arabic"),
    0x19: ("ru", "Russian"),
    0x07: ("de", "German"),
    0x0C: ("fr", "French"),
}


def hkl_to_language_info(hkl: int) -> LanguageInfo:
    langid = hkl & 0xFFFF
    primary = langid & 0x3FF
    if primary in _PRIMARY:
        tag, name = _PRIMARY[primary]
    else:
        name = _get_locale_name(langid) or f"lang-{langid:#06x}"
        tag = name
    return LanguageInfo(tag=tag, name=name, hkl=hkl)


def _as_hkl(value: object) -> int:
    """Normalize ctypes HKL / handle returns to a plain int."""
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    # c_void_p / c_size_t etc.
    raw = getattr(value, "value", value)
    return int(raw or 0)


def current_language() -> LanguageInfo | None:
    hwnd = w.user32.GetForegroundWindow()
    thread_id = 0
    if hwnd:
        thread_id = int(w.user32.GetWindowThreadProcessId(hwnd, None) or 0)
    hkl = _as_hkl(w.user32.GetKeyboardLayout(thread_id))
    if hkl == 0:
        # Fallback: layout of the calling thread
        hkl = _as_hkl(w.user32.GetKeyboardLayout(0))
    if hkl == 0:
        return None
    return hkl_to_language_info(hkl)


def _get_locale_name(langid: int) -> str | None:
    buf = ctypes.create_unicode_buffer(85)
    # GetLocaleInfoW is in kernel32 on older Windows, but often re-exported.
    get_locale = getattr(w.kernel32, "GetLocaleInfoW", None)
    if get_locale is None:
        return None
    get_locale.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.LPWSTR, ctypes.c_int]
    get_locale.restype = ctypes.c_int
    length = get_locale(langid, w.LOCALE_SNAME, buf, 85)
    if length <= 1:
        return None
    return buf.value


def language_label(info: LanguageInfo) -> str:
    if info.tag.lower().startswith("fa"):
        return "فا"
    if info.tag.lower().startswith("en"):
        return "EN"
    return info.tag.upper()[:3]

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
    try:
        return int(raw or 0)  # type: ignore[call-overload]
    except (ValueError, TypeError):
        return 0


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


def get_installed_layouts() -> list[LanguageInfo]:
    """Return all keyboard layouts installed in Windows."""
    try:
        count = int(w.user32.GetKeyboardLayoutList(0, None) or 0)
        if count <= 0:
            return []
        buf = (wintypes.HKL * count)()
        actual = int(w.user32.GetKeyboardLayoutList(count, buf) or 0)
        out: list[LanguageInfo] = []
        for i in range(actual):
            hkl = _as_hkl(buf[i])
            if hkl != 0:
                out.append(hkl_to_language_info(hkl))
        return out
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to query installed keyboard layouts: %s", exc)
        return []


def get_layout_for_language(lang_tag: str) -> int | None:
    """Return HKL matching given language tag ('fa', 'en') from installed layouts."""
    tag_clean = lang_tag.strip().lower()
    for info in get_installed_layouts():
        if info.tag.lower().startswith(tag_clean) or tag_clean.startswith(info.tag.lower()):
            return info.hkl
    return None


_mock_ime_composing: bool | None = None


def set_mock_ime_composing(val: bool | None) -> None:
    global _mock_ime_composing
    _mock_ime_composing = val


def is_ime_composing(hwnd: int | None = None) -> bool:
    """Return True if the target window is currently mid-IME composition."""
    if _mock_ime_composing is not None:
        return _mock_ime_composing
    try:
        target_hwnd = hwnd or w.user32.GetForegroundWindow()
        if not target_hwnd:
            return False
        imm32 = getattr(ctypes.windll, "imm32", None)
        if imm32 is None:
            return False
        if not hasattr(imm32, "_prototyped"):
            imm32.ImmGetContext.argtypes = [wintypes.HWND]
            imm32.ImmGetContext.restype = wintypes.HANDLE
            imm32.ImmReleaseContext.argtypes = [wintypes.HWND, wintypes.HANDLE]
            imm32.ImmReleaseContext.restype = wintypes.BOOL
            imm32.ImmGetCompositionStringW.argtypes = [
                wintypes.HANDLE,
                wintypes.DWORD,
                wintypes.LPVOID,
                wintypes.DWORD,
            ]
            imm32.ImmGetCompositionStringW.restype = wintypes.LONG
            imm32._prototyped = True
        himc = imm32.ImmGetContext(target_hwnd)
        if not himc:
            return False
        try:
            # GCS_COMPSTR = 0x0008
            comp_len = imm32.ImmGetCompositionStringW(himc, 0x0008, None, 0)
            return int(comp_len or 0) > 0
        finally:
            imm32.ImmReleaseContext(target_hwnd, himc)
    except Exception:  # noqa: BLE001
        return False


def switch_to_language(lang_tag: str, hwnd: int | None = None) -> bool:
    """Activate Windows keyboard layout corresponding to lang_tag ('fa' or 'en')."""
    hkl = get_layout_for_language(lang_tag)
    if not hkl:
        log.debug("No installed layout found for language tag %r", lang_tag)
        return False

    target_hwnd = hwnd or w.user32.GetForegroundWindow()
    # WM_INPUTLANGCHANGEREQUEST = 0x0050, KLF_SETFORPROCESS = 0x00000100
    try:
        if target_hwnd:
            w.user32.PostMessageW(target_hwnd, 0x0050, 0, hkl)
        w.user32.ActivateKeyboardLayout(hkl, 0x00000100)
        log.info("Switched keyboard layout to %s (HKL: %#x)", lang_tag, hkl)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to switch keyboard layout to %s: %s", lang_tag, exc)
        return False

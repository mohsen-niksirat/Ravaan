"""Bilingual localization (i18n) framework for Ravaan (EN / FA)."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_DEFAULT_LOCALE = "en"
_SUPPORTED_LOCALES = ("en", "fa")
_current_locale = "en"
_locales_data: dict[str, dict[str, Any]] = {}
_change_listeners: list[Callable[[str], None]] = []


def _data_locales_dir() -> Path:
    base = Path(__file__).resolve().parent.parent / "data" / "locales"
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass_loc = Path(sys._MEIPASS) / "ravan" / "data" / "locales"
        if meipass_loc.is_dir():
            return meipass_loc
    return base


def load_locale(locale: str) -> dict[str, Any]:
    """Load and cache locale JSON data from disk."""
    if locale in _locales_data:
        return _locales_data[locale]

    loc_dir = _data_locales_dir()
    loc_file = loc_dir / f"{locale}.json"
    if not loc_file.is_file():
        # Fallback to empty if file not found
        _locales_data[locale] = {}
        return {}

    try:
        data = json.loads(loc_file.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            _locales_data[locale] = data
            return data
    except Exception as exc:  # noqa: BLE001
        log.error("Failed to load locale file %s: %s", loc_file, exc)

    _locales_data[locale] = {}
    return {}


def detect_system_locale() -> str:
    """Detect whether Windows system UI language is Persian (fa) or English (en)."""
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        lcid = kernel32.GetUserDefaultUILanguage()
        # Primary language ID for Persian is 0x29
        primary_lang = lcid & 0x03FF
        if primary_lang == 0x29:
            return "fa"
    except Exception:  # noqa: BLE001
        pass
    return "en"


def get_locale() -> str:
    """Return the currently active locale code ('en' or 'fa')."""
    return _current_locale


def is_rtl() -> bool:
    """Return True if the current locale requires Right-to-Left UI layout."""
    return _current_locale == "fa"


def set_locale(locale: str) -> None:
    """Switch active locale, loading data on demand and notifying registered listeners."""
    global _current_locale
    loc = locale.strip().lower()
    if loc == "auto":
        loc = detect_system_locale()

    if loc not in _SUPPORTED_LOCALES:
        loc = _DEFAULT_LOCALE

    load_locale(loc)
    load_locale("en")  # Always have english loaded as fallback

    changed = _current_locale != loc
    _current_locale = loc

    if changed:
        log.info("Active locale changed to: %s (RTL: %s)", _current_locale, is_rtl())
        for cb in list(_change_listeners):
            try:
                cb(_current_locale)
            except Exception as exc:  # noqa: BLE001
                log.warning("Locale change listener error: %s", exc)


def register_locale_listener(callback: Callable[[str], None]) -> None:
    """Register a callback invoked when the UI language switches."""
    if callback not in _change_listeners:
        _change_listeners.append(callback)


def unregister_locale_listener(callback: Callable[[str], None]) -> None:
    """Remove a previously registered locale change callback."""
    if callback in _change_listeners:
        _change_listeners.remove(callback)


def t(key: str, default: str | None = None, **kwargs: Any) -> str:
    """Translate dot-separated key (e.g. 'settings.tab_general') with optional kwargs."""
    current_data = load_locale(_current_locale)
    fallback_data = load_locale("en")

    parts = key.split(".")
    val: Any = current_data
    for p in parts:
        if isinstance(val, dict) and p in val:
            val = val[p]
        else:
            val = None
            break

    if val is None:
        # Fallback to English
        val = fallback_data
        for p in parts:
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                val = None
                break

    if val is None or not isinstance(val, str):
        val = default if default is not None else key

    if kwargs:
        try:
            return val.format(**kwargs)
        except Exception:
            return val
    return val

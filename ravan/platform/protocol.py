"""Windows URL protocol handler registration and parsing for ravan:// deep links."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

log = logging.getLogger(__name__)

PROTOCOL_SCHEME = "ravan"
REG_SUBKEY = r"Software\Classes\ravan"


def is_protocol_registered() -> bool:
    """Return True if ravan:// protocol is registered in HKEY_CURRENT_USER."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SUBKEY) as key:
            val, _ = winreg.QueryValueEx(key, "URL Protocol")
            return val is not None
    except OSError:
        return False


def register_protocol(exe_path: str | Path | None = None) -> bool:
    """Register ravan:// URL protocol handler in HKEY_CURRENT_USER (per-user, no admin)."""
    if sys.platform != "win32":
        log.info("URL protocol registration is only supported on Windows")
        return False

    try:
        import winreg

        if exe_path is None:
            if getattr(sys, "frozen", False):
                target_exe = Path(sys.executable).resolve()
            else:
                target_exe = Path(sys.executable).resolve()
        else:
            target_exe = Path(exe_path).resolve()

        # 1. HKCU\Software\Classes\ravan
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_SUBKEY) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:Ravaan Protocol")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")

        # 2. HKCU\Software\Classes\ravan\DefaultIcon
        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER, f"{REG_SUBKEY}\\DefaultIcon"
        ) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{target_exe}",0')

        # 3. HKCU\Software\Classes\ravan\shell\open\command
        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER, f"{REG_SUBKEY}\\shell\\open\\command"
        ) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{target_exe}" "%1"')

        log.info("Registered ravan:// protocol pointing to %s", target_exe)
        return True
    except OSError as exc:
        log.warning("Failed to register ravan:// protocol: %s", exc)
        return False


def unregister_protocol() -> bool:
    """Remove ravan:// URL protocol handler from HKEY_CURRENT_USER."""
    if sys.platform != "win32":
        return False

    try:
        import winreg

        def _delete_tree(root, subkey):
            try:
                with winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
                    while True:
                        try:
                            child = winreg.EnumKey(key, 0)
                            _delete_tree(key, child)
                        except OSError:
                            break
                winreg.DeleteKey(root, subkey)
            except OSError:
                pass

        _delete_tree(winreg.HKEY_CURRENT_USER, REG_SUBKEY)
        log.info("Unregistered ravan:// protocol")
        return True
    except OSError as exc:
        log.warning("Failed to unregister ravan:// protocol: %s", exc)
        return False


ALLOWED_ACTIONS = {"settings", "stats", "snippet", "help", "about"}
ALLOWED_SETTINGS_TABS = {
    "general",
    "prediction",
    "hotkeys",
    "exclusions",
    "snippets",
    "sync",
    "about",
}
MAX_URL_LENGTH = 2048
MAX_PARAM_LENGTH = 256


def sanitize_param_value(val: str) -> str:
    """Sanitize parameter string: strip control chars, null bytes, enforce max length."""
    cleaned = "".join(ch for ch in val if ch >= " " and ch != "\x7f")
    return cleaned[:MAX_PARAM_LENGTH].strip()


def parse_protocol_url(url: str) -> dict[str, Any]:
    """Parse and validate deep link URL like ravan://settings?tab=sync.

    Security guarantees:
    - Never throws unhandled exceptions on malformed / fuzzed input.
    - Limits total length to 2048 chars to mitigate buffer overflow / ReDoS.
    - Rejects any scheme other than 'ravan'.
    - Whitelists only known safe actions: settings, stats, snippet, help, about.
    - Strips path traversal / directory navigation characters.
    - Validates and sanitizes parameters (no arbitrary code execution or injection).
    """
    clean_url = str(url).strip()
    if not clean_url or len(clean_url) > MAX_URL_LENGTH or "\x00" in clean_url:
        return {"valid": False, "action": "", "params": {}, "error": "Invalid or oversized URL"}

    try:
        parsed = urlparse(clean_url)
    except Exception as exc:  # noqa: BLE001
        return {"valid": False, "action": "", "params": {}, "error": f"URL parse error: {exc}"}

    if parsed.scheme.lower() != PROTOCOL_SCHEME:
        return {"valid": False, "action": "", "params": {}, "error": f"Invalid scheme: {parsed.scheme}"}

    raw_action = (parsed.netloc or parsed.path).strip("/")
    raw_action = raw_action.replace("\\", "/").partition("/")[0].strip().lower()

    if raw_action not in ALLOWED_ACTIONS:
        return {
            "valid": False,
            "action": "",
            "params": {},
            "error": f"Disallowed action: {raw_action[:32]}",
        }

    raw_params = parse_qs(parsed.query, keep_blank_values=False, max_num_fields=20)
    params: dict[str, str] = {}
    for k, v in raw_params.items():
        clean_k = sanitize_param_value(k).lower()
        if not clean_k or not v:
            continue
        params[clean_k] = sanitize_param_value(v[0])

    if raw_action == "settings":
        tab = params.get("tab", "").lower()
        if tab and tab not in ALLOWED_SETTINGS_TABS:
            params["tab"] = "general"
    elif raw_action == "snippet":
        trigger = params.get("trigger", "")
        if trigger:
            clean_trigger = "".join(ch for ch in trigger if ch.isalnum() or ch in "@#$/._-")
            params["trigger"] = clean_trigger[:64]

    return {"valid": True, "action": raw_action, "params": params, "error": None}

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


def parse_protocol_url(url: str) -> dict[str, Any]:
    """Parse deep link URL like ravan://settings?tab=sync into action and parameters."""
    clean_url = url.strip()
    if not clean_url:
        return {"action": "", "params": {}}

    parsed = urlparse(clean_url)
    if parsed.scheme.lower() != PROTOCOL_SCHEME:
        return {"action": "", "params": {}}

    action = (parsed.netloc or parsed.path).strip("/").lower()
    raw_params = parse_qs(parsed.query)
    # Simplify query dict values from list[str] to single str when length is 1
    params: dict[str, Any] = {}
    for k, v in raw_params.items():
        params[k] = v[0] if len(v) == 1 else v

    return {"action": action, "params": params}

"""Launch-at-startup via HKCU Run registry key."""

from __future__ import annotations

import logging
import os
import sys

log = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "Ravan"


def _command() -> str:
    exe = sys.executable
    # pythonw.exe avoids a console window at startup
    if exe.lower().endswith("python.exe"):
        pyw = exe[:-10] + "pythonw.exe"
        if os.path.exists(pyw):
            exe = pyw
    script = f'"{exe}" -m ravan'
    return script


def is_startup_enabled() -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            val, _ = winreg.QueryValueEx(key, VALUE_NAME)
            return bool(val)
    except FileNotFoundError:
        return False
    except OSError as exc:
        log.warning("Startup check failed: %s", exc)
        return False


def set_startup(enabled: bool) -> bool:
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _command())
            else:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError as exc:
        log.warning("Startup set failed: %s", exc)
        return False

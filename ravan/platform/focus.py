"""Foreground window / process tracking."""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes
from typing import Any

from . import winapi as w

log = logging.getLogger(__name__)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _query_full_process_name(hprocess: wintypes.HANDLE) -> str | None:
    buf = ctypes.create_unicode_buffer(1024)
    size = wintypes.DWORD(len(buf))
    kernel32 = w.kernel32
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    ok = kernel32.QueryFullProcessImageNameW(
        hprocess, 0, buf, ctypes.byref(size)
    )
    if not ok:
        return None
    return buf.value


def exe_for_hwnd(hwnd: int | None = None) -> str | None:
    """Return the executable file name (lowercased) of the given window (or foreground if None)."""
    target_hwnd = hwnd or w.user32.GetForegroundWindow()
    if not target_hwnd:
        return None
    pid = wintypes.DWORD(0)
    w.user32.GetWindowThreadProcessId(target_hwnd, ctypes.byref(pid))
    if not pid.value:
        return None
    kernel32 = w.kernel32
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    hprocess = kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value
    )
    if not hprocess:
        return None
    try:
        name = _query_full_process_name(hprocess)
    finally:
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        kernel32.CloseHandle(hprocess)
    if not name:
        return None
    return name.rsplit("\\", 1)[-1].lower()


def foreground_exe() -> str | None:
    """Return the executable file name (lowercased) of the foreground window."""
    return exe_for_hwnd(w.user32.GetForegroundWindow())


def window_title(hwnd: int | None = None) -> str | None:
    target_hwnd = hwnd or w.user32.GetForegroundWindow()
    if not target_hwnd:
        return None
    w.user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    w.user32.GetWindowTextLengthW.restype = ctypes.c_int
    length = w.user32.GetWindowTextLengthW(target_hwnd)
    if length <= 0:
        return None
    buf = ctypes.create_unicode_buffer(length + 1)
    w.user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    w.user32.GetWindowTextW.restype = ctypes.c_int
    w.user32.GetWindowTextW(target_hwnd, buf, length + 1)
    return buf.value


def window_class_name(hwnd: int | None = None) -> str | None:
    target_hwnd = hwnd or w.user32.GetForegroundWindow()
    if not target_hwnd:
        return None
    buf = ctypes.create_unicode_buffer(256)
    w.user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    w.user32.GetClassNameW.restype = ctypes.c_int
    res = w.user32.GetClassNameW(target_hwnd, buf, 256)
    return buf.value if res > 0 else None


def is_current_process_elevated() -> bool:
    try:
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        return bool(shell32.IsUserAnAdmin())
    except Exception:
        return False


def is_window_elevated(hwnd: int | None = None) -> bool:
    """Return True if the target window's process is elevated while current process is not."""
    if is_current_process_elevated():
        return False
    target_hwnd = hwnd or w.user32.GetForegroundWindow()
    if not target_hwnd:
        return False
    pid = wintypes.DWORD(0)
    w.user32.GetWindowThreadProcessId(target_hwnd, ctypes.byref(pid))
    if not pid.value:
        return False
    kernel32 = w.kernel32
    hprocess = kernel32.OpenProcess(0x0400 | 0x1000, False, pid.value)
    if not hprocess:
        err = ctypes.get_last_error()
        return err in (5, 0x5)
    try:
        advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        htoken = wintypes.HANDLE()
        if not advapi32.OpenProcessToken(hprocess, 0x0008, ctypes.byref(htoken)):
            return ctypes.get_last_error() in (5, 0x5)
        try:
            class TOKEN_ELEVATION(ctypes.Structure):
                _fields_ = [("TokenIsElevated", wintypes.DWORD)]

            elevation = TOKEN_ELEVATION()
            cb_size = wintypes.DWORD(ctypes.sizeof(elevation))
            if advapi32.GetTokenInformation(
                htoken, 20, ctypes.byref(elevation), cb_size, ctypes.byref(cb_size)
            ):
                return bool(elevation.TokenIsElevated)
        finally:
            kernel32.CloseHandle(htoken)
    except Exception:
        pass
    finally:
        kernel32.CloseHandle(hprocess)
    return False


def active_window_info() -> dict[str, Any]:
    """Return dictionary with hwnd, pid, exe, class_name, and title of current foreground window."""
    hwnd = int(w.user32.GetForegroundWindow() or 0)
    if not hwnd:
        return {"hwnd": 0, "pid": 0, "exe": None, "class_name": None, "title": None}
    pid = wintypes.DWORD(0)
    w.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    exe = foreground_exe()
    title = window_title(hwnd)
    cls_name = window_class_name(hwnd)
    return {
        "hwnd": hwnd,
        "pid": int(pid.value),
        "exe": exe,
        "class_name": cls_name,
        "title": title,
    }


def enumerate_visible_windows() -> list[dict[str, Any]]:
    """Enumerate top-level visible windows with title, exe, and class name."""
    results: list[dict[str, Any]] = []
    wnd_enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _enum_cb(hwnd: int, lparam: int) -> bool:
        try:
            if not w.user32.IsWindowVisible(hwnd):
                return True
            title = window_title(hwnd)
            if not title or not title.strip():
                return True
            exe = exe_for_hwnd(hwnd)
            cls_name = window_class_name(hwnd)
            results.append({
                "hwnd": hwnd,
                "title": title.strip(),
                "exe": exe,
                "class_name": cls_name,
            })
        except Exception:
            pass
        return True

    cb = wnd_enum_proc(_enum_cb)
    w.user32.EnumWindows.argtypes = [wnd_enum_proc, wintypes.LPARAM]
    w.user32.EnumWindows.restype = wintypes.BOOL
    w.user32.EnumWindows(cb, 0)
    return results


_mock_password_focused: bool | None = None


def set_mock_password_focused(value: bool | None) -> None:
    """Mock hook for testing password field detection."""
    global _mock_password_focused
    _mock_password_focused = value


def is_password_focused() -> bool:
    """Return True if the focused control is a password input field.

    Checks:
    1. Test mock override if active.
    2. Classic Win32 EM_GETPASSWORDCHAR and ES_PASSWORD window style.
    3. UI Automation IUIAutomationElement.CurrentIsPassword property.
    """
    if _mock_password_focused is not None:
        return _mock_password_focused

    # 1. Win32 GUI Thread Info check
    try:
        hwnd_fg = w.user32.GetForegroundWindow()
        if hwnd_fg:
            tid = w.user32.GetWindowThreadProcessId(hwnd_fg, None)
            if tid:
                gui_info = w.GUITHREADINFO()
                gui_info.cbSize = ctypes.sizeof(w.GUITHREADINFO)
                if w.user32.GetGUIThreadInfo(tid, ctypes.byref(gui_info)):
                    hwnd_focus = gui_info.hwndFocus
                    if hwnd_focus:
                        # EM_GETPASSWORDCHAR = 0x00D2
                        w.user32.SendMessageW.argtypes = [
                            wintypes.HWND,
                            wintypes.UINT,
                            wintypes.WPARAM,
                            wintypes.LPARAM,
                        ]
                        w.user32.SendMessageW.restype = wintypes.LPARAM
                        pw_char = w.user32.SendMessageW(hwnd_focus, 0x00D2, 0, 0)
                        if pw_char != 0:
                            return True

                        # Check ES_PASSWORD (0x0020) style on edit control
                        style = w.user32.GetWindowLongW(hwnd_focus, -16)  # GWL_STYLE
                        if style & 0x0020:
                            return True
    except Exception:
        pass

    # 2. UI Automation check (browsers, Electron, WPF/UWP)
    try:
        from ravan.platform.caret import _cached_uia_automation

        automation = _cached_uia_automation
        if automation is not None:
            elem = automation.GetFocusedElement()
            if elem is not None and getattr(elem, "CurrentIsPassword", False):
                return True
    except Exception:
        pass

    return False


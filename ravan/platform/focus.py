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


def foreground_exe() -> str | None:
    """Return the executable file name (lowercased) of the foreground window."""
    hwnd = w.user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = wintypes.DWORD(0)
    w.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
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


def window_title() -> str | None:
    hwnd = w.user32.GetForegroundWindow()
    if not hwnd:
        return None
    w.user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    w.user32.GetWindowTextLengthW.restype = ctypes.c_int
    length = w.user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return None
    buf = ctypes.create_unicode_buffer(length + 1)
    w.user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    w.user32.GetWindowTextW.restype = ctypes.c_int
    w.user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def active_window_info() -> dict[str, Any]:
    """Return dictionary with hwnd, pid, exe, and title of current foreground window."""
    hwnd = int(w.user32.GetForegroundWindow() or 0)
    if not hwnd:
        return {"hwnd": 0, "pid": 0, "exe": None, "title": None}
    pid = wintypes.DWORD(0)
    w.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    exe = foreground_exe()
    title = window_title()
    return {"hwnd": hwnd, "pid": int(pid.value), "exe": exe, "title": title}


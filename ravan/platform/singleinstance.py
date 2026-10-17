"""Single-instance guard via a named Windows mutex."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

ERROR_ALREADY_EXISTS = 183
ERROR_ACCESS_DENIED = 5

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
kernel32.ReleaseMutex.restype = wintypes.BOOL


class SingleInstance:
    """Hold a named mutex for the process lifetime.

    Usage:
        guard = SingleInstance("Ravan")
        if not guard.acquired:
            print("Already running")
            return 1
    """

    def __init__(self, name: str = "Ravan") -> None:
        self._handle = None
        self.acquired = False
        # Try Local\ first (per-session, no special privileges required),
        # falling back to Global\ if desired.
        for prefix in ("Local\\", "Global\\"):
            handle = kernel32.CreateMutexW(None, False, f"{prefix}{name}")
            err = ctypes.get_last_error()
            if handle:
                if err == ERROR_ALREADY_EXISTS:
                    kernel32.CloseHandle(handle)
                    self.acquired = False
                    return
                self._handle = handle
                self.acquired = True
                import atexit

                atexit.register(self.release)
                return
            if err != ERROR_ACCESS_DENIED:
                break

    def __del__(self) -> None:
        self.release()

    def release(self) -> None:
        if self._handle:
            try:
                kernel32.ReleaseMutex(self._handle)
                kernel32.CloseHandle(self._handle)
            except Exception:
                pass
            self._handle = None
            self.acquired = False

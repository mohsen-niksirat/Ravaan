"""Global low-level keyboard hook (WH_KEYBOARD_LL)."""

from __future__ import annotations

import ctypes
import logging
import queue
import threading
from ctypes import wintypes
from dataclasses import dataclass

from . import winapi as w

log = logging.getLogger(__name__)

# LLKHF_INJECTED — ignore our own SendInput echo
LLKHF_INJECTED = 0x10

_popup_visible = False
_swallow_digits = False

_NAV_VKS = {
    w.VK_ESCAPE,
    w.VK_RETURN,
    w.VK_TAB,
    w.VK_UP,
    w.VK_DOWN,
    w.VK_LEFT,
    w.VK_RIGHT,
}
_DIGIT_VKS = {ord("1"), ord("2"), ord("3"), ord("4"), ord("5")}


@dataclass(frozen=True)
class HookEvent:
    vk_code: int
    flags: int
    scan_code: int
    is_key_down: bool


def set_popup_visible(visible: bool, swallow_digits: bool = True) -> None:
    """When visible, navigation keys (and optionally 1–5) are swallowed."""
    global _popup_visible, _swallow_digits
    _popup_visible = visible
    _swallow_digits = swallow_digits and visible


class KeyboardHook:
    """Installs WH_KEYBOARD_LL on a dedicated thread; events go to a queue only."""

    def __init__(self) -> None:
        self._queue: queue.Queue[HookEvent] = queue.Queue(maxsize=1024)
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._hook = None
        self._proc = None
        self._running = False

    @property
    def events(self) -> queue.Queue[HookEvent]:
        return self._queue

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run, name="ravan-keyboard-hook", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread_id is not None:
            w.user32.PostThreadMessageW(self._thread_id, w.WM_QUIT, 0, 0)
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _emit(self, event: HookEvent) -> None:
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            pass

    def _run(self) -> None:
        self._thread_id = int(w.kernel32.GetCurrentThreadId())
        self._proc = w.HOOKPROC(self._callback)
        hmod = w.kernel32.GetModuleHandleW(None)
        self._hook = w.user32.SetWindowsHookExW(w.WH_KEYBOARD_LL, self._proc, hmod, 0)
        if not self._hook:
            log.error("SetWindowsHookExW failed: %s", ctypes.get_last_error())
            self._running = False
            return
        log.info("Keyboard hook installed")
        msg = wintypes.MSG()
        while self._running:
            ret = w.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret == 0 or ret == -1:
                break
            w.user32.TranslateMessage(ctypes.byref(msg))
            w.user32.DispatchMessageW(ctypes.byref(msg))
        if self._hook:
            w.user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
        log.info("Keyboard hook uninstalled")

    def _callback(self, n_code: int, w_param: int, l_param: int) -> int:
        if n_code == w.HC_ACTION:
            kb = ctypes.cast(l_param, ctypes.POINTER(w.KBDLLHOOKSTRUCT)).contents
            flags = int(kb.flags)
            is_down = w_param in (w.WM_KEYDOWN, w.WM_SYSKEYDOWN)
            event = HookEvent(
                vk_code=int(kb.vkCode),
                flags=flags,
                scan_code=int(kb.scanCode),
                is_key_down=is_down,
            )

            # Never forward injected events into our logic queue for swallow path only;
            # still emit so we can filter injected on the consumer side.
            if flags & LLKHF_INJECTED:
                self._emit(event)
                return int(
                    w.user32.CallNextHookEx(self._hook or 0, n_code, w_param, l_param)
                )

            if _popup_visible and is_down:
                vk = event.vk_code
                if vk in _NAV_VKS or (_swallow_digits and vk in _DIGIT_VKS):
                    self._emit(event)
                    return 1  # swallow — target app must not see these

            self._emit(event)
        return int(w.user32.CallNextHookEx(self._hook or 0, n_code, w_param, l_param))

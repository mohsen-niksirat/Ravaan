"""Caret position via UIA + GetGUIThreadInfo + cursor fallback."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from . import winapi as w

log = logging.getLogger(__name__)

UIA_TextPatternId = 10023
UIA_TextPattern2Id = 10024

_last_caret_source: str = "none"
_uia_failed_until: dict[int, float] = {}
_uia_failed_pids: set[int] = set()
_cached_caret: tuple[CaretRect, str, float] | None = None
_cached_uia_automation = None



@dataclass(frozen=True)
class CaretRect:
    x: int
    y: int
    width: int
    height: int


def get_last_caret_source() -> str:
    """Return the name of the last successful caret detection source."""
    return _last_caret_source


def reset_caret_cache() -> None:
    """Reset cached caret position and UIA cooldown."""
    global _cached_caret, _last_caret_source, _cached_uia_automation
    _cached_caret = None
    _last_caret_source = "none"
    _cached_uia_automation = None
    _uia_failed_until.clear()


def _get_active_pid() -> int:
    try:
        import ctypes
        from ctypes import wintypes

        hwnd = w.user32.GetForegroundWindow()
        if not hwnd:
            return 0
        pid = wintypes.DWORD(0)
        w.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(pid.value)
    except Exception:
        return 0


_mock_caret: tuple[CaretRect, str] | None = None


def set_mock_caret(rect: CaretRect | None, source: str = "mock") -> None:
    """Mock hook for testing caret detection and fallback."""
    global _mock_caret
    if rect is None:
        _mock_caret = None
    else:
        _mock_caret = (rect, source)


def get_caret_rect_with_source() -> tuple[CaretRect, str]:
    """Return the caret rect and detection source ('UIA', 'GetGUIThreadInfo', or 'cursor')."""
    global _last_caret_source, _cached_caret

    if _mock_caret is not None:
        return _mock_caret[0], _mock_caret[1]

    now = time.monotonic()
    if _cached_caret is not None and (now - _cached_caret[2]) < 0.030:
        return _cached_caret[0], _cached_caret[1]

    active_pid = _get_active_pid()
    rect = None
    # Skip UIA if this PID recently failed UIA within cooldown
    if active_pid not in _uia_failed_until or now > _uia_failed_until[active_pid]:
        rect = _try_uia_caret()
        if rect is not None and (-10000 <= rect.x <= 50000) and (-10000 <= rect.y <= 50000):
            _uia_failed_until.pop(active_pid, None)
            _last_caret_source = "UIA"
            _cached_caret = (rect, "UIA", now)
            return rect, "UIA"
        else:
            if active_pid:
                _uia_failed_until[active_pid] = now + 3.0

    # UIA was unavailable for this active window. Log once per process ID.
    if active_pid and active_pid not in _uia_failed_pids:
        _uia_failed_pids.add(active_pid)
        if len(_uia_failed_pids) > 100:
            _uia_failed_pids.pop()
        from ravan.platform.focus import foreground_exe

        exe = foreground_exe() or "app"
        log.info(
            "UIA caret detection unavailable for %s (PID %d); falling back to GetGUIThreadInfo/cursor",
            exe,
            active_pid,
        )

    rect = _try_gui_thread_info()
    if rect is not None and (-10000 <= rect.x <= 50000) and (-10000 <= rect.y <= 50000):
        _last_caret_source = "GetGUIThreadInfo"
        _cached_caret = (rect, "GetGUIThreadInfo", now)
        log.debug("Caret via GetGUIThreadInfo: %s", rect)
        return rect, "GetGUIThreadInfo"

    rect = _cursor_position()
    _last_caret_source = "cursor"
    _cached_caret = (rect, "cursor", now)
    log.debug("Caret via cursor: %s", rect)
    return rect, "cursor"


def get_caret_rect() -> CaretRect:
    rect, _ = get_caret_rect_with_source()
    return rect


def _rects_to_caret(rects) -> CaretRect | None:
    if not rects or len(rects) < 4:
        return None
    left, top, width, height = rects[0], rects[1], rects[2], rects[3]
    # Filter out whole-window/container bounding boxes (e.g. terminals, canvases)
    if width > 600 or height > 250:
        return None
    # Filter out degenerate (0, 0) rects
    if left == 0 and top == 0 and (width <= 2 or height <= 2):
        return None
    if width <= 0:  # empty selection → caret line
        width = 2
    if height <= 0:
        height = 16
    return CaretRect(x=int(left), y=int(top), width=int(width), height=int(height))


def _pattern_ok(pattern) -> bool:
    return pattern is not None and bool(pattern)


def _try_uia_caret() -> CaretRect | None:
    """UIA: focused element (or nearest text ancestor) → caret/selection rect."""
    try:
        import comtypes
        import comtypes.client
        from comtypes.gen import UIAutomationClient as UIA
    except Exception:  # noqa: BLE001 — comtypes/gen may not be generated yet
        try:
            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen import UIAutomationClient as UIA  # type: ignore
        except Exception:  # noqa: BLE001
            return None

    try:
        import comtypes

        comtypes.CoInitialize()
    except Exception:
        pass

    global _cached_uia_automation
    try:
        if _cached_uia_automation is None:
            _cached_uia_automation = comtypes.client.CreateObject(
                UIA.CUIAutomation, interface=UIA.IUIAutomation
            )
        automation = _cached_uia_automation
        element = automation.GetFocusedElement()
        if element is None:
            return None

        # 1) Direct TextPattern2 on focused element
        rect = _caret_from_element(element, UIA)
        if rect is not None:
            return rect

        # 2) Walk ancestors looking for a text-enabled element (Firefox, Chrome…)
        try:
            walker = automation.ControlViewWalker
        except Exception:  # noqa: BLE001
            return None
        current = element
        for _ in range(10):
            try:
                parent = walker.GetParentElement(current)
            except Exception:  # noqa: BLE001
                return None
            if parent is None:
                return None
            rect = _caret_from_element(parent, UIA)
            if rect is not None:
                return rect
            current = parent
        return None
    except Exception:  # noqa: BLE001 — UIA is best-effort
        _cached_uia_automation = None
        return None


def _caret_from_element(element, UIA) -> CaretRect | None:
    try:
        pattern = element.GetCurrentPattern(UIA_TextPattern2Id)
        if _pattern_ok(pattern):
            pattern2 = pattern.QueryInterface(UIA.IUIAutomationTextPattern2)
            result = pattern2.GetCaretRange()
            caret_range = result[-1] if isinstance(result, tuple) else result
            if caret_range is not None and bool(caret_range):
                rects = caret_range.GetBoundingRectangles()
                caret = _rects_to_caret(rects)
                if caret is not None:
                    return caret
    except Exception:  # noqa: BLE001
        pass
    try:
        pattern = element.GetCurrentPattern(UIA_TextPatternId)
        if _pattern_ok(pattern):
            text_pattern = pattern.QueryInterface(UIA.IUIAutomationTextPattern)
            selections = text_pattern.GetSelection()
            if selections is not None:
                count = selections.Length if hasattr(selections, "Length") else 0
                if count > 0:
                    rng = selections.GetElement(0)
                    rects = rng.GetBoundingRectangles()
                    caret = _rects_to_caret(rects)
                    if caret is not None:
                        return caret
    except Exception:  # noqa: BLE001
        pass
    return None


def _try_gui_thread_info() -> CaretRect | None:
    import ctypes

    hwnd = w.user32.GetForegroundWindow()
    if not hwnd:
        return None
    thread_id = w.user32.GetWindowThreadProcessId(hwnd, None)
    own_tid = w.kernel32.GetCurrentThreadId()
    attached = False
    if thread_id != own_tid:
        attached = bool(w.user32.AttachThreadInput(own_tid, thread_id, True))

    try:
        info = w.GUITHREADINFO()
        info.cbSize = ctypes.sizeof(w.GUITHREADINFO)
        result = None
        if w.user32.GetGUIThreadInfo(thread_id, ctypes.byref(info)):
            caret = info.rcCaret
            hwnd_caret = info.hwndCaret
            if (
                hwnd_caret
                and not (
                    caret.left == 0
                    and caret.top == 0
                    and caret.right == 0
                    and caret.bottom == 0
                )
            ):
                pt = w.POINT(caret.left, caret.top)
                if w.user32.ClientToScreen(hwnd_caret, ctypes.byref(pt)):
                    width = caret.right - caret.left
                    height = caret.bottom - caret.top
                    if height <= 0:
                        height = 16
                    if width <= 0:
                        width = 2
                    result = CaretRect(x=pt.x, y=pt.y, width=width, height=height)
        return result
    finally:
        if attached:
            w.user32.AttachThreadInput(own_tid, thread_id, False)


def _cursor_position() -> CaretRect:
    import ctypes

    pt = w.POINT()
    w.user32.GetCursorPos(ctypes.byref(pt))
    return CaretRect(x=pt.x, y=pt.y, width=2, height=16)

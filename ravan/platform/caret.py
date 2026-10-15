"""Caret position via UIA + GetGUIThreadInfo + cursor fallback."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from . import winapi as w

log = logging.getLogger(__name__)

UIA_TextPatternId = 10023
UIA_TextPattern2Id = 10024


@dataclass(frozen=True)
class CaretRect:
    x: int
    y: int
    width: int
    height: int


def get_caret_rect() -> CaretRect:
    rect = _try_uia_caret()
    if rect is not None:
        log.debug("Caret via UIA: %s", rect)
        return rect
    rect = _try_gui_thread_info()
    if rect is not None:
        log.debug("Caret via GetGUIThreadInfo: %s", rect)
        return rect
    rect = _cursor_position()
    log.debug("Caret via cursor: %s", rect)
    return rect


def _rects_to_caret(rects) -> CaretRect | None:
    if not rects or len(rects) < 4:
        return None
    left, top, width, height = rects[0], rects[1], rects[2], rects[3]
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
        automation = comtypes.client.CreateObject(
            UIA.CUIAutomation, interface=UIA.IUIAutomation
        )
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

    info = w.GUITHREADINFO()
    info.cbSize = ctypes.sizeof(w.GUITHREADINFO)
    result = None
    if w.user32.GetGUIThreadInfo(thread_id, ctypes.byref(info)):
        caret = info.rcCaret
        hwnd_caret = info.hwndCaret
        if hwnd_caret:
            pt = w.POINT(caret.left, caret.top)
            w.user32.ClientToScreen(hwnd_caret, ctypes.byref(pt))
            width = caret.right - caret.left
            height = caret.bottom - caret.top
            if height <= 0:
                height = 16
            if width <= 0:
                width = 2
            result = CaretRect(x=pt.x, y=pt.y, width=width, height=height)

    if attached:
        w.user32.AttachThreadInput(own_tid, thread_id, False)
    return result


def _cursor_position() -> CaretRect:
    import ctypes

    pt = w.POINT()
    w.user32.GetCursorPos(ctypes.byref(pt))
    return CaretRect(x=pt.x, y=pt.y, width=2, height=16)

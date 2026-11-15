"""Win32 DWM Acrylic/Mica window decorations, multi-monitor clamping, and Toplevel lifecycle."""

from __future__ import annotations

import ctypes
import logging
import sys
import tkinter as tk
from typing import Any

from ravan.ui.theme_palettes import Palette, get_active_palette

log = logging.getLogger(__name__)


def _hex_to_colorref(hex_color: str) -> int | None:
    """Convert '#rrggbb' to a Windows COLORREF (0x00bbggrr)."""
    try:
        rgb = int(hex_color.lstrip("#"), 16)
        return ((rgb & 0xFF) << 16) | (rgb & 0xFF00) | ((rgb >> 16) & 0xFF)
    except (ValueError, AttributeError):
        return None


def _set_window_composition_accent(hwnd: int, accent_state: int, gradient_color: int = 0) -> bool:
    """Invoke Win32 SetWindowCompositionAttribute with explicit ctypes HWND signature."""
    from ctypes import wintypes

    class ACCENT_POLICY(ctypes.Structure):
        _fields_ = [
            ("AccentState", ctypes.c_int),
            ("AccentFlags", ctypes.c_int),
            ("GradientColor", ctypes.c_uint),
            ("AnimationId", ctypes.c_int),
        ]

    class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
        _fields_ = [
            ("dwAttribute", ctypes.c_int),
            ("pData", ctypes.c_void_p),
            ("cbData", ctypes.c_size_t),
        ]

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    fn = user32.SetWindowCompositionAttribute
    fn.argtypes = [wintypes.HWND, ctypes.c_void_p]
    fn.restype = wintypes.BOOL

    policy = ACCENT_POLICY(accent_state, 0, gradient_color, 0)
    data = WINDOWCOMPOSITIONATTRIBDATA(
        19,
        ctypes.cast(ctypes.byref(policy), ctypes.c_void_p),
        ctypes.sizeof(policy),
    )
    return bool(fn(wintypes.HWND(hwnd), ctypes.byref(data)))


def _set_dwm_attribute(hwnd: int, attribute: int, value: Any) -> int:
    """Invoke Win32 DwmSetWindowAttribute with explicit ctypes HWND signature."""
    from ctypes import wintypes

    dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
    fn = dwmapi.DwmSetWindowAttribute
    fn.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    fn.restype = ctypes.c_long
    return int(fn(wintypes.HWND(hwnd), attribute, ctypes.byref(value), ctypes.sizeof(value)))


def _enable_acrylic_blur(hwnd: int, hex_color: str) -> bool:
    """Enable acrylic blur-behind behind a popup window (SetWindowCompositionAttribute)."""
    try:
        rgb = int(hex_color.lstrip("#"), 16)
        r, g, b = (rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF
        tint = (0xC8 << 24) | (b << 16) | (g << 8) | r  # ABGR with ~78% opacity
        _set_window_composition_accent(hwnd, 0, 0)
        return _set_window_composition_accent(hwnd, 4, tint)
    except Exception as exc:  # noqa: BLE001
        log.debug("Acrylic blur unavailable: %s", exc)
        return False


def _disable_acrylic_blur(hwnd: int) -> None:
    """Remove any acrylic accent previously applied to the window."""
    try:
        _set_window_composition_accent(hwnd, 0, 0)
    except Exception:  # noqa: BLE001
        pass


def apply_popup_window_attributes(
    win: tk.Tk | tk.Toplevel,
    palette: Palette,
    show: bool = False,
    acrylic: bool = False,
    border_color: str | None = None,
    corner_radius: float = 8.0,
) -> dict[str, bool]:
    """Apply unified frameless, topmost, opacity, and DWM rounded corners to a popup window."""
    result = {"acrylic": False}
    win.attributes("-topmost", True)
    win.overrideredirect(True)
    try:
        win.attributes("-alpha", palette.alpha)
    except tk.TclError:
        pass

    if sys.platform != "win32":
        return result

    try:
        from ravan.platform import winapi as wapi

        hwnd = win.winfo_id()
        root_hwnd = int(wapi.user32.GetAncestor(hwnd, 2) or hwnd)
        if not root_hwnd:
            return result

        # WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
        style = wapi.user32.GetWindowLongW(root_hwnd, -20)
        wapi.user32.SetWindowLongW(root_hwnd, -20, style | 0x08000088)
        wapi.user32.SetWindowPos(root_hwnd, -1, 0, 0, 0, 0, 0x0037)
        if show:
            wapi.user32.ShowWindow(root_hwnd, wapi.SW_SHOWNOACTIVATE)

        if corner_radius <= 0:
            corner_val = 1
        elif corner_radius <= 6:
            corner_val = 3
        else:
            corner_val = 2
        corner_pref = ctypes.c_int(corner_val)
        _set_dwm_attribute(root_hwnd, 33, corner_pref)

        if border_color:
            cref = _hex_to_colorref(border_color)
            if cref is not None:
                val = ctypes.c_uint(cref)
                _set_dwm_attribute(root_hwnd, 34, val)

        if acrylic:
            result["acrylic"] = _enable_acrylic_blur(root_hwnd, palette.bg)
        else:
            _disable_acrylic_blur(root_hwnd)
        return result
    except Exception:
        return result


def rects_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    """Return True when two screen-space rectangles (x1, y1, x2, y2) intersect."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


def clamp_popup_position(
    win: tk.Tk | tk.Toplevel,
    px: int,
    py: int,
    width: int,
    height: int,
    margin: int = 10,
) -> tuple[int, int]:
    """Clamp popup top-left coordinates safely inside the target monitor's work area."""
    if sys.platform == "win32":
        try:
            from ravan.platform.winapi import get_monitor_work_area

            m_left, m_top, m_right, m_bottom = get_monitor_work_area(px, py)
            if (m_right - m_left) >= 320 and (m_bottom - m_top) >= 240:
                return (
                    max(m_left + margin, min(px, m_right - width - margin)),
                    max(m_top + margin, min(py, m_bottom - height - margin)),
                )
        except Exception:
            pass
    try:
        sw = max(320, int(win.winfo_screenwidth()))
        sh = max(240, int(win.winfo_screenheight()))
    except Exception:
        return max(margin, px), max(margin, py)
    return max(margin, min(px, sw - width - margin)), max(margin, min(py, sh - height - margin))


def resolve_popup_position(
    win: tk.Tk | tk.Toplevel,
    px: int,
    py: int,
    width: int,
    height: int,
    avoid_rects: list[tuple[int, int, int, int]] | tuple[tuple[int, int, int, int], ...] = (),
) -> tuple[int, int]:
    """Clamp (px, py) to screen and shift vertically away from any overlapping popups."""
    cx, cy = clamp_popup_position(win, px, py, width, height)
    for rect in avoid_rects:
        if rects_overlap((cx, cy, cx + width, cy + height), rect):
            _ax1, ay1, _ax2, ay2 = rect
            above_y = ay1 - height - 8
            candidate_y = above_y if above_y >= 10 else ay2 + 8
            cx, cy = clamp_popup_position(win, cx, candidate_y, width, height)
    return cx, cy


def apply_window_decorations(win: tk.Tk | tk.Toplevel, palette: Palette | None = None) -> None:
    """Apply native Windows 11 Fluent dark/light title bar, Mica backdrop, and rounded corners."""
    if palette is None:
        palette = get_active_palette()
    try:
        win.configure(bg=palette.bg)
    except Exception:
        pass

    if sys.platform != "win32":
        return

    try:
        from ravan.platform import winapi as wapi

        win.update_idletasks()
        hwnd = win.winfo_id()
        root_hwnd = int(wapi.user32.GetAncestor(hwnd, 2) or hwnd)
        if not root_hwnd:
            return

        # 1. Immersive dark mode (DWMWA_USE_IMMERSIVE_DARK_MODE = 20, fallback 19)
        is_dark = 1 if palette.name in ("dark", "high_contrast") else 0
        val = ctypes.c_int(is_dark)
        res = _set_dwm_attribute(root_hwnd, 20, val)
        if res != 0:
            _set_dwm_attribute(root_hwnd, 19, val)

        # 2. Window corner preference (DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_ROUND = 2)
        corner_pref = ctypes.c_int(2)
        _set_dwm_attribute(root_hwnd, 33, corner_pref)
    except Exception as exc:
        log.debug("apply_window_decorations error: %s", exc)


def _resolve_live_tk_parent(parent: tk.Misc | None) -> tk.Misc | None:
    """Return `parent` or `tk._default_root` only if its Tcl/Tk interpreter is still alive."""
    for candidate in (parent, getattr(tk, "_default_root", None)):
        if candidate is None:
            continue
        try:
            if candidate.winfo_exists():
                return candidate
        except (tk.TclError, RuntimeError):
            continue
    return None


def create_managed_toplevel(parent: tk.Misc | None = None) -> tuple[tk.Toplevel, tk.Tk | None]:
    """Create a Toplevel attached to a live root, or spawn a dedicated hidden root to own and clean up."""
    live_parent = _resolve_live_tk_parent(parent)
    if live_parent is not None:
        return tk.Toplevel(live_parent), None
    owned_root = tk.Tk()
    owned_root.withdraw()
    return tk.Toplevel(owned_root), owned_root


def destroy_managed_toplevel(toplevel: tk.Misc | None, owned_root: tk.Tk | None) -> None:
    """Flush pending idle callbacks and destroy a managed Toplevel plus any owned hidden root."""
    for win in (toplevel, owned_root):
        if win is None:
            continue
        try:
            win.update_idletasks()
        except (tk.TclError, RuntimeError):
            pass
        try:
            win.destroy()
        except (tk.TclError, RuntimeError):
            pass

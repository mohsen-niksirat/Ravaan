"""Virtual-key helpers: Unicode translation and hotkey matching."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from ravan.core.config import HotkeySpec

from . import winapi as w

_MODIFIER_VKS = {
    "alt": w.VK_MENU,
    "ctrl": w.VK_CONTROL,
    "control": w.VK_CONTROL,
    "shift": w.VK_SHIFT,
    "win": w.VK_LWIN,
}

_KEY_NAME_TO_VK = {
    "f12": w.VK_F12,
    "escape": w.VK_ESCAPE,
    "esc": w.VK_ESCAPE,
    "enter": w.VK_RETURN,
    "return": w.VK_RETURN,
    "tab": w.VK_TAB,
    "space": w.VK_SPACE,
    "up": w.VK_UP,
    "down": w.VK_DOWN,
    "left": w.VK_LEFT,
    "right": w.VK_RIGHT,
}


def key_name_to_vk(name: str) -> int | None:
    lower = name.strip().lower()
    if lower in _KEY_NAME_TO_VK:
        return _KEY_NAME_TO_VK[lower]
    if len(lower) == 1:
        ch = lower.upper()
        # ASCII letters / digits map to their VK codes
        return ord(ch)
    if lower.startswith("f") and lower[1:].isdigit():
        n = int(lower[1:])
        if 1 <= n <= 24:
            return 0x70 + (n - 1)
    return None


_ALL_MODS = ("alt", "ctrl", "shift", "win")


def modifiers_down(modifiers: list[str], exact: bool = True) -> bool:
    expected = {m.lower() for m in modifiers}
    if "control" in expected:
        expected.remove("control")
        expected.add("ctrl")

    for mod in _ALL_MODS:
        vk = _MODIFIER_VKS.get(mod)
        if vk is None:
            continue
        down = bool(w.user32.GetAsyncKeyState(vk) & 0x8000)
        if mod == "win":
            down = down or bool(w.user32.GetAsyncKeyState(w.VK_RWIN) & 0x8000)

        if exact:
            if down != (mod in expected):
                return False
        else:
            if (mod in expected) and not down:
                return False
    return True


def matches_hotkey(vk: int, spec: HotkeySpec) -> bool:
    expected = key_name_to_vk(spec.key)
    if expected is None or vk != expected:
        return False
    return modifiers_down(spec.modifiers, exact=True)



def vk_to_unicode(vk: int, scan_code: int = 0) -> str | None:
    """Translate a VK to a Unicode character using the foreground keyboard layout."""
    if vk in (
        w.VK_SHIFT,
        w.VK_CONTROL,
        w.VK_MENU,
        w.VK_LWIN,
        w.VK_RWIN,
        w.VK_TAB,
        w.VK_RETURN,
        w.VK_ESCAPE,
        w.VK_BACK,
        w.VK_UP,
        w.VK_DOWN,
        w.VK_LEFT,
        w.VK_RIGHT,
    ):
        return None
    if 0x70 <= vk <= 0x87:  # F-keys
        return None

    state = (wintypes.BYTE * 256)()
    w.user32.GetKeyboardState(state)
    hwnd = w.user32.GetForegroundWindow()
    thread_id = w.user32.GetWindowThreadProcessId(hwnd, None) if hwnd else 0
    hkl = w.user32.GetKeyboardLayout(thread_id)
    buf = ctypes.create_unicode_buffer(8)
    result = w.user32.ToUnicodeEx(vk, scan_code, state, buf, 8, 0, hkl)
    if result <= 0:
        return None
    return buf.value[:result]


def is_modifier(vk: int) -> bool:
    return vk in (
        w.VK_SHIFT,
        w.VK_LSHIFT if hasattr(w, "VK_LSHIFT") else w.VK_SHIFT,
        w.VK_CONTROL,
        w.VK_MENU,
        w.VK_LWIN,
        w.VK_RWIN,
    )

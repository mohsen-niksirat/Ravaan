"""Virtual-key helpers: Unicode translation and hotkey matching."""

from __future__ import annotations

import ctypes

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
    "pause": w.VK_PAUSE,
    "break": w.VK_PAUSE,
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
    if w.user32 is None:
        return False
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


def matches_hotkey(
    vk: int, spec: HotkeySpec, held_modifiers: frozenset[str] | None = None
) -> bool:
    expected = key_name_to_vk(spec.key)
    if expected is None or vk != expected:
        return False
    if held_modifiers is not None:
        norm_expected = {
            "ctrl" if m.lower() == "control" else m.lower() for m in spec.modifiers
        }
        return held_modifiers == norm_expected
    return modifiers_down(spec.modifiers, exact=True)



def _foreground_keyboard_state():
    """Build a 256-byte keyboard state array synced with live hardware/toggle keys."""
    state = (ctypes.c_ubyte * 256)()
    w.user32.GetKeyboardState(state)

    def _sync_down(vk_code: int) -> bool:
        down = bool(w.user32.GetAsyncKeyState(vk_code) & 0x8000)
        state[vk_code] = 0x80 if down else 0x00
        return down

    lshift = _sync_down(w.VK_LSHIFT)
    rshift = _sync_down(w.VK_RSHIFT)
    shift = bool(w.user32.GetAsyncKeyState(w.VK_SHIFT) & 0x8000) or lshift or rshift
    state[w.VK_SHIFT] = 0x80 if shift else 0x00

    lctrl = _sync_down(w.VK_LCONTROL)
    rctrl = _sync_down(w.VK_RCONTROL)
    ctrl = bool(w.user32.GetAsyncKeyState(w.VK_CONTROL) & 0x8000) or lctrl or rctrl
    state[w.VK_CONTROL] = 0x80 if ctrl else 0x00

    lalt = _sync_down(w.VK_LMENU)
    ralt = _sync_down(w.VK_RMENU)
    alt = bool(w.user32.GetAsyncKeyState(w.VK_MENU) & 0x8000) or lalt or ralt
    state[w.VK_MENU] = 0x80 if alt else 0x00

    caps_vk = getattr(w, "VK_CAPITAL", 0x14)
    caps_on = bool(w.user32.GetKeyState(caps_vk) & 0x0001)
    state[caps_vk] = (state[caps_vk] & 0xFE) | (0x01 if caps_on else 0x00)
    return state


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

    state = _foreground_keyboard_state()
    hwnd = w.user32.GetForegroundWindow()
    thread_id = w.user32.GetWindowThreadProcessId(hwnd, None) if hwnd else 0
    hkl = w.user32.GetKeyboardLayout(thread_id)
    buf = ctypes.create_unicode_buffer(8)
    # Bit 2 (0x4, Windows 10 1607+) avoids mutating foreground dead-key state.
    result = w.user32.ToUnicodeEx(vk, scan_code, state, buf, 8, 0x04, hkl)
    if result <= 0:
        return None
    return buf.value[:result]


def is_modifier(vk: int) -> bool:
    return vk in (
        w.VK_SHIFT,
        getattr(w, "VK_LSHIFT", w.VK_SHIFT),
        getattr(w, "VK_RSHIFT", w.VK_SHIFT),
        w.VK_CONTROL,
        getattr(w, "VK_LCONTROL", w.VK_CONTROL),
        getattr(w, "VK_RCONTROL", w.VK_CONTROL),
        w.VK_MENU,
        getattr(w, "VK_LMENU", w.VK_MENU),
        getattr(w, "VK_RMENU", w.VK_MENU),
        w.VK_LWIN,
        w.VK_RWIN,
    )

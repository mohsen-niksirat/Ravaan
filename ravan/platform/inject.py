"""Text injection via SendInput (Unicode events)."""

from __future__ import annotations

import ctypes
import logging

from . import winapi as w

log = logging.getLogger(__name__)


def _unicode_input(code_unit: int, key_up: bool) -> w.INPUT:
    flags = w.KEYEVENTF_UNICODE
    if key_up:
        flags |= w.KEYEVENTF_KEYUP
    inp = w.INPUT()
    inp.type = w.INPUT_KEYBOARD
    inp.union.ki = w.KEYBDINPUT(
        wVk=0,
        wScan=code_unit,
        dwFlags=flags,
        time=0,
        dwExtraInfo=0,
    )
    return inp


def _vk_input(vk: int, key_up: bool) -> w.INPUT:
    flags = w.KEYEVENTF_KEYUP if key_up else 0
    inp = w.INPUT()
    inp.type = w.INPUT_KEYBOARD
    inp.union.ki = w.KEYBDINPUT(
        wVk=vk,
        wScan=0,
        dwFlags=flags,
        time=0,
        dwExtraInfo=0,
    )
    return inp


def _char_to_inputs(ch: str) -> list[w.INPUT]:
    """Convert a single character to low-level Windows keyboard inputs."""
    if ch == "\r":
        return []
    if ch == "\n":
        return [
            _vk_input(w.VK_RETURN, False),
            _vk_input(w.VK_RETURN, True),
        ]
    code = ord(ch)
    # Surrogate pairs for non-BMP
    if code > 0xFFFF:
        code -= 0x10000
        high = 0xD800 + (code >> 10)
        low = 0xDC00 + (code & 0x3FF)
        return [
            _unicode_input(high, False),
            _unicode_input(high, True),
            _unicode_input(low, False),
            _unicode_input(low, True),
        ]
    return [
        _unicode_input(code, False),
        _unicode_input(code, True),
    ]


def inject_text(text: str) -> None:
    if not text:
        return
    log.debug("Injecting text: %r", text)
    inputs: list[w.INPUT] = []
    for ch in text:
        inputs.extend(_char_to_inputs(ch))
    arr = (w.INPUT * len(inputs))(*inputs)
    w.user32.SendInput(len(inputs), arr, ctypes.sizeof(w.INPUT))


def inject_backspaces(n: int) -> None:
    if n <= 0:
        return
    log.debug("Injecting %s backspaces", n)
    inputs: list[w.INPUT] = []
    for _ in range(n):
        inputs.append(_vk_input(w.VK_BACK, False))
        inputs.append(_vk_input(w.VK_BACK, True))
    arr = (w.INPUT * len(inputs))(*inputs)
    w.user32.SendInput(len(inputs), arr, ctypes.sizeof(w.INPUT))


def inject_left_arrows(n: int) -> None:
    if n <= 0:
        return
    log.debug("Injecting %s left arrows", n)
    inputs: list[w.INPUT] = []
    for _ in range(n):
        inputs.append(_vk_input(w.VK_LEFT, False))
        inputs.append(_vk_input(w.VK_LEFT, True))
    arr = (w.INPUT * len(inputs))(*inputs)
    w.user32.SendInput(len(inputs), arr, ctypes.sizeof(w.INPUT))


def replace_last_n_with(
    delete_n: int, new_text: str, cursor_offset: int | None = None
) -> None:
    inputs: list[w.INPUT] = []
    for _ in range(max(0, delete_n)):
        inputs.append(_vk_input(w.VK_BACK, False))
        inputs.append(_vk_input(w.VK_BACK, True))
    for ch in new_text:
        inputs.extend(_char_to_inputs(ch))
    if cursor_offset is not None and cursor_offset > 0:
        for _ in range(cursor_offset):
            inputs.append(_vk_input(w.VK_LEFT, False))
            inputs.append(_vk_input(w.VK_LEFT, True))
    if inputs:
        arr = (w.INPUT * len(inputs))(*inputs)
        w.user32.SendInput(len(inputs), arr, ctypes.sizeof(w.INPUT))



def send_shortcut(modifiers: list[int], key_vk: int) -> None:
    """Send a key combination (e.g. Ctrl+C or Ctrl+V)."""
    inputs: list[w.INPUT] = []
    for mod in modifiers:
        inputs.append(_vk_input(mod, False))
    inputs.append(_vk_input(key_vk, False))
    inputs.append(_vk_input(key_vk, True))
    for mod in reversed(modifiers):
        inputs.append(_vk_input(mod, True))
    arr = (w.INPUT * len(inputs))(*inputs)
    w.user32.SendInput(len(inputs), arr, ctypes.sizeof(w.INPUT))

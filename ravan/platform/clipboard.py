"""Thread-safe Win32 clipboard reader and writer."""

from __future__ import annotations

import ctypes
import logging
import sys
import time
from ctypes import wintypes

log = logging.getLogger(__name__)

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

if sys.platform == "win32":
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.restype = wintypes.HGLOBAL

    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
else:
    user32 = None
    kernel32 = None


def _open_clipboard(retries: int = 5, delay: float = 0.01) -> bool:
    if user32 is None:
        return False
    for _ in range(retries):
        if user32.OpenClipboard(None):
            return True
        time.sleep(delay)
    return False


def get_clipboard_text() -> str | None:
    """Read plain Unicode text from clipboard if available."""
    if not _open_clipboard():
        return None
    try:
        h_mem = user32.GetClipboardData(CF_UNICODETEXT)
        if not h_mem:
            return None
        ptr = kernel32.GlobalLock(h_mem)
        if not ptr:
            return None
        try:
            return ctypes.c_wchar_p(ptr).value
        finally:
            kernel32.GlobalUnlock(h_mem)
    finally:
        user32.CloseClipboard()


def set_clipboard_text(text: str) -> bool:
    """Write Unicode text to clipboard."""
    if not _open_clipboard():
        return False
    try:
        if not user32.EmptyClipboard():
            return False
        # Calculate buffer size in bytes including null terminator
        raw = text.encode("utf-16-le") + b"\x00\x00"
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(raw))
        if not h_mem:
            return False
        ptr = kernel32.GlobalLock(h_mem)
        if not ptr:
            kernel32.GlobalFree(h_mem)
            return False
        ctypes.memmove(ptr, raw, len(raw))
        kernel32.GlobalUnlock(h_mem)
        if not user32.SetClipboardData(CF_UNICODETEXT, h_mem):
            kernel32.GlobalFree(h_mem)
            return False
        return True
    finally:
        user32.CloseClipboard()


def try_convert_selection(converter) -> bool:
    """Attempt to convert currently selected text in the active app.

    Returns True if text was selected, converted, and pasted.
    Returns False if no selection was present.
    """
    if sys.platform != "win32":
        return False

    from ravan.platform import winapi as w
    from ravan.platform.inject import send_shortcut

    old_clip = get_clipboard_text()

    # Clear clipboard temporarily with an empty or unique marker so we know if copy succeeded
    sentinel = f"__ravan_sel_check_{time.monotonic()}__"
    if not set_clipboard_text(sentinel):
        return False

    # Send Ctrl+C
    send_shortcut([w.VK_CONTROL], ord("C"))
    # Wait for the active application to populate clipboard
    time.sleep(0.04)

    new_clip = get_clipboard_text()
    if new_clip is None or new_clip == sentinel or not new_clip.strip():
        # Nothing was selected; restore previous clipboard if needed
        if old_clip is not None:
            set_clipboard_text(old_clip)
        return False

    # We got selected text! Convert it
    converted = converter(new_clip)
    if not converted or converted == new_clip:
        if old_clip is not None:
            set_clipboard_text(old_clip)
        return False

    set_clipboard_text(converted)
    # Paste converted text over selection
    send_shortcut([w.VK_CONTROL], ord("V"))
    time.sleep(0.04)
    return True


def set_clipboard_image(image_path: str) -> bool:
    """Load an image file and place it on the Windows clipboard (CF_DIB)."""
    if sys.platform != "win32" or user32 is None or kernel32 is None:
        return False
    from pathlib import Path

    img = Path(image_path)
    if not img.is_file():
        return False

    try:
        import io

        from PIL import Image

        with Image.open(img) as image, io.BytesIO() as output:
            image.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]  # Skip 14-byte BMP header to obtain CF_DIB

        CF_DIB = 8
        if not _open_clipboard():
            return False
        try:
            user32.EmptyClipboard()
            h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if not h_mem:
                return False
            ptr = kernel32.GlobalLock(h_mem)
            if not ptr:
                kernel32.GlobalFree(h_mem)
                return False
            ctypes.memmove(ptr, data, len(data))
            kernel32.GlobalUnlock(h_mem)
            res = user32.SetClipboardData(CF_DIB, h_mem)
            if not res:
                kernel32.GlobalFree(h_mem)
                return False
            return True
        finally:
            user32.CloseClipboard()
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to copy image to clipboard: %s", exc)
        return False


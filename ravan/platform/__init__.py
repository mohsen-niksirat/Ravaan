"""Windows platform bindings for Ravan."""

from __future__ import annotations

import sys

if sys.platform == "win32":
    from .caret import CaretRect, get_caret_rect
    from .focus import foreground_exe, window_title
    from .hook import HookEvent, KeyboardHook, set_popup_visible
    from .inject import inject_backspaces, inject_text, replace_last_n_with
    from .lang import current_language, hkl_to_language_info
    from .singleinstance import SingleInstance
    from .startup import is_startup_enabled, set_startup

    __all__ = [
        "CaretRect",
        "get_caret_rect",
        "HookEvent",
        "KeyboardHook",
        "set_popup_visible",
        "inject_backspaces",
        "inject_text",
        "replace_last_n_with",
        "current_language",
        "hkl_to_language_info",
        "foreground_exe",
        "window_title",
        "SingleInstance",
        "is_startup_enabled",
        "set_startup",
    ]
else:
    __all__ = []

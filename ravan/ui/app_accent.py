"""Quick Accent (Persian Letter Picker) mixin for RavanApp."""

from __future__ import annotations

import logging
import time
from typing import Any

from ravan.core.accent import AccentEngine
from ravan.platform import winapi as w
from ravan.platform.caret import get_caret_rect
from ravan.platform.focus import is_fullscreen_focused
from ravan.platform.hook import set_popup_visible
from ravan.platform.inject import replace_last_n_with
from ravan.ui.accent_bar import AccentBarWindow

log = logging.getLogger(__name__)


class AppAccentMixin:
    """Mixin providing Quick Accent key-hold tracking and UI popup management."""

    def _init_accent(self: Any) -> None:
        if getattr(self.cfg, "quick_accent_enabled", False):
            hold_ms = getattr(self.cfg, "quick_accent_hold_ms", 300)
            self.accent = AccentEngine(hold_ms=hold_ms)
            self.accent_bar = AccentBarWindow(
                parent=getattr(self.overlay, "_root", None),
                theme_mode=getattr(self.cfg, "theme_mode", "auto"),
            )
        else:
            self.accent = None
            self.accent_bar = None

    def _handle_accent_key(self: Any, event: Any, vk: int, char: str) -> bool:
        """Handle accent picker active navigation or key-hold trigger. Returns True if swallowed."""
        if not getattr(self, "accent", None) or not self.cfg.quick_accent_enabled:
            return False

        # If accent bar is currently visible, handle selection keys
        if self.accent.is_active:
            if vk == w.VK_ESCAPE:
                self._dismiss_accent()
                return True

            if vk in (w.VK_LEFT, w.VK_UP):
                idx = self.accent.move_selection(-1)
                if self.accent_bar:
                    self.accent_bar.update_selection(idx)
                return True

            if vk in (w.VK_RIGHT, w.VK_DOWN):
                idx = self.accent.move_selection(1)
                if self.accent_bar:
                    self.accent_bar.update_selection(idx)
                return True

            if vk in (w.VK_RETURN, w.VK_SPACE):
                chosen = self.accent.accept_current()
                if chosen:
                    self._suppress_until = time.monotonic() + 0.05
                    replace_last_n_with(1, chosen)
                    self.journal.pop_last_n_chars(1)
                    self.journal.push(chosen)
                self._dismiss_accent()
                return True

            if ord("1") <= vk <= ord("9"):
                digit = vk - ord("0")
                chosen = self.accent.select_digit(digit)
                if chosen:
                    self._suppress_until = time.monotonic() + 0.05
                    replace_last_n_with(1, chosen)
                    self.journal.pop_last_n_chars(1)
                    self.journal.push(chosen)
                self._dismiss_accent()
                return True

            # Any other key dismisses the accent bar and passes through
            self._dismiss_accent()
            return False

        # Suppress accent hold in fullscreen (games, movies)
        if is_fullscreen_focused():
            return False

        # Key-hold detection
        if char:
            now = time.monotonic()
            variants = self.accent.on_key_down(vk, char, now)
            if variants and self.accent_bar:
                caret = get_caret_rect()
                self.accent_bar.show(
                    variants,
                    self.accent.selected_index,
                    caret.x,
                    caret.y,
                    caret.height,
                )
                set_popup_visible(True, swallow_digits=True)
                return True

        return False

    def _dismiss_accent(self: Any) -> None:
        if getattr(self, "accent", None):
            self.accent.reset()
        if getattr(self, "accent_bar", None):
            self.accent_bar.hide()
        set_popup_visible(False)

    def _on_key_up(self: Any, event: Any) -> None:
        if getattr(self, "accent", None):
            self.accent.on_key_up(event.vk_code, time.monotonic())


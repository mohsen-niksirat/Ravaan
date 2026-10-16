"""Action handlers for RavanApp (text transformation, clipboard, language indicator, and undo)."""

from __future__ import annotations

import logging
import time
from typing import Any

from ravan.platform import winapi as w
from ravan.platform.caret import get_caret_rect
from ravan.platform.inject import replace_last_n_with
from ravan.platform.lang import current_language, language_label

log = logging.getLogger(__name__)


class AppActionsMixin:
    """Mixin containing user action implementations for RavanApp."""

    def _undo_last_autocorrect(self: Any) -> bool:
        if self._last_autocorrect is None:
            return False
        orig, corrected, t_done, delim = self._last_autocorrect
        self._last_autocorrect = None
        if time.monotonic() - t_done > 10.0:
            return False

        delete_len = len(corrected) + len(delim)
        replace_text = orig + delim
        self._suppress_until = time.monotonic() + 0.08
        replace_last_n_with(delete_len, replace_text)

        for _ in range(delete_len):
            if self.journal._chars:
                self.journal._chars.pop()
        for ch in replace_text:
            self.journal.push(ch)

        log.info("Undid autocorrect: reverted %r back to %r", corrected, orig)
        self._record_event(f"Undid autocorrect: reverted '{corrected}' -> '{orig}'")
        self.tray.notify(f"Reverted to '{orig}'")
        return True

    def _convert_selection_or_last_word(self: Any) -> None:
        """Convert selected text if any exists; otherwise convert the last typed word."""
        from ravan.platform.clipboard import try_convert_selection

        self._suppress_until = time.monotonic() + 0.12
        if try_convert_selection(self.mapper.convert_text):
            log.info("Converted selected text layout")
            return
        self._convert_last_word()

    def _convert_last_word(self: Any) -> None:
        word, trailing = self.journal.last_word_info(allow_trailing_spaces=True)
        if not word:
            return
        converted = self.mapper.convert_word(word)
        if not converted or converted == word:
            log.info("No conversion for %r", word)
            return
        log.info("Convert %r → %r (trailing spaces: %d)", word, converted, trailing)
        self._suppress_until = time.monotonic() + 0.05
        trailing_str = " " * trailing
        replace_last_n_with(len(word) + trailing, converted + trailing_str)
        self.journal.pop_last_word_info(allow_trailing_spaces=True)
        for ch in converted + trailing_str:
            self.journal.push(ch)

    def _normalize_selection_or_last_word(self: Any) -> None:
        """Normalize Persian text in selection or the last typed word."""
        from ravan.core.transform import normalize_text
        from ravan.platform.clipboard import try_convert_selection

        self._suppress_until = time.monotonic() + 0.12
        if try_convert_selection(normalize_text):
            log.info("Normalized selected text")
            return
        self._normalize_last_word()

    def _normalize_last_word(self: Any) -> None:
        from ravan.core.transform import normalize_text

        word, trailing = self.journal.last_word_info(allow_trailing_spaces=True)
        if not word:
            return
        normalized = normalize_text(word)
        if not normalized or normalized == word:
            return
        log.info("Normalize %r → %r (trailing: %d)", word, normalized, trailing)
        self._suppress_until = time.monotonic() + 0.05
        trailing_str = " " * trailing
        replace_last_n_with(len(word) + trailing, normalized + trailing_str)
        self.journal.pop_last_word_info(allow_trailing_spaces=True)
        for ch in normalized + trailing_str:
            self.journal.push(ch)

    def _cycle_case_selection_or_last_word(self: Any) -> None:
        """Cycle case (UPPER -> lower -> Title) of selection or last typed word."""
        from ravan.core.transform import cycle_case
        from ravan.platform.clipboard import try_convert_selection

        self._suppress_until = time.monotonic() + 0.12
        if try_convert_selection(cycle_case):
            log.info("Cycled case of selected text")
            return
        self._cycle_case_last_word()

    def _cycle_case_last_word(self: Any) -> None:
        from ravan.core.transform import cycle_case

        word, trailing = self.journal.last_word_info(allow_trailing_spaces=True)
        if not word:
            return
        cased = cycle_case(word)
        if not cased or cased == word:
            return
        log.info("Cycle case %r → %r (trailing: %d)", word, cased, trailing)
        self._suppress_until = time.monotonic() + 0.05
        trailing_str = " " * trailing
        replace_last_n_with(len(word) + trailing, cased + trailing_str)
        self.journal.pop_last_word_info(allow_trailing_spaces=True)
        for ch in cased + trailing_str:
            self.journal.push(ch)

    def _show_lang_indicator(self: Any) -> None:
        lang = current_language()
        if lang is None:
            return
        caret = get_caret_rect()
        self.overlay.show_language(
            language_label(lang), caret.x, caret.y, caret.height
        )

    def _show_clipboard_popup(self: Any) -> None:
        from ravan.platform.hook import set_popup_visible

        items = self.clip_history.items()
        if not items:
            self.tray.notify("Clipboard history is empty")
            return
        caret = get_caret_rect()
        self.overlay.show_clipboard(items, caret.x, caret.y, caret.height)
        set_popup_visible(True, swallow_digits=self.cfg.quickpick_digits)
        self._popup_shown_at = time.monotonic()
        log.info("Showing clipboard popup with %d items", len(items))

    def _paste_clipboard_item(self: Any, text: str) -> None:
        from ravan.platform.clipboard import set_clipboard_text
        from ravan.platform.inject import send_shortcut

        self._suppress_until = time.monotonic() + 0.1
        set_clipboard_text(text)
        time.sleep(0.02)
        send_shortcut([w.VK_CONTROL], ord("V"))
        log.info("Pasted clipboard item (%d chars)", len(text))

    def _maybe_attach_suffix_zwnj(self: Any, suffix: str) -> bool:
        from ravan.core.zwnj import ZWNJ, should_attach_suffix

        text = self.journal.text()
        suffix_with_spaces = f" {suffix} "
        if not text.endswith(suffix_with_spaces):
            return False
        before = text[: -len(suffix_with_spaces)]
        i = len(before) - 1
        while i >= 0 and not before[i].isspace():
            i -= 1
        prev_word = before[i + 1 :]
        if not prev_word or not should_attach_suffix(prev_word, suffix):
            return False

        delete_n = len(suffix) + 2
        replace_text = f"{ZWNJ}{suffix} "
        self._suppress_until = time.monotonic() + 0.05
        replace_last_n_with(delete_n, replace_text)
        for _ in range(delete_n):
            if self.journal._chars:
                self.journal._chars.pop()
        for c in replace_text:
            self.journal.push(c)
        log.info("Attached suffix ZWNJ: %r + %r", prev_word, suffix)
        return True

    def _get_diagnostics_snapshot(self: Any) -> dict[str, Any]:
        from ravan import __version__
        from ravan.platform.caret import get_caret_rect, get_last_caret_source
        from ravan.platform.focus import active_window_info

        info = active_window_info()
        caret = get_caret_rect()
        lang = current_language()
        layout_str = (
            f"{language_label(lang)} ({hex(lang.hkl)})" if lang else "Unknown"
        )
        hook_alive = bool(
            self.hook and self.hook._thread and self.hook._thread.is_alive()
        )

        return {
            "version": __version__,
            "hook_active": hook_alive,
            "foreground_exe": info.get("exe") or "None",
            "foreground_pid": info.get("pid") or 0,
            "window_title": info.get("title") or "None",
            "is_excluded": self._is_excluded(),
            "layout": layout_str,
            "caret_source": get_last_caret_source(),
            "caret_pos": f"(x={caret.x}, y={caret.y}, w={caret.width}, h={caret.height})",
            "recent_events": list(self.recent_events),
        }

"""Action handlers for RavanApp (text transformation, clipboard, language indicator, and undo)."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from ravan.platform import winapi as w
from ravan.platform.caret import get_caret_rect
from ravan.platform.inject import replace_last_n_with
from ravan.platform.lang import current_language, language_label

log = logging.getLogger(__name__)


class AppActionsMixin:
    """Mixin containing user action implementations for RavanApp."""

    def _convert_selection_or_last_word(self: Any) -> None:
        """Convert selected text if any exists; otherwise convert the last typed word(s)."""
        from ravan.platform.clipboard import try_convert_selection

        self._suppress_until = time.monotonic() + 0.12
        if try_convert_selection(self.mapper.convert_text):
            log.info("Converted selected text layout")
            self._f12_last_converted = None
            self._f12_repeat_count = 0
            return

        now = time.monotonic()
        if (
            hasattr(self, "_f12_last_converted")
            and self._f12_last_converted is not None
            and now - getattr(self, "_last_f12_time", 0.0) < 1.5
        ):
            self._f12_repeat_count = getattr(self, "_f12_repeat_count", 1) + 1
            prev_conv_len, prev_orig_text = self._f12_last_converted
            self._suppress_until = now + 0.06
            replace_last_n_with(prev_conv_len, prev_orig_text)
            self.journal.pop_last_n_chars(prev_conv_len)
            for ch in prev_orig_text:
                self.journal.push(ch)
            time.sleep(0.02)
        else:
            self._f12_repeat_count = 1

        self._last_f12_time = time.monotonic()
        self._convert_last_n_words(self._f12_repeat_count)

    def _convert_last_word(self: Any) -> None:
        self._convert_last_n_words(1)

    def _convert_last_n_words(self: Any, n: int) -> None:
        span_text, span_len = self.journal.last_n_words_span(n=n)
        if not span_text or span_len <= 0:
            self._f12_last_converted = None
            self._f12_repeat_count = 0
            return

        converted = self.mapper.convert_text(span_text)
        if not converted or converted == span_text:
            log.info("No conversion for %r", span_text)
            self._f12_last_converted = None
            return

        log.info("Convert %d words: %r → %r", n, span_text, converted)
        self._suppress_until = time.monotonic() + 0.06
        replace_last_n_with(span_len, converted)
        self.journal.pop_last_n_chars(span_len)
        for ch in converted:
            self.journal.push(ch)
        self._f12_last_converted = (len(converted), span_text)

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
        label = language_label(lang)
        if getattr(self.cfg, "translit_enabled", False):
            label = f"{label}-TL"
        caret = get_caret_rect()
        self.overlay.show_language(
            label, caret.x, caret.y, caret.height
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

    def _show_quick_text_stats(self: Any) -> None:
        from ravan.core.text_stats import calculate_text_stats
        from ravan.platform import winapi as w
        from ravan.platform.caret import get_caret_rect
        from ravan.platform.clipboard import get_clipboard_text, set_clipboard_text
        from ravan.platform.inject import send_shortcut
        from ravan.ui.stats_popup import StatsPopupWindow

        old_clip = get_clipboard_text()
        self._suppress_until = time.monotonic() + 0.15

        # Simulate Ctrl+C to copy selected text
        send_shortcut([w.VK_CONTROL], 0x43)
        time.sleep(0.06)

        new_clip = get_clipboard_text()
        if old_clip is not None:
            set_clipboard_text(old_clip)

        target_text = ""
        if new_clip and new_clip.strip() and new_clip != old_clip:
            target_text = new_clip
        else:
            word = self.journal.last_word()
            if word and len(word) >= 2:
                target_text = word

        if not target_text:
            from ravan.core.i18n import t

            self.tray.notify(
                t(
                    "notifications.select_text_stats_hint",
                    "Select text and press Alt+S to view statistics.",
                ),
                title=t("stats.header", "📊 Text Statistics"),
            )
            return

        stats = calculate_text_stats(target_text)
        caret = get_caret_rect()
        if not hasattr(self, "_stats_popup") or self._stats_popup is None:
            self._stats_popup = StatsPopupWindow(parent=getattr(self.overlay, "_root", None))
        self._stats_popup.show(stats, x=caret.x, y=caret.y + caret.height + 6)

    def toggle_power_mode(self: Any, duration_min: int | None = None) -> bool:
        """Toggle Power Mode (Focus Typing) to suppress all popups."""
        self.power_mode_active = not getattr(self, "power_mode_active", False)
        from ravan.core.i18n import t

        if self.power_mode_active:
            self.overlay.hide()
            from ravan.ui.app import set_popup_visible

            set_popup_visible(False)
            if hasattr(self, "_stats_popup") and self._stats_popup is not None:
                self._stats_popup.hide()
            if hasattr(self.tray, "set_power_mode"):
                self.tray.set_power_mode(True)

            mins = (
                duration_min
                if duration_min is not None
                else getattr(self.cfg, "power_mode_duration_min", 0)
            )
            if mins > 0:
                if (
                    hasattr(self, "_power_mode_timer")
                    and self._power_mode_timer is not None
                ):
                    self._power_mode_timer.cancel()
                self._power_mode_timer = threading.Timer(
                    mins * 60, self._auto_disable_power_mode
                )
                self._power_mode_timer.daemon = True
                self._power_mode_timer.start()
                msg = t(
                    "power_mode.enabled_timed",
                    "Power Mode active ({mins} min): popups suppressed.",
                    mins=mins,
                )
            else:
                msg = t(
                    "power_mode.enabled",
                    "Power Mode active: popups suppressed for focus typing.",
                )
            self.tray.notify(msg, title=t("power_mode.title", "Focus Typing"))
        else:
            if hasattr(self, "_power_mode_timer") and self._power_mode_timer:
                self._power_mode_timer.cancel()
                self._power_mode_timer = None
            if hasattr(self.tray, "set_power_mode"):
                self.tray.set_power_mode(False)
            msg = t("power_mode.disabled", "Power Mode disabled: popups restored.")
            self.tray.notify(msg, title=t("power_mode.title", "Focus Typing"))

        return self.power_mode_active

    def _auto_disable_power_mode(self: Any) -> None:
        """Callback when Power Mode duration timer expires."""
        if getattr(self, "power_mode_active", False):
            self.toggle_power_mode()

    def start_macro_recording(self: Any) -> None:
        """Start recording user keystrokes for a macro snippet."""
        if not hasattr(self, "macro_recorder") or self.macro_recorder is None:
            from ravan.core.macro import MacroRecorder

            self.macro_recorder = MacroRecorder()
        self.macro_recorder.start()
        from ravan.core.i18n import t

        self.tray.notify(
            t(
                "macro.recording_started",
                "Macro recording started. Type keystrokes and press Esc to finish.",
            ),
            title=t("macro.recording_title", "Recording Macro…"),
        )

    def stop_macro_recording(self: Any) -> None:
        """Stop recording macro and open save dialog."""
        if not hasattr(self, "macro_recorder") or not self.macro_recorder.is_recording:
            return
        events = self.macro_recorder.stop()
        from ravan.core.i18n import t

        if not events:
            self.tray.notify(
                t("macro.cancelled", "Macro recording cancelled (no keystrokes).")
            )
            return

        def _show_dialog() -> None:
            from ravan.ui.macro_dialog import MacroSaveDialog

            dlg = MacroSaveDialog(
                parent=getattr(self.overlay, "_root", None),
                events=events,
                existing_snippets=self.cfg.snippets,
                on_save=self._on_macro_saved,
            )
            dlg.show()

        if getattr(self.overlay, "_root", None):
            self.overlay._root.after(0, _show_dialog)

    def _on_macro_saved(self: Any, snippet: Any) -> None:
        """Callback when user saves a macro snippet from dialog."""
        from ravan.core.config import save_config
        from ravan.core.i18n import t
        from ravan.core.snippet import SnippetEngine

        self.cfg.snippets = [
            s for s in self.cfg.snippets if s.trigger != snippet.trigger
        ] + [snippet]
        save_config(self.cfg)
        self.snippets = SnippetEngine.from_config(self.cfg)
        self.tray.notify(
            t(
                "macro.saved_notice",
                "Macro '{trigger}' saved successfully!",
                trigger=snippet.trigger,
            )
        )


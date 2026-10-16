"""State polling and background monitoring for RavanApp (focus, language, clipboard, and prediction)."""

from __future__ import annotations

import logging
import time
from typing import Any

from ravan.platform import winapi as w
from ravan.platform.caret import get_caret_rect
from ravan.platform.focus import foreground_exe
from ravan.platform.hook import set_popup_visible
from ravan.platform.lang import current_language, language_label
from ravan.platform.winapi import wintypes

log = logging.getLogger(__name__)


class AppPollingMixin:
    """Mixin containing polling and debounce timer logic for RavanApp."""

    def _poll_focus(self: Any) -> None:
        now = time.monotonic()
        if now - self._last_focus_poll < 0.2:
            return
        self._last_focus_poll = now

        exe = foreground_exe()
        # Transient failures (None) or our own overlay/settings window shouldn't
        # be treated as a real app switch — they would wipe the journal mid-type.
        if not exe or self._is_foreground_self():
            return
        if exe == self._current_exe:
            return
        self._current_exe = exe
        # New window → unknown text state; reset journal & popup
        self.journal.clear()
        self._pending_predict = False
        if self.overlay.predicting:
            self.overlay.hide()
            set_popup_visible(False)

    def _is_foreground_self(self: Any) -> bool:
        """True if the focused window belongs to this process (overlay/settings)."""
        import ctypes

        try:
            hwnd = w.user32.GetForegroundWindow()
            if not hwnd:
                return False
            pid = wintypes.DWORD(0)
            w.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            return pid.value == self._own_pid
        except Exception:  # noqa: BLE001
            return False

    def _is_excluded(self: Any) -> bool:
        return self.cfg.is_excluded(self._current_exe)

    def _poll_language(self: Any) -> None:
        now = time.monotonic()
        if now - self._last_lang_poll < 0.15:
            return
        self._last_lang_poll = now
        lang = current_language()
        if lang is None:
            return
        self._active_layout_tag = lang.tag
        if self._last_lang_hkl is None:
            self._last_lang_hkl = lang.hkl
            return
        if lang.hkl != self._last_lang_hkl:
            self._last_lang_hkl = lang.hkl
            if self._is_excluded():
                return
            if self.cfg.sound_feedback_enabled:
                from ravan.platform.sound import play_layout_switch_sound

                play_layout_switch_sound(lang.tag == "fa")
            caret = get_caret_rect()
            self.overlay.show_language(
                language_label(lang), caret.x, caret.y, caret.height
            )

    def _poll_clipboard(self: Any) -> None:
        if not self.cfg.clipboard_history_enabled:
            return
        now = time.monotonic()
        if now - self._last_clip_poll < 0.35:
            return
        self._last_clip_poll = now
        from ravan.platform.clipboard import get_clipboard_text

        text = get_clipboard_text()
        if text:
            self.clip_history.add(text)

    def _schedule_predict(self: Any) -> None:
        self._last_key_time = time.monotonic()
        self._pending_predict = True

    def _maybe_predict(self: Any) -> None:
        if not self._pending_predict or not self.cfg.prediction_enabled:
            return
        if self._is_excluded():
            return
        elapsed_ms = (time.monotonic() - self._last_key_time) * 1000
        if elapsed_ms < self.cfg.prediction_debounce_ms:
            return
        self._pending_predict = False
        prefix = self.journal.last_word()
        context_word = (
            self.journal.previous_word()
            if hasattr(self.journal, "previous_word")
            else ""
        )

        if len(prefix) < self.cfg.min_prefix_len:
            if self.cfg.next_word_prediction and context_word and prefix == "":
                cands = self.predictor.predict(
                    "", context_word, self.cfg.prediction_max_candidates
                )
                if cands:
                    caret = get_caret_rect()
                    self.overlay.show_predictions(
                        cands, caret.x, caret.y, caret.height
                    )
                    set_popup_visible(
                        True, swallow_digits=self.cfg.quickpick_digits
                    )
                    self._popup_shown_at = time.monotonic()
                    log.info(
                        "Showing %d next-word suggestions for context %r",
                        len(cands),
                        context_word,
                    )
                    return
            if self.overlay.predicting:
                self.overlay.hide()
                set_popup_visible(False)
            return

        cands = self.predictor.predict(
            prefix, context_word, self.cfg.prediction_max_candidates
        )
        if not cands:
            if self.overlay.predicting:
                self.overlay.hide()
                set_popup_visible(False)
            return
        caret = get_caret_rect()
        self.overlay.show_predictions(cands, caret.x, caret.y, caret.height)
        set_popup_visible(True, swallow_digits=self.cfg.quickpick_digits)
        self._popup_shown_at = time.monotonic()
        log.info("Showing %d suggestions for %r", len(cands), prefix)

    def _maybe_timeout_popup(self: Any) -> None:
        """Auto-hide a stale prediction popup (e.g. user switched to mouse)."""
        if not self.overlay.predicting:
            return
        timeout_s = self.cfg.popup_timeout_ms / 1000.0
        if timeout_s <= 0:
            return
        if time.monotonic() - self._popup_shown_at > timeout_s:
            self.overlay.hide()
            set_popup_visible(False)

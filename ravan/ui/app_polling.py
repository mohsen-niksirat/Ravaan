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

        hwnd = w.user32.GetForegroundWindow()
        if not hwnd or self._is_foreground_self():
            return

        from ravan.platform.focus import is_window_elevated, window_class_name

        if is_window_elevated(hwnd):
            if not getattr(self, "_elevated_notified", False):
                self._elevated_notified = True
                self.tray.notify(
                    "Ravaan cannot assist in this window (admin). Run Ravaan as admin to enable.",
                    title="Ravaan (روان)",
                )

        exe = foreground_exe()
        if not exe or exe == self._current_exe:
            return
        self._current_exe = exe
        self._current_window_class = window_class_name(hwnd)
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
        return self.cfg.is_excluded(
            self._current_exe, getattr(self, "_current_window_class", None)
        )

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
            self.journal.previous_context(2)
            if hasattr(self.journal, "previous_context")
            else (
                self.journal.previous_word()
                if hasattr(self.journal, "previous_word")
                else ""
            )
        )

        if len(prefix) < self.cfg.min_prefix_len:
            if self.cfg.next_word_prediction and context_word and prefix == "":
                cands = self.predictor.predict(
                    "", context_word, self.cfg.prediction_max_candidates, app_name=self._current_exe
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
            prefix, context_word, self.cfg.prediction_max_candidates, app_name=self._current_exe
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

    def _poll_background_sync(self: Any) -> None:
        """Periodic background sync debounced after typing bursts with offline backoff."""
        if not getattr(self.cfg, "cloud_sync_enabled", False):
            return
        interval_min = getattr(self.cfg, "sync_interval_min", 0)
        if interval_min <= 0:
            return

        now = time.monotonic()
        if not hasattr(self, "_last_bg_sync_poll"):
            self._last_bg_sync_poll = now
            self._last_sync_attempt = 0.0
            self._sync_backoff_delay = 0.0
            self._sync_in_progress = False
            self._pending_sync_queued = False

        if now - self._last_bg_sync_poll < 1.0:
            return
        self._last_bg_sync_poll = now

        # Debounce after typing bursts: require at least 15s of idle time
        if now - getattr(self, "_last_key_time", 0.0) < 15.0:
            return

        interval_sec = interval_min * 60.0
        effective_interval = max(interval_sec, self._sync_backoff_delay)
        if (now - self._last_sync_attempt < effective_interval) and not self._pending_sync_queued:
            return

        if self._sync_in_progress:
            self._pending_sync_queued = True
            return

        self._sync_in_progress = True
        self._pending_sync_queued = False
        self._last_sync_attempt = now

        def _bg_worker() -> None:
            from ravan.core.config import Snippet, save_config
            from ravan.core.sync import (
                merge_dictionaries,
                merge_snippets,
                pull_sync,
                push_sync,
            )
            from ravan.core.user_dict import load_user_words, save_user_words

            try:
                local_words = load_user_words()
                local_snips = [
                    {"trigger": s.trigger, "replacement": s.replacement, "enabled": s.enabled}
                    for s in self.cfg.snippets
                ]
                res = pull_sync(self.cfg, current_words=local_words, current_snippets=local_snips)
                if not res.get("ok"):
                    log.warning(
                        "Background sync pull failed (%s); queuing backoff retry",
                        res.get("error", "Unknown"),
                    )
                    self._sync_backoff_delay = min(
                        300.0, max(30.0, (self._sync_backoff_delay or 15.0) * 2)
                    )
                    self._pending_sync_queued = True
                    return

                merged_words = merge_dictionaries(local_words, res.get("user_words", []))
                merged_snips, _ = merge_snippets(
                    local_snips, res.get("snippets", []), resolution_strategy="keep_both"
                )

                push_res = push_sync(self.cfg, merged_words, merged_snips)
                if push_res.get("ok"):
                    self._sync_backoff_delay = 0.0
                    save_user_words(merged_words)
                    self.cfg.snippets = [
                        Snippet(
                            trigger=str(s["trigger"]),
                            replacement=str(s["replacement"]),
                            enabled=bool(s.get("enabled", True)),
                        )
                        for s in merged_snips
                        if isinstance(s, dict) and s.get("trigger")
                    ]
                    self.cfg.last_sync_time = push_res.get("timestamp", "")
                    save_config(self.cfg)
                    log.info("Background sync succeeded at %s", self.cfg.last_sync_time)
                else:
                    log.warning("Background sync push failed: %s", push_res.get("error"))
                    self._sync_backoff_delay = min(
                        300.0, max(30.0, (self._sync_backoff_delay or 15.0) * 2)
                    )
                    self._pending_sync_queued = True
            except Exception as exc:  # noqa: BLE001
                log.error("Unexpected error in background sync: %s", exc)
                self._sync_backoff_delay = 60.0
                self._pending_sync_queued = True
            finally:
                self._sync_in_progress = False

        import threading
        threading.Thread(target=_bg_worker, name="ravan-bg-sync", daemon=True).start()

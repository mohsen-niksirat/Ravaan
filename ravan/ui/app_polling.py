"""State polling and background monitoring for RavanApp (focus, language, clipboard, and prediction)."""

from __future__ import annotations

import logging
import time
from typing import Any

from ravan.platform import winapi as w
from ravan.platform.caret import get_caret_rect
from ravan.platform.focus import foreground_exe, window_class_name
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

        self._check_elevated(hwnd)

        exe = foreground_exe()
        if not exe:
            return
        prev_hwnd = getattr(self, "_current_hwnd", None)
        hwnd_changed = prev_hwnd not in (None, 0) and hwnd != prev_hwnd
        if exe == self._current_exe and not hwnd_changed:
            self._current_hwnd = hwnd
            return
        self._current_exe = exe
        self._current_hwnd = hwnd
        self._current_window_class = window_class_name(hwnd)
        # New window or dialog → unknown text state; reset journal & popup
        self.journal.clear()
        self._journal_desynced = True
        self._last_autocorrect = None
        self._pending_predict = False
        self._pending_selection_check_time = None
        if self.overlay.visible:
            self.overlay.hide()
            set_popup_visible(False)
        if hasattr(self, "_hide_selection_toolbar"):
            self._hide_selection_toolbar()
        if hasattr(self, "_hide_undo_chip"):
            self._hide_undo_chip()

        if exe and exe != getattr(self, "_last_profile_layout_exe", None):
            self._last_profile_layout_exe = exe
            from ravan.core.profiles import resolve_effective_profile

            prof = resolve_effective_profile(self.cfg, exe)
            if prof.preferred_layout in ("fa", "en") and not self._is_excluded():
                from ravan.platform.focus import is_fullscreen_focused, is_password_focused
                from ravan.platform.lang import (
                    current_language,
                    is_ime_composing,
                    switch_to_language,
                )

                if not is_password_focused() and not is_fullscreen_focused() and not is_ime_composing():
                    cur = current_language()
                    if cur is None or not cur.tag.lower().startswith(prof.preferred_layout):
                        switch_to_language(prof.preferred_layout, hwnd=hwnd)

    def _poll_hook_health(self: Any) -> None:
        """Watchdog to verify keyboard hook is alive; detect sleep/resume and lock screen."""
        now = time.monotonic()
        last_tick = getattr(self, "_last_watchdog_tick", now)
        elapsed = now - last_tick
        self._last_watchdog_tick = now

        # Detect sleep/resume or lock screen via monotonic clock jump (> 4.0s)
        if elapsed > 4.0:
            log.info("System clock jump detected (elapsed=%.2fs); recovering after wake/lock.", elapsed)
            self.journal.clear()
            self._pending_predict = False
            if hasattr(self, "overlay") and self.overlay.visible:
                self.overlay.hide()
                set_popup_visible(False)
            if hasattr(self, "hook") and self.hook:
                self.hook.check_health()
            return

        # Periodic health check every 3.0 seconds
        last_check = getattr(self, "_last_hook_health_check", 0.0)
        if now - last_check >= 3.0:
            self._last_hook_health_check = now
            if hasattr(self, "hook") and self.hook:
                self.hook.check_health()

    def _check_elevated(self: Any, hwnd: int | None = None) -> bool:
        from ravan.platform.focus import is_window_elevated

        target_hwnd = hwnd or w.user32.GetForegroundWindow()
        if not target_hwnd or self._is_foreground_self():
            return False
        if is_window_elevated(target_hwnd):
            warned = getattr(self, "_elevated_warned_hwnds", None)
            if warned is None:
                warned = set()
                self._elevated_warned_hwnds = warned
            if target_hwnd not in warned:
                warned.add(target_hwnd)
                if len(warned) > 100:
                    warned.pop()
                self.tray.notify(
                    "Ravaan cannot assist in this window (admin). Run Ravaan as admin to enable.",
                    title="Ravaan (روان)",
                )
            return True
        return False

    def _is_foreground_self(self: Any) -> bool:
        """True if the focused window belongs to an interactive Ravan window (settings/dialog), NOT the overlay."""
        import ctypes

        try:
            hwnd = w.user32.GetForegroundWindow()
            if not hwnd:
                return False
            cur_root = int(w.user32.GetAncestor(hwnd, 2) or hwnd)
            # Never treat non-activating suggestion overlay or toast as an interactive dialog
            if hasattr(self, "overlay") and hasattr(self.overlay, "_get_root_hwnd"):
                ov_hwnd = self.overlay._get_root_hwnd()
                if ov_hwnd and (int(hwnd) == int(ov_hwnd) or cur_root == int(ov_hwnd)):
                    return False
            if hasattr(self, "_toast") and getattr(self._toast, "_top", None):
                try:
                    thwnd = int(self._toast._top.winfo_id())
                    troothwnd = int(w.user32.GetAncestor(thwnd, 2) or thwnd)
                    if int(hwnd) in (thwnd, troothwnd) or cur_root in (thwnd, troothwnd):
                        return False
                except Exception:
                    pass

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
            if self.overlay.predicting:
                self.overlay.hide()
                set_popup_visible(False)
            self._pending_predict = False
            if self.cfg.sound_feedback_enabled:
                from ravan.platform.sound import play_layout_switch_sound

                play_layout_switch_sound(lang.tag == "fa")
            caret = get_caret_rect()
            placement = getattr(self.cfg, "lang_indicator_placement", "bottom_right")
            if placement in ("bottom_right", "bottom_left", "top_right", "top_left"):
                self.overlay.show_language(
                    language_label(lang), -1, -1, caret.height, placement=placement
                )
            else:
                self.overlay.show_language(
                    language_label(lang), caret.x, caret.y, caret.height
                )
            # Stamp the popup timer so the language chip is not instantly hidden
            # by _maybe_timeout_popup on the next loop tick.
            self._popup_shown_at = time.monotonic()

    def _poll_learning_flush(self: Any) -> None:
        """Periodically persist lazily-deferred learning/clipboard state off the keystroke path."""
        now = time.monotonic()
        if now - getattr(self, "_last_lazy_flush", 0.0) < 15.0:
            return
        self._last_lazy_flush = now
        try:
            if hasattr(self.predictor, "flush_learning"):
                self.predictor.flush_learning()
        except Exception:  # noqa: BLE001
            log.debug("Deferred learning flush failed", exc_info=True)
        try:
            if hasattr(self, "clip_history") and hasattr(self.clip_history, "flush"):
                self.clip_history.flush()
        except Exception:  # noqa: BLE001
            log.debug("Deferred clipboard flush failed", exc_info=True)

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
            self.clip_history.add(
                text,
                source_app=self._current_exe,
                ignore_passwords=self.cfg.clip_history_ignore_passwords,
                excluded_apps=self.cfg.excluded_apps,
                retention_days=self.cfg.clip_history_retention_days,
            )

    def _schedule_predict(self: Any) -> None:
        self._last_key_time = time.monotonic()
        self._pending_predict = True

    def _effective_swallow_arrow(self: Any) -> str | None:
        """Compute which horizontal arrow key(s) WH_KEYBOARD_LL should swallow while popup is visible."""
        if getattr(self.cfg, "prediction_layout", "vertical") == "horizontal":
            return "both"
        arrow_cfg = getattr(self.cfg, "suggestion_accept_arrow", "right")
        if arrow_cfg == "none":
            return None
        if arrow_cfg == "left":
            return "left"
        if arrow_cfg in ("auto", "auto_rtl"):
            lang = current_language()
            return "left" if (lang and lang.is_persian) else "right"
        return "right"

    def _resync_journal_from_caret(self: Any) -> None:
        """Best-effort UIA resync of recent pre-caret text after edits/clicks/backspace."""
        if getattr(self, "_uia_resync_enabled", False) is not True:
            return
        try:
            from ravan.platform.caret import get_text_before_caret

            uia_text = get_text_before_caret(max_chars=64)
        except Exception:  # noqa: BLE001
            return
        if uia_text is None:
            return
        uia_text = uia_text.replace("\u200b", "").replace("\ufeff", "")
        if (
            uia_text == ""
            and not getattr(self, "_last_key_was_backspace", False)
            and self.journal.last_word()
        ):
            return
        self.journal.clear()
        for ch in uia_text:
            self.journal.push(ch)
        self._journal_desynced = False

    def _maybe_predict(self: Any) -> None:
        pred_enabled = (
            self._effective_prediction_enabled()
            if hasattr(self, "_effective_prediction_enabled")
            else bool(getattr(self.cfg, "prediction_enabled", True))
        )
        if not self._pending_predict or not pred_enabled:
            return
        if getattr(self, "power_mode_active", False):
            self._pending_predict = False
            return
        from ravan.platform.focus import is_numeric_focused, is_password_focused
        from ravan.platform.lang import is_ime_composing

        if is_password_focused() or is_numeric_focused() or is_ime_composing():
            self._pending_predict = False
            return
        if self._is_excluded():
            return
        elapsed_ms = (time.monotonic() - self._last_key_time) * 1000
        if elapsed_ms < self.cfg.prediction_debounce_ms:
            return
        self._pending_predict = False
        if getattr(self, "_just_pasted", False) and not self.journal.last_word():
            if self.overlay.visible:
                self.overlay.hide()
                set_popup_visible(False)
            return
        if getattr(self, "_last_key_was_backspace", False) or getattr(
            self, "_journal_desynced", False
        ):
            self._resync_journal_from_caret()
        from ravan.core.normalizer import (
            is_numeric_or_symbol_token,
            is_valid_prediction_context_word,
        )

        prefix = self.journal.last_word()
        if prefix and is_numeric_or_symbol_token(prefix):
            if self.overlay.visible:
                self.overlay.hide()
                set_popup_visible(False)
            return
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
            last_ctx_token = context_word.strip().split()[-1] if context_word and context_word.strip() else ""
            if (
                self.cfg.next_word_prediction
                and context_word
                and prefix == ""
                and not getattr(self, "_last_key_was_backspace", False)
                and not getattr(self, "_just_pasted", False)
                and is_valid_prediction_context_word(last_ctx_token)
            ):
                cands = self.predictor.predict(
                    "", context_word, self.cfg.prediction_max_candidates, app_name=self._current_exe
                )
                if cands:
                    if getattr(self.overlay, "has_custom_pos", False) and self.overlay.custom_x >= 0:
                        cx, cy, ch = self.overlay.custom_x, self.overlay.custom_y, 16
                    else:
                        caret = get_caret_rect()
                        cx, cy, ch = caret.x, caret.y, caret.height
                    self.overlay.show_predictions(
                        cands, cx, cy, ch, on_accept=self._accept_candidate
                    )
                    swallow_enter = bool(getattr(self.cfg, "suggestion_accept_enter", False))
                    set_popup_visible(
                        True,
                        swallow_digits=self.cfg.quickpick_digits,
                        swallow_arrow=self._effective_swallow_arrow(),
                        swallow_enter=swallow_enter,
                    )
                    self._popup_shown_at = time.monotonic()
                    log.info(
                        "Showing %d next-word suggestions for context %r",
                        len(cands),
                        context_word,
                    )
                    return
            if self.overlay.visible:
                self.overlay.hide()
                set_popup_visible(False)
            return

        cands = self.predictor.predict(
            prefix, context_word, self.cfg.prediction_max_candidates, app_name=self._current_exe
        )
        if not cands:
            if (
                self.overlay.predicting
                and not getattr(self, "_last_key_was_backspace", False)
                and not getattr(self, "_edited_since_popup", False)
            ):
                # Sticky popup: keep the current suggestion box visible until the
                # next keystroke refreshes it, a word completes, or the timeout
                # fires — a mid-word candidate gap must not flicker it away.
                return
            self._edited_since_popup = False
            if self.overlay.visible:
                self.overlay.hide()
                set_popup_visible(False)
            return
        self._edited_since_popup = False
        if getattr(self.overlay, "has_custom_pos", False) and self.overlay.custom_x >= 0:
            cx, cy, ch = self.overlay.custom_x, self.overlay.custom_y, 16
        else:
            caret = get_caret_rect()
            cx, cy, ch = caret.x, caret.y, caret.height
        self.overlay.show_predictions(
            cands, cx, cy, ch, on_accept=self._accept_candidate
        )
        swallow_enter = bool(getattr(self.cfg, "suggestion_accept_enter", False))
        set_popup_visible(
            True,
            swallow_digits=self.cfg.quickpick_digits,
            swallow_arrow=self._effective_swallow_arrow(),
            swallow_enter=swallow_enter,
        )
        self._popup_shown_at = time.monotonic()
        log.info("Showing %d suggestions for %r", len(cands), prefix)

    def _maybe_timeout_popup(self: Any) -> None:
        """Auto-hide a stale prediction popup (e.g. user switched to mouse)."""
        if not self.overlay.visible:
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

        from ravan.core.sync import snippet_to_dict

        local_snips = [snippet_to_dict(s) for s in list(self.cfg.snippets)]

        def _bg_worker() -> None:
            from ravan.core.config import save_config
            from ravan.core.sync import (
                dict_to_snippet,
                merge_dictionaries,
                merge_snippets,
                pull_sync,
                push_sync,
            )
            from ravan.core.user_dict import load_user_words, save_user_words

            try:
                local_words = load_user_words()
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
                    new_snippets = [
                        dict_to_snippet(s)
                        for s in merged_snips
                        if isinstance(s, dict) and str(s.get("trigger", "")).strip()
                    ]
                    ts = push_res.get("timestamp", "")
                    if hasattr(self, "_ui_queue") and self._ui_queue is not None:
                        self._ui_queue.put(("apply_bg_sync", (new_snippets, ts)))
                    else:
                        from ravan.core.snippet import SnippetEngine

                        self.cfg.snippets = new_snippets
                        self.cfg.last_sync_time = ts
                        self.snippets = SnippetEngine.from_config(self.cfg)
                        save_config(self.cfg)
                    log.info("Background sync succeeded at %s", ts)
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

    def _invalidate_journal_for_external_click(self: Any) -> None:
        """Reset linear journal immediately when user clicks outside Ravaan overlay."""
        if self._is_foreground_self():
            return
        if hasattr(self, "journal"):
            self.journal.clear()
        self._journal_desynced = True
        self._just_pasted = False
        self._last_autocorrect = None
        self._pending_predict = False
        if getattr(self.overlay, "predicting", False) is True:
            self.overlay.hide()
            set_popup_visible(False)
        if hasattr(self, "_hide_selection_toolbar"):
            self._hide_selection_toolbar()
        if hasattr(self, "_hide_undo_chip"):
            self._hide_undo_chip()

    def _is_point_in_overlay(self: Any, pos: Any) -> bool:
        if pos is None:
            return False
        for attr in ("overlay", "undo_chip", "selection_toolbar"):
            pop = getattr(self, attr, None)
            if pop is None or getattr(pop, "visible", False) is not True:
                continue
            fn = getattr(pop, "contains_screen_point", None)
            if callable(fn) and fn(pos.x, pos.y) is True:
                return True
        return False

    def _poll_mouse_click(self: Any) -> None:
        """Detect mouse click in an input area, reset stale journal, and show indicator.

        Protects laptop touchpad and mouse double-clicks: if a second tap/click arrives
        within the double-click threshold (~220ms), any pending single-click indicator is
        aborted immediately so double-clicks and double-taps remain 100% responsive and
        never interrupted by window creation or input inspection.
        """
        now = time.monotonic()
        is_down = bool(w.user32.GetAsyncKeyState(0x01) & 0x8000)  # VK_LBUTTON
        last_down = getattr(self, "_mouse_left_down", False)
        is_right_down = bool(w.user32.GetAsyncKeyState(0x02) & 0x8000)  # VK_RBUTTON
        last_right_down = getattr(self, "_mouse_right_down", False)
        if is_right_down and not last_right_down:
            self._mouse_right_down = True
            try:
                from ravan.platform.caret import _cursor_position

                r_pos = _cursor_position()
            except Exception:
                r_pos = None
            if not self._is_point_in_overlay(r_pos):
                self._invalidate_journal_for_external_click()
        elif not is_right_down and last_right_down:
            self._mouse_right_down = False
        show_lang = bool(getattr(self.cfg, "show_lang_on_click", True))

        if show_lang:
            # Check if a pending single-click has settled (no second click arrived)
            pending_time = getattr(self, "_pending_click_time", None)
            if pending_time is not None and now - pending_time >= 0.22:
                self._pending_click_time = None
                self._dispatch_mouse_click_indicator()
        else:
            self._pending_click_time = None

        pending_sel = getattr(self, "_pending_selection_check_time", None)
        if pending_sel is not None and now >= pending_sel:
            self._pending_selection_check_time = None
            self._dispatch_selection_toolbar()

        if is_down and not last_down:
            self._mouse_left_down = True
            self._mouse_down_time = now
            self._pending_selection_check_time = None

            # If a single-click was pending, a second tap/click has started -> DOUBLE-CLICK!
            if (show_lang and getattr(self, "_pending_click_time", None) is not None) or (
                now - getattr(self, "_last_tap_up_time", 0.0) < 0.35
            ):
                self._pending_click_time = None
                self._last_double_click_time = now
                self._invalidate_journal_for_external_click()
                return

            down_pos = None
            try:
                from ravan.platform.caret import _cursor_position

                down_pos = _cursor_position()
            except Exception:
                down_pos = None
            self._mouse_down_pos = down_pos
            if not self._is_point_in_overlay(down_pos):
                self._invalidate_journal_for_external_click()
            return

        if not is_down and last_down:
            self._mouse_left_down = False
            down_pos = getattr(self, "_mouse_down_pos", None)
            if self._is_point_in_overlay(down_pos):
                return

            # If this release completes a double-click, schedule selection toolbar check
            if now - getattr(self, "_last_double_click_time", 0.0) < 0.45:
                self._pending_selection_check_time = now + 0.08
                return

            down_time = getattr(self, "_mouse_down_time", 0.0)
            elapsed = now - down_time
            moved = False
            if down_pos is not None:
                try:
                    from ravan.platform.caret import _cursor_position

                    cur = _cursor_position()
                    dx = abs(cur.x - down_pos.x)
                    dy = abs(cur.y - down_pos.y)
                    moved = dx > 15 or dy > 15
                except Exception:
                    moved = False

            if elapsed > 0.45 or moved:
                self._invalidate_journal_for_external_click()
                self._pending_selection_check_time = now + 0.08
                return

            self._last_tap_up_time = now
            if not show_lang:
                return

            last_shown = getattr(self, "_last_mouse_lang_shown", 0.0)
            if now - last_shown < 0.6:
                return

            if self._is_excluded() or self._is_foreground_self():
                return

            # Schedule single-click verification to ensure it's not the first tap of a double-tap
            self._pending_click_time = now

    def _dispatch_selection_toolbar(self: Any) -> None:
        """Show Floating Selection Mini-Toolbar if UIA confirms non-empty selection."""
        tb = getattr(self, "selection_toolbar", None)
        if tb is None or not callable(getattr(tb, "show", None)):
            return
        if getattr(self, "is_paused", False) or getattr(self, "power_mode_active", False):
            return
        if self._is_excluded() or self._is_foreground_self():
            return

        from ravan.core.profiles import resolve_effective_profile

        prof = resolve_effective_profile(self.cfg, getattr(self, "_current_exe", None))
        if not prof.selection_toolbar:
            return

        from ravan.platform.focus import is_fullscreen_focused, is_password_focused

        if is_password_focused() or is_fullscreen_focused():
            return

        from ravan.platform.caret import _cursor_position, get_selected_text_and_rect

        sel = get_selected_text_and_rect(max_chars=240)
        if sel is None:
            return
        sel_text, sel_rect = sel
        if not sel_text or len(sel_text.strip()) < 2:
            return

        rect = sel_rect
        if rect is None:
            try:
                rect = _cursor_position()
            except Exception:
                return

        if hasattr(tb, "parent"):
            ov_root = getattr(getattr(self, "overlay", None), "_root", None)
            if ov_root is not None:
                tb.parent = ov_root

        avoid = (
            self._popup_avoid_rects(exclude=tb)
            if hasattr(self, "_popup_avoid_rects") and callable(self._popup_avoid_rects)
            else []
        )
        tb.show(
            x=int(rect.x),
            y=int(rect.y),
            width=int(getattr(rect, "width", 0)),
            height=int(getattr(rect, "height", 16)),
            show_ai=bool(getattr(self.cfg, "ai_assistant_enabled", False)),
            avoid_rects=avoid,
            theme_mode=getattr(self.cfg, "theme_mode", "auto"),
        )

    def _dispatch_mouse_click_indicator(self: Any) -> None:
        """Fires the language indicator after confirming a single click in an active text field."""
        if self._is_excluded() or self._is_foreground_self():
            return

        from ravan.platform.caret import is_text_caret_active

        if not is_text_caret_active():
            return

        self._pending_predict = False
        if hasattr(self, "journal"):
            self.journal.clear()
        self._last_autocorrect = None

        if self.overlay.visible or self.overlay.predicting:
            self.overlay.hide()
            set_popup_visible(False)

        self._last_mouse_lang_shown = time.monotonic()
        self._show_lang_indicator(use_mouse_pos=True)

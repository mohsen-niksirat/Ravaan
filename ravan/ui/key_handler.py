"""Low-level keystroke handling, hotkey dispatch, and inline triggers for RavanApp."""

from __future__ import annotations

import logging
import time
from typing import Any

from ravan.platform import winapi as w
from ravan.platform.hook import LLKHF_INJECTED, HookEvent, set_popup_visible
from ravan.platform.inject import replace_last_n_with
from ravan.platform.keys import is_modifier, matches_hotkey, vk_to_unicode
from ravan.platform.lang import current_language

log = logging.getLogger(__name__)


class KeyHandlerMixin:
    """Mixin containing keystroke processing and trigger dispatch for RavanApp."""

    def _drain_hook_events(self: Any) -> None:
        if self._is_foreground_self():
            while True:
                event = self.hook.poll()
                if event is None:
                    break
            return
        while True:
            event = self.hook.poll()
            if event is None:
                break
            if not event.is_key_down:
                continue
            if event.flags & LLKHF_INJECTED:
                continue
            if time.monotonic() < self._suppress_until:
                continue
            self._handle_key(event)

    def _handle_key(self: Any, event: HookEvent) -> None:
        vk = event.vk_code
        char = vk_to_unicode(vk, event.scan_code) or ""
        self._record_event("Key pressed", vk=vk, char=char)

        # ── Clipboard popup navigation ──
        if self.overlay.clipboard_open:
            if vk == w.VK_ESCAPE:
                self.overlay.hide()
                set_popup_visible(False)
                return
            if vk == w.VK_UP:
                self.overlay.move_selection(-1)
                return
            if vk == w.VK_DOWN:
                self.overlay.move_selection(1)
                return
            if vk in (w.VK_RETURN, w.VK_TAB):
                item = self.overlay.accept_clipboard_selected()
                if item:
                    self._paste_clipboard_item(item)
                set_popup_visible(False)
                return
            if self.cfg.quickpick_digits and ord("1") <= vk <= ord("5"):
                item = self.overlay.accept_clipboard_index(vk - ord("1"))
                if item:
                    self._paste_clipboard_item(item)
                set_popup_visible(False)
                return
            # Non-nav key closes clipboard popup
            self.overlay.hide()
            set_popup_visible(False)

        # ── Prediction popup navigation ──
        elif self.overlay.predicting:
            if vk == w.VK_ESCAPE:
                self.overlay.hide()
                set_popup_visible(False)
                log.info("Prediction popup dismissed by Esc")
                return
            if vk == w.VK_UP:
                self.overlay.move_selection(-1)
                return
            if vk == w.VK_DOWN:
                self.overlay.move_selection(1)
                return
            if vk in (w.VK_RETURN, w.VK_TAB):
                cand = self.overlay.accept_selected()
                if cand:
                    self._accept_candidate(cand)
                set_popup_visible(False)
                return
            if self.cfg.quickpick_digits and ord("1") <= vk <= ord("5"):
                cand = self.overlay.accept_index(vk - ord("1"))
                if cand:
                    self._accept_candidate(cand)
                set_popup_visible(False)
                return
            # Note: Regular character keys fall through to typing, keeping prediction continuous!

        # Hotkeys
        if hasattr(self.cfg, "quick_stats_hotkey") and matches_hotkey(
            vk, self.cfg.quick_stats_hotkey
        ):
            self._ui_queue.put(("quick_stats", None))
            return
        if self.cfg.clipboard_history_enabled and matches_hotkey(
            vk, self.cfg.clipboard_history_hotkey
        ):
            self._show_clipboard_popup()
            return

        if matches_hotkey(vk, self.cfg.undo_autocorrect_hotkey):
            if self._undo_last_autocorrect():
                return
        if matches_hotkey(vk, self.cfg.normalize_hotkey):
            now = time.monotonic()
            if now - self._last_convert_at > 0.3:
                self._last_convert_at = now
                self._normalize_selection_or_last_word()
            return
        if matches_hotkey(vk, self.cfg.case_hotkey):
            now = time.monotonic()
            if now - self._last_convert_at > 0.3:
                self._last_convert_at = now
                self._cycle_case_selection_or_last_word()
            return
        if matches_hotkey(vk, self.cfg.convert_hotkey):
            now = time.monotonic()
            if now - self._last_convert_at > 0.3:
                self._last_convert_at = now
                self._convert_selection_or_last_word()
            return
        if matches_hotkey(vk, self.cfg.lang_indicator_hotkey):
            self._show_lang_indicator()
            return

        if is_modifier(vk):
            return

        if vk == w.VK_ESCAPE:
            if self._last_autocorrect is not None:
                orig, corrected, t_done, delim = self._last_autocorrect
                if time.monotonic() - t_done < 4.0:
                    if self._undo_last_autocorrect():
                        return
            self._last_autocorrect = None
            return

        if vk == w.VK_BACK:
            if self._last_autocorrect is not None:
                orig, corrected, t_done, delim = self._last_autocorrect
                if time.monotonic() - t_done < 4.0:
                    if self._undo_last_autocorrect():
                        return
            self._last_autocorrect = None
            self.journal.push("\b")
            self._schedule_predict()
            return

        # Shift+Space manual ZWNJ hotkey
        if self.cfg.shift_space_zwnj and vk == w.VK_SPACE:
            from ravan.core.zwnj import ZWNJ
            from ravan.platform.keys import modifiers_down

            if modifiers_down(["shift"], exact=True):
                self._suppress_until = time.monotonic() + 0.05
                replace_last_n_with(0, ZWNJ)
                self.journal.push(ZWNJ)
                self.overlay.hide()
                set_popup_visible(False)
                return

        # Regular typing: get unicode char
        ch = vk_to_unicode(vk, event.scan_code)
        if not ch:
            return

        # Inline math calculator trigger '='
        if ch == "=" and self.cfg.inline_calc_enabled:
            from ravan.core.calc import calculate, extract_math_expression

            text_buf = self.journal.text()
            expr = extract_math_expression(text_buf)
            if expr:
                res = calculate(expr)
                if res is not None:
                    self._suppress_until = time.monotonic() + 0.05
                    replace_last_n_with(len(expr), res)
                    for _ in range(len(expr)):
                        if self.journal._chars:
                            self.journal._chars.pop()
                    for c in res:
                        self.journal.push(c)
                    self._record_event(f"Calc: '{expr}=' -> '{res}'", char=res)
                    log.info("Inline calc: %r= → %r", expr, res)
                    return

        # Clean trailing space error before punctuation in Persian typing (e.g. "کتاب ." -> "کتاب.")
        if self.cfg.fix_punctuation_spacing and ch in ".,!?:؛،؟)":
            lang = current_language()
            if lang and lang.tag == "fa":
                text_buf = self.journal.text()
                if len(text_buf) >= 2 and text_buf[-1] == " " and text_buf[-2] not in (" ", "\n"):
                    self._suppress_until = time.monotonic() + 0.05
                    replace_last_n_with(1, "")
                    if self.journal._chars:
                        self.journal._chars.pop()
                    self._record_event(f"Fixed spacing before punctuation '{ch}'")

        if self._last_autocorrect is not None:
            if time.monotonic() - self._last_autocorrect[2] > 4.0 or ch.isalnum():
                self._last_autocorrect = None

        if ch.isspace() or ch in ".,;:!?\n\r\t،؛؟":
            word = self.journal.last_word(allow_trailing_spaces=False)

            # Auto ZWNJ for Persian prefix (e.g. می + space -> می‌)
            if ch == " " and self.cfg.auto_zwnj_enabled:
                from ravan.core.zwnj import ZWNJ, is_zwnj_prefix

                if is_zwnj_prefix(word):
                    self._suppress_until = time.monotonic() + 0.05
                    replace_last_n_with(1, ZWNJ)
                    self.journal.push(ZWNJ)
                    self.overlay.hide()
                    set_popup_visible(False)
                    return

            handled = self._on_word_completed(word, delimiter=ch)
            if not handled:
                self.journal.push(ch)
                # Auto ZWNJ for Persian suffix (e.g. کتاب ها + space -> کتاب‌ها )
                if ch == " " and self.cfg.auto_zwnj_enabled:
                    self._maybe_attach_suffix_zwnj(word)
            self.overlay.hide()
            set_popup_visible(False)
            if self.cfg.next_word_prediction and ch == " ":
                self._schedule_predict()
            return

        self.journal.push(ch)
        self._schedule_predict()

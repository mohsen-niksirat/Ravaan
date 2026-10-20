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
                if hasattr(self, "_on_key_up"):
                    self._on_key_up(event)
                continue
            if event.flags & LLKHF_INJECTED:
                continue
            if time.monotonic() < self._suppress_until:
                continue
            self._handle_key(event)

    def _handle_key(self: Any, event: HookEvent) -> None:
        # Ignore input inside excluded applications completely
        if hasattr(self, "_is_excluded") and self._is_excluded():
            if self.overlay.visible:
                self.overlay.hide()
                set_popup_visible(False)
            if hasattr(self, "journal"):
                self.journal.clear()
            return

        # Suppress all features inside password fields for privacy & security
        from ravan.platform.focus import is_password_focused

        if is_password_focused():
            if self.overlay.visible:
                self.overlay.hide()
                set_popup_visible(False)
            if hasattr(self, "journal"):
                self.journal.clear()
            return

        # Suppress assistance in elevated (admin) windows (single tray warning, never spam)
        if hasattr(self, "_check_elevated") and self._check_elevated():
            if self.overlay.visible:
                self.overlay.hide()
                set_popup_visible(False)
            return

        vk = event.vk_code
        char = vk_to_unicode(vk, event.scan_code) or ""
        self._record_event("Key pressed", vk=vk, char=char)

        if hasattr(self, "_handle_accent_key") and self._handle_accent_key(event, vk, char):
            return

        if getattr(self, "is_paused", False):
            if hasattr(self.cfg, "power_mode_hotkey") and matches_hotkey(
                vk, self.cfg.power_mode_hotkey
            ):
                self._ui_queue.put(("toggle_pause", None))
            return

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
                if vk == w.VK_RETURN and (w.user32.GetKeyState(w.VK_SHIFT) & 0x8000):
                    cand = (
                        self.overlay.accept_sentence_continuation()
                        if hasattr(self.overlay, "accept_sentence_continuation")
                        else None
                    ) or self.overlay.accept_selected()
                else:
                    cand = self.overlay.accept_selected()
                if cand:
                    self._accept_candidate(cand)
                set_popup_visible(False)
                return
            arrow_cfg = getattr(self.cfg, "suggestion_accept_arrow", "right")
            if arrow_cfg != "none":
                is_rtl = False
                if arrow_cfg in ("auto", "auto_rtl"):
                    lang = current_language()
                    is_rtl = bool(lang and lang.is_persian)
                accept_vk = (
                    w.VK_LEFT
                    if (arrow_cfg == "left" or (arrow_cfg in ("auto", "auto_rtl") and is_rtl))
                    else w.VK_RIGHT
                )
                if vk == accept_vk:
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
        if hasattr(self.cfg, "power_mode_hotkey") and matches_hotkey(vk, self.cfg.power_mode_hotkey):
            self._ui_queue.put(("toggle_power_mode", None))
            return
        if hasattr(self.cfg, "quick_stats_hotkey") and matches_hotkey(vk, self.cfg.quick_stats_hotkey):
            if not getattr(self, "power_mode_active", False):
                self._ui_queue.put(("quick_stats", None))
            return
        if self.cfg.clipboard_history_enabled and matches_hotkey(vk, self.cfg.clipboard_history_hotkey):
            self._show_clipboard_popup()
            return

        if getattr(self, "macro_recorder", None) and self.macro_recorder.is_recording:
            if vk == w.VK_ESCAPE:
                self._ui_queue.put(("stop_macro_recording", None))
                return
            self.macro_recorder.record(vk, vk_to_unicode(vk, event.scan_code) or "")

        if (
            matches_hotkey(vk, getattr(self.cfg, "global_undo_hotkey", None))
            or matches_hotkey(vk, self.cfg.undo_autocorrect_hotkey)
        ):
            if hasattr(self, "_undo_last_correction") and self._undo_last_correction():
                return
            if hasattr(self, "_undo_last_autocorrect") and self._undo_last_autocorrect():
                return

        now = time.monotonic()
        for hk, action in (
            (self.cfg.normalize_hotkey, self._normalize_selection_or_last_word),
            (self.cfg.case_hotkey, self._cycle_case_selection_or_last_word),
            (self.cfg.convert_hotkey, self._convert_selection_or_last_word),
        ):
            if matches_hotkey(vk, hk):
                if now - self._last_convert_at > 0.3:
                    self._last_convert_at = now
                    action()
                return

        if matches_hotkey(vk, self.cfg.lang_indicator_hotkey):
            if not getattr(self, "power_mode_active", False):
                self._show_lang_indicator()
            return
        for hk_name, fn_name in (
            ("translit_hotkey", "_toggle_translit"),
            ("ai_assistant_hotkey", "_trigger_ai_assistant"),
            ("voice_dictation_hotkey", "_toggle_voice_dictation"),
        ):
            if hasattr(self.cfg, hk_name) and matches_hotkey(vk, getattr(self.cfg, hk_name)):
                fn = getattr(self, fn_name, None)
                if fn:
                    fn()
                return

        if is_modifier(vk):
            return

        if vk == w.VK_ESCAPE:
            if self._last_autocorrect is not None:
                orig, corrected, t_done, delim = self._last_autocorrect
                if time.monotonic() - t_done < 4.0 and self._undo_last_autocorrect():
                    return
            self._last_autocorrect = None
            return

        if vk == w.VK_BACK:
            if hasattr(self, "_undo_last_correction_from_backspace"):
                if self._undo_last_correction_from_backspace():
                    return
            if self._last_autocorrect is not None:
                orig, corrected, t_done, delim = self._last_autocorrect
                if time.monotonic() - t_done < 4.0 and self._undo_last_autocorrect():
                    return
            self._last_autocorrect = None
            self.journal.push("\b")
            self._schedule_predict()
            return

        # Suppress features inside password fields and excluded apps for security
        from ravan.platform.focus import is_password_focused

        if is_password_focused() or (hasattr(self, "_is_excluded") and self._is_excluded()):
            self.overlay.hide()
            set_popup_visible(False)
            self.journal.clear()
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

        # Inline math calculator trigger '=' and rounding/currency macros (Math v2)
        if self.cfg.inline_calc_enabled:
            from ravan.core.calc import (
                calculate,
                extract_math_expression,
                extract_math_query,
            )

            # Follow-up rounding macro e.g. typing '2' right after '=' calculated 1308.0 -> 1308.00
            if (
                hasattr(self, "_last_calc")
                and self._last_calc is not None
                and (
                    ch.isdigit()
                    or ("\u06f0" <= ch <= "\u06f9")
                    or ch.lower() in ("t", "r", "ت", "ر")
                )
            ):
                expr_prev, res_prev, t_prev = self._last_calc
                if time.monotonic() - t_prev < 2.5:
                    new_res = None
                    if ch.isdigit() or ("\u06f0" <= ch <= "\u06f9"):
                        from ravan.core.normalizer import fa_to_en_digits

                        new_res = calculate(expr_prev, decimals=int(fa_to_en_digits(ch)))
                    elif ch.lower() in ("t", "ت"):
                        new_res = calculate(expr_prev, currency="toman")
                    elif ch.lower() in ("r", "ر"):
                        new_res = calculate(expr_prev, currency="rial")

                    if new_res is not None:
                        self._suppress_until = time.monotonic() + 0.05
                        replace_last_n_with(len(res_prev), new_res)
                        for _ in range(len(res_prev)):
                            if self.journal._chars:
                                self.journal._chars.pop()
                        for c in new_res:
                            self.journal.push(c)
                        self._last_calc = (expr_prev, new_res, time.monotonic())
                        self._record_event(
                            f"Calc v2 macro: '{expr_prev}={ch}' -> '{new_res}'",
                            char=new_res,
                        )
                        return
                else:
                    self._last_calc = None

            if ch == "=":
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
                        self._last_calc = (expr, res, time.monotonic())
                        self._record_event(f"Calc: '{expr}=' -> '{res}'", char=res)
                        log.info("Inline calc: %r= → %r", expr, res)
                        return

            # Direct whole query typing e.g. "1200*1.09=2" or "12000=t"
            if (
                ch.isdigit()
                or ("\u06f0" <= ch <= "\u06f9")
                or ch.lower() in ("t", "r", "ت", "ر")
            ):
                text_with_ch = self.journal.text() + ch
                query_info = extract_math_query(text_with_ch)
                if query_info:
                    expr_part, dec, curr, match_len = query_info
                    if dec is not None or curr is not None:
                        res = calculate(expr_part, decimals=dec, currency=curr)
                        if res is not None:
                            self._suppress_until = time.monotonic() + 0.05
                            erase_n = match_len - 1
                            replace_last_n_with(erase_n, res)
                            for _ in range(erase_n):
                                if self.journal._chars:
                                    self.journal._chars.pop()
                            for c in res:
                                self.journal.push(c)
                            self._last_calc = (expr_part, res, time.monotonic())
                            self._record_event(
                                f"Calc v2: '{expr_part}' -> '{res}'", char=res
                            )
                            log.info("Inline calc v2: %r → %r", expr_part, res)
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

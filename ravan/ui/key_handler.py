"""Low-level keystroke handling, hotkey dispatch, and inline triggers for RavanApp."""

from __future__ import annotations

import logging
import time
from typing import Any

from ravan.platform import keys as _keys
from ravan.platform import winapi as w
from ravan.platform.hook import LLKHF_INJECTED, HookEvent, _is_shift_pressed, set_popup_visible
from ravan.platform.inject import replace_last_n_with
from ravan.platform.keys import is_modifier, matches_hotkey, vk_to_unicode
from ravan.platform.lang import current_language

log = logging.getLogger(__name__)


def _event_has_modifier(event: HookEvent, mod: str) -> bool:
    """Return modifier state captured at hook instant, or live state for synthetic events."""
    mods = getattr(event, "modifiers", None)
    if mods is not None:
        return mod in mods
    if mod == "shift":
        return _is_shift_pressed()
    return _keys.modifiers_down([mod], exact=False)


def _matches_event_hotkey(event: HookEvent, vk: int, spec: Any) -> bool:
    mods = getattr(event, "modifiers", None)
    if mods is not None:
        return matches_hotkey(vk, spec, held_modifiers=mods)
    return matches_hotkey(vk, spec)


class KeyHandlerMixin:
    """Mixin containing keystroke processing and trigger dispatch for RavanApp."""

    def _mark_paste_state(self: Any) -> None:
        """Invalidate tracked typing buffer and suppress auto/next-word predictions on paste."""
        self._select_all_pending = False
        self._last_autocorrect = None
        self._journal_desynced = True
        self._just_pasted = True
        self._pending_predict = False
        if hasattr(self, "journal"):
            self.journal.clear()
        if getattr(self.overlay, "visible", False):
            self.overlay.hide()
        set_popup_visible(False)

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
            self._pending_click_time = None
            if not event.is_key_down:
                if hasattr(self, "_on_key_up"):
                    self._on_key_up(event)
                continue
            if event.flags & LLKHF_INJECTED:
                continue
            # All injected events carry LLKHF_INJECTED and are filtered above; never drop
            # real physical keystrokes via time cooldown or journal desyncs from the screen.
            self._handle_key(event)

    def _handle_key(self: Any, event: HookEvent) -> None:
        # Ignore input inside excluded applications completely
        if hasattr(self, "_is_excluded") and self._is_excluded():
            if self.overlay.visible:
                self.overlay.hide()
                set_popup_visible(False)
            if hasattr(self, "_hide_selection_toolbar"):
                self._hide_selection_toolbar()
            if hasattr(self, "_hide_undo_chip"):
                self._hide_undo_chip()
            if hasattr(self, "journal"):
                self.journal.clear()
            return

        # Suppress all features inside password fields for privacy & security
        from ravan.platform.focus import is_password_focused

        if is_password_focused():
            if self.overlay.visible:
                self.overlay.hide()
                set_popup_visible(False)
            if hasattr(self, "_hide_selection_toolbar"):
                self._hide_selection_toolbar()
            if hasattr(self, "_hide_undo_chip"):
                self._hide_undo_chip()
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

        # Typing dismisses any active language indicator chip instantly (except modifier keys or the hotkey itself)
        if not is_modifier(vk) and not _matches_event_hotkey(event, vk, self.cfg.lang_indicator_hotkey):
            if getattr(self.overlay, "visible", False) and getattr(self.overlay, "_mode", "") == "lang":
                self.overlay.hide()
        if not is_modifier(vk):
            if vk == w.VK_ESCAPE:
                if hasattr(self, "_hide_selection_toolbar"):
                    self._hide_selection_toolbar()
                if hasattr(self, "_hide_undo_chip"):
                    self._hide_undo_chip()
            elif not _event_has_modifier(event, "ctrl") and hasattr(self, "_hide_selection_toolbar"):
                self._hide_selection_toolbar()

        if hasattr(self, "_handle_accent_key") and self._handle_accent_key(event, vk, char):
            return

        if getattr(self, "is_paused", False):
            if hasattr(self.cfg, "pause_hotkey") and _matches_event_hotkey(
                event, vk, self.cfg.pause_hotkey
            ):
                self._ui_queue.put(("toggle_pause", None))
            elif hasattr(self.cfg, "power_mode_hotkey") and _matches_event_hotkey(
                event, vk, self.cfg.power_mode_hotkey
            ):
                self._ui_queue.put(("toggle_power_mode", None))
            return

        # ── Clipboard popup navigation ──
        if self.overlay.clipboard_open:
            is_horizontal = getattr(self.cfg, "prediction_layout", "vertical") == "horizontal"
            if vk == w.VK_ESCAPE:
                self.overlay.hide()
                set_popup_visible(False)
                return
            if vk == w.VK_UP or (is_horizontal and vk == w.VK_LEFT):
                self.overlay.move_selection(-1)
                return
            if vk == w.VK_DOWN or (is_horizontal and vk == w.VK_RIGHT):
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
        elif self.overlay.predicting and not (
            _event_has_modifier(event, "ctrl")
            or _event_has_modifier(event, "alt")
            or _event_has_modifier(event, "win")
        ):
            is_horizontal = getattr(self.cfg, "prediction_layout", "vertical") == "horizontal"
            if vk == w.VK_ESCAPE:
                self.overlay.hide()
                set_popup_visible(False)
                log.info("Prediction popup dismissed by Esc")
                return
            if is_horizontal:
                # In horizontal mode: Left/Right moves between columns; Up/Down accepts the selected word!
                if vk in (w.VK_LEFT, w.VK_RIGHT):
                    cands = getattr(self.overlay, "_candidates", [])
                    if cands:
                        is_rtl = any(ord(ch) > 127 for cand in cands for ch in cand.text[:2])
                    else:
                        lang = current_language()
                        is_rtl = bool(lang and lang.is_persian)
                    step = -1 if (vk == w.VK_RIGHT if is_rtl else vk == w.VK_LEFT) else 1
                    self.overlay.move_selection(step)
                    return
                if vk in (w.VK_UP, w.VK_DOWN):
                    cand = self.overlay.accept_selected()
                    if cand:
                        self._accept_candidate(cand)
                    set_popup_visible(False)
                    return
            else:
                if vk == w.VK_UP:
                    self.overlay.move_selection(-1)
                    return
                if vk == w.VK_DOWN:
                    self.overlay.move_selection(1)
                    return
            if vk in (w.VK_RETURN, w.VK_TAB):
                if vk == w.VK_RETURN:
                    if not getattr(self.cfg, "suggestion_accept_enter", False) or _is_shift_pressed():
                        # Enter when suggestion_accept_enter is False (default) or Shift+Enter:
                        # User wants Enter to pass through to active app (e.g. browser navigation, editor newline).
                        # Dismiss prediction popup, push newline to journal, do NOT accept candidate.
                        self.overlay.hide()
                        set_popup_visible(False)
                        self._last_autocorrect = None
                        self.journal.push("\n")
                        log.debug("Enter passed through to target app; prediction dismissed without accept")
                        return

                cand = self.overlay.accept_selected()
                if cand:
                    self._accept_candidate(cand)
                set_popup_visible(False)
                return
            if not is_horizontal:
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
        if hasattr(self.cfg, "pause_hotkey") and _matches_event_hotkey(event, vk, self.cfg.pause_hotkey):
            self._ui_queue.put(("toggle_pause", None))
            return
        if hasattr(self.cfg, "power_mode_hotkey") and _matches_event_hotkey(event, vk, self.cfg.power_mode_hotkey):
            self._ui_queue.put(("toggle_power_mode", None))
            return
        if hasattr(self.cfg, "quick_stats_hotkey") and _matches_event_hotkey(event, vk, self.cfg.quick_stats_hotkey):
            if not getattr(self, "power_mode_active", False):
                self._ui_queue.put(("quick_stats", None))
            return
        if self.cfg.clipboard_history_enabled and _matches_event_hotkey(event, vk, self.cfg.clipboard_history_hotkey):
            self._show_clipboard_popup()
            return

        if getattr(self, "macro_recorder", None) and self.macro_recorder.is_recording:
            if vk == w.VK_ESCAPE:
                self._ui_queue.put(("stop_macro_recording", None))
                return
            self.macro_recorder.record(vk, char)

        if (
            _matches_event_hotkey(event, vk, getattr(self.cfg, "global_undo_hotkey", None))
            or _matches_event_hotkey(event, vk, self.cfg.undo_autocorrect_hotkey)
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
            (getattr(self.cfg, "clean_clipboard_hotkey", None), self._clean_clipboard_text),
            (getattr(self.cfg, "digits_hotkey", None), self._toggle_digits_selection_or_last_word),
        ):
            if hk is not None and _matches_event_hotkey(event, vk, hk):
                if now - self._last_convert_at > 0.3:
                    self._last_convert_at = now
                    action()
                return

        if _matches_event_hotkey(event, vk, self.cfg.lang_indicator_hotkey):
            if not getattr(self, "power_mode_active", False):
                self._show_lang_indicator()
            return
        for hk_name, fn_name in (
            ("translit_hotkey", "_toggle_translit"),
            ("ai_assistant_hotkey", "_trigger_ai_assistant"),
            ("voice_dictation_hotkey", "_toggle_voice_dictation"),
        ):
            if hasattr(self.cfg, hk_name) and _matches_event_hotkey(event, vk, getattr(self.cfg, hk_name)):
                fn = getattr(self, fn_name, None)
                if fn:
                    fn()
                return

        if is_modifier(vk):
            return

        is_ctrl = _event_has_modifier(event, "ctrl")
        is_alt = _event_has_modifier(event, "alt")
        is_shift = _event_has_modifier(event, "shift")
        is_win = _event_has_modifier(event, "win")

        # Handle Windows-key shortcuts (including Win+V Windows Clipboard History paste)
        if is_win:
            if vk == ord("V"):
                self._mark_paste_state()
            else:
                self._pending_predict = False
                if self.overlay.visible:
                    self.overlay.hide()
                    set_popup_visible(False)
            return

        # Handle Ctrl-based shortcuts and clipboard operations (Copy, Cut, Paste, Select All)
        if is_ctrl and not is_alt:
            # Dismiss any active prediction overlay for application-level Ctrl shortcuts
            if self.overlay.visible:
                self.overlay.hide()
                set_popup_visible(False)
            self._pending_predict = False

            if vk == ord("A"):
                # Ctrl+A (Select All)
                self._select_all_pending = True
                return

            if vk == ord("V"):
                # Ctrl+V (Paste): invalidate journal and suppress unsolicited post-paste predictions
                self._mark_paste_state()
                return

            if vk == ord("X"):
                # Ctrl+X (Cut): invalidate linear journal
                self._select_all_pending = False
                self._last_autocorrect = None
                self._journal_desynced = True
                self.journal.clear()
                return

            if vk == ord("C"):
                # Ctrl+C (Copy)
                self._select_all_pending = False
                return

            # All other Ctrl shortcuts (Ctrl+Z, Ctrl+Y, Ctrl+Tab, Ctrl+T/W/N/L, etc.)
            self._select_all_pending = False
            if vk in (
                ord("Z"),
                ord("Y"),
                w.VK_TAB,
                w.VK_PRIOR,
                w.VK_NEXT,
                ord("T"),
                ord("W"),
                ord("N"),
                ord("L"),
            ):
                self._last_autocorrect = None
                self._journal_desynced = True
                self.journal.clear()
            return

        # Handle plain Alt menu/navigation shortcuts (AltGr sets both Ctrl+Alt so it still types)
        if is_alt and not is_ctrl:
            self._pending_predict = False
            self._select_all_pending = False
            self._last_autocorrect = None
            self._journal_desynced = True
            self.journal.clear()
            if self.overlay.visible:
                self.overlay.hide()
                set_popup_visible(False)
            return

        # Handle Shift+Insert (Standard Windows Paste shortcut)
        if vk == w.VK_INSERT and is_shift and not is_ctrl and not is_alt:
            self._mark_paste_state()
            return

        # Context-menu key should dismiss popups without altering typed state
        if vk == getattr(w, "VK_APPS", 0x5D):
            self._pending_predict = False
            if self.overlay.visible:
                self.overlay.hide()
                set_popup_visible(False)
            return

        # Tab when prediction popup is not active switches UI field or indents
        if vk == w.VK_TAB and not is_ctrl and not is_alt:
            self._select_all_pending = False
            self._last_autocorrect = None
            self._journal_desynced = True
            self.journal.clear()
            self._pending_predict = False
            if self.overlay.visible:
                self.overlay.hide()
                set_popup_visible(False)
            return

        # Caret movement / Forward Delete keys invalidate the linear journal buffer
        if vk in (w.VK_DELETE, w.VK_HOME, w.VK_END, w.VK_PRIOR, w.VK_NEXT, w.VK_LEFT, w.VK_RIGHT, w.VK_UP, w.VK_DOWN):
            self._select_all_pending = False
            self._last_autocorrect = None
            self._journal_desynced = True
            self.journal.clear()
            self._pending_predict = False
            if self.overlay.visible:
                self.overlay.hide()
                set_popup_visible(False)
            return

        if vk == w.VK_ESCAPE:
            self._select_all_pending = False
            if self._last_autocorrect is not None:
                orig, corrected, t_done, delim = self._last_autocorrect
                if time.monotonic() - t_done < 4.0 and self._undo_last_autocorrect():
                    return
            self._last_autocorrect = None
            return

        if vk == w.VK_BACK:
            self._last_key_was_backspace = True
            self._edited_since_popup = True
            if getattr(self, "_select_all_pending", False):
                self._select_all_pending = False
                self._last_autocorrect = None
                self.journal.clear()
                self._pending_predict = False
                if self.overlay.visible:
                    self.overlay.hide()
                    set_popup_visible(False)
                return
            if _event_has_modifier(event, "ctrl"):
                self._last_autocorrect = None
                self._journal_desynced = True
                self.journal.pop_last_word_info(allow_trailing_spaces=True)
            else:
                if hasattr(self, "_undo_last_correction_from_backspace"):
                    if self._undo_last_correction_from_backspace():
                        return
                if self._last_autocorrect is not None:
                    orig, corrected, t_done, delim = self._last_autocorrect
                    if time.monotonic() - t_done < 4.0 and self._undo_last_autocorrect():
                        return
                self._last_autocorrect = None
                self.journal.push("\b")
            # Check remaining prefix of the current word after backspace:
            # If the word is now empty or shorter than min_prefix_len, immediately hide popup
            # and DO NOT trigger next-word prediction on Backspace!
            rem_word = self.journal.last_word()
            if len(rem_word) < self.cfg.min_prefix_len:
                self._pending_predict = False
                if self.overlay.visible:
                    self.overlay.hide()
                    set_popup_visible(False)
                if (
                    getattr(self, "_uia_resync_enabled", False) is True
                    and getattr(self, "_journal_desynced", False)
                    and not getattr(self, "_just_pasted", False)
                ):
                    self._schedule_predict()
                return
            self._schedule_predict()
            return

        self._last_key_was_backspace = False
        if getattr(self, "_select_all_pending", False):
            self._select_all_pending = False
            self.journal.clear()

        if vk == w.VK_RETURN:
            self._last_autocorrect = None
            self.journal.push("\n")
            if self.overlay.predicting or self.overlay.visible:
                self.overlay.hide()
                set_popup_visible(False)
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

            mods = getattr(event, "modifiers", None)
            shift_only = (
                mods == frozenset({"shift"})
                if mods is not None
                else _keys.modifiers_down(["shift"], exact=True)
            )
            if shift_only:
                self._suppress_until = time.monotonic() + 0.05
                # The delivered space is already in the target buffer: erase it and
                # insert the ZWNJ in its place (same accounting as auto-ZWNJ below).
                replace_last_n_with(1, ZWNJ)
                self.journal.push(ZWNJ)
                self.overlay.hide()
                set_popup_visible(False)
                return

        # Regular typing: reuse decoded unicode char from above and filter control chars
        ch = char
        if not ch or (len(ch) == 1 and ord(ch) < 32 and ch not in ("\r", "\n", "\t")):
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
                        # +1: the macro char that triggered this path was delivered to
                        # the target app before our backspaces reach the input queue.
                        replace_last_n_with(len(res_prev) + 1, new_res)
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
                        # The '=' key itself was delivered to the target app, and any
                        # trailing spaces are part of the journal buffer as well.
                        trail = len(text_buf) - len(text_buf.rstrip(" "))
                        self._suppress_until = time.monotonic() + 0.05
                        replace_last_n_with(len(expr) + trail + 1, res)
                        for _ in range(len(expr) + trail):
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
                            # match_len covers the whole typed span including the char
                            # just delivered to the target app; the journal holds all
                            # of it except that final character.
                            self._suppress_until = time.monotonic() + 0.05
                            replace_last_n_with(match_len, res)
                            for _ in range(match_len - 1):
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
        if self.cfg.fix_punctuation_spacing and ch in ".,!?:؛،؟)»]":
            lang = current_language()
            if lang and lang.tag == "fa":
                text_buf = self.journal.text()
                if len(text_buf) >= 2 and text_buf[-1] == " " and text_buf[-2] not in (" ", "\n"):
                    self._suppress_until = time.monotonic() + 0.05
                    # Delivered punctuation + the stray space are both in the target
                    # buffer: erase both and re-inject the punctuation.
                    replace_last_n_with(2, ch)
                    if self.journal._chars:
                        self.journal._chars.pop()
                    self._record_event(f"Fixed spacing before punctuation '{ch}'")

        # Auto-insert space before opening brackets/quotes if typed immediately after a word (e.g. "کتاب(" -> "کتاب (")
        if self.cfg.fix_punctuation_spacing and ch in "(«[":
            lang = current_language()
            if lang and lang.tag == "fa":
                text_buf = self.journal.text()
                if text_buf and text_buf[-1] not in (" ", "\n", "(", "«", "[", "\t"):
                    self._suppress_until = time.monotonic() + 0.05
                    # The delivered bracket is already in the target buffer: erase it
                    # and re-insert as " <bracket>".
                    replace_last_n_with(1, " " + ch)
                    self.journal.push(" ")

        # Smart contextual Persian punctuation (e.g. ? -> ؟, , -> ،, ; -> ؛)
        smart_punct_ok = (
            self._effective_smart_punctuation()
            if hasattr(self, "_effective_smart_punctuation")
            else bool(self.cfg.smart_punctuation_enabled)
        )
        if smart_punct_ok and ch in "?,;":
            lang = current_language()
            if lang and lang.tag == "fa":
                text_buf = self.journal.text()
                last_ch = text_buf[-1] if text_buf else ""
                from ravan.core.predictor import is_arabic_persian

                if is_arabic_persian(last_ch) or (
                    last_ch == " " and len(text_buf) >= 2 and is_arabic_persian(text_buf[-2])
                ):
                    mapping = {"?": "؟", ",": "،", ";": "؛"}
                    target_p = mapping.get(ch)
                    if target_p:
                        word_before_p = self.journal.last_word(allow_trailing_spaces=False)
                        self._suppress_until = time.monotonic() + 0.05
                        # The delivered ASCII punctuation is already in the target
                        # buffer: erase it and inject the Persian equivalent.
                        replace_last_n_with(1, target_p)
                        self.journal.push(target_p)
                        auto_zwnj_ok = (
                            self._effective_auto_zwnj()
                            if hasattr(self, "_effective_auto_zwnj")
                            else bool(self.cfg.auto_zwnj_enabled)
                        )
                        fixed_p = False
                        if auto_zwnj_ok and hasattr(self, "_maybe_apply_live_zwnj"):
                            fixed_p = self._maybe_apply_live_zwnj(word_before_p, delimiter=target_p)
                        if not fixed_p and hasattr(self, "_maybe_apply_live_orthography"):
                            self._maybe_apply_live_orthography(word_before_p, delimiter=target_p)
                        self._record_event(f"Smart Persian punctuation conversion: '{target_p}'")
                        self.overlay.hide()
                        set_popup_visible(False)
                        return

        if self._last_autocorrect is not None:
            if time.monotonic() - self._last_autocorrect[2] > 4.0 or ch.isalnum():
                self._last_autocorrect = None

        if ch.isspace() or ch in ".,;:!?\n\r\t،؛؟)»]":
            word = self.journal.last_word(allow_trailing_spaces=False)

            auto_zwnj_ok = (
                self._effective_auto_zwnj()
                if hasattr(self, "_effective_auto_zwnj")
                else bool(self.cfg.auto_zwnj_enabled)
            )
            # Auto ZWNJ for Persian prefix (e.g. می + space -> می‌)
            if ch == " " and auto_zwnj_ok:
                from ravan.core.orthography import is_token_blacklisted
                from ravan.core.zwnj import ZWNJ, is_zwnj_prefix

                bl = getattr(self.cfg, "zwnj_orthography_blacklist", [])
                if is_zwnj_prefix(word) and not is_token_blacklisted(word, bl):
                    self._suppress_until = time.monotonic() + 0.05
                    replace_last_n_with(1, ZWNJ)
                    self.journal.push(ZWNJ)
                    self.overlay.hide()
                    set_popup_visible(False)
                    return

            handled = self._on_word_completed(word, delimiter=ch)
            if not handled:
                self.journal.push(ch)
                auto_zwnj_ok = (
                    self._effective_auto_zwnj()
                    if hasattr(self, "_effective_auto_zwnj")
                    else bool(self.cfg.auto_zwnj_enabled)
                )
                fixed_live = False
                # Auto ZWNJ for Persian suffixes, compounds, and joined words
                if auto_zwnj_ok and ch not in "\r\n":
                    if hasattr(self, "_maybe_apply_live_zwnj"):
                        fixed_live = self._maybe_apply_live_zwnj(word, delimiter=ch)
                    elif ch == " " and hasattr(self, "_maybe_attach_suffix_zwnj"):
                        fixed_live = bool(self._maybe_attach_suffix_zwnj(word))
                if not fixed_live and ch not in "\r\n" and hasattr(self, "_maybe_apply_live_orthography"):
                    self._maybe_apply_live_orthography(word, delimiter=ch)
            self.overlay.hide()
            set_popup_visible(False)
            should_predict_next = False
            if (
                self.cfg.next_word_prediction
                and ch == " "
                and word
                and not getattr(self, "_just_pasted", False)
            ):
                from ravan.core.normalizer import is_valid_prediction_context_word

                prev_word_fn = getattr(self.journal, "previous_word", None)
                last_token = prev_word_fn() if callable(prev_word_fn) else word
                if not isinstance(last_token, str) or not last_token:
                    last_token = word
                should_predict_next = is_valid_prediction_context_word(last_token)
            if should_predict_next:
                self._schedule_predict()
            return

        if ch.isalpha():
            self._just_pasted = False
        self.journal.push(ch)
        if hasattr(self, "_maybe_autofix_mid_word"):
            cur_word = self.journal.last_word(allow_trailing_spaces=False)
            if cur_word and len(cur_word) >= 4:
                if self._maybe_autofix_mid_word(cur_word):
                    self.overlay.hide()
                    set_popup_visible(False)
                    return
        cur_after = self.journal.last_word(allow_trailing_spaces=False)
        if isinstance(cur_after, str) and cur_after:
            from ravan.core.normalizer import is_numeric_or_symbol_token

            if is_numeric_or_symbol_token(cur_after):
                self._pending_predict = False
                if self.overlay.visible:
                    self.overlay.hide()
                    set_popup_visible(False)
                return
        self._schedule_predict()

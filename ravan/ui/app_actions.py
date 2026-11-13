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
        """Convert selected text if any exists; otherwise convert the last typed sentence or word(s)."""
        from ravan.platform.clipboard import try_convert_selection

        self._suppress_until = time.monotonic() + 0.03
        if try_convert_selection(self.mapper.convert_text):
            log.info("Converted selected text layout")
            self._f12_last_converted = None
            self._f12_repeat_count = 0
            from ravan.core.layout import is_persian_or_arabic
            from ravan.platform.clipboard import get_clipboard_text

            clip_now = get_clipboard_text() or ""
            if any(is_persian_or_arabic(c) for c in clip_now):
                self._maybe_switch_keyboard_layout("fa")
            elif any("a" <= c.lower() <= "z" for c in clip_now):
                self._maybe_switch_keyboard_layout("en")
            return

        now = time.monotonic()
        convert_scope = getattr(self.cfg, "convert_scope", "sentence")

        if convert_scope == "sentence":
            self._convert_last_sentence()
            return

        # Word-by-word expansion mode
        if (
            hasattr(self, "_f12_last_converted")
            and self._f12_last_converted is not None
            and now - getattr(self, "_last_f12_time", 0.0) < 1.5
        ):
            self._f12_repeat_count = getattr(self, "_f12_repeat_count", 1) + 1
            prev_conv_len, prev_orig_text = self._f12_last_converted
            self._suppress_until = now + 0.03
            replace_last_n_with(prev_conv_len, prev_orig_text)
            self.journal.pop_last_n_chars(prev_conv_len)
            for ch in prev_orig_text:
                self.journal.push(ch)
            time.sleep(0.02)
        else:
            self._f12_repeat_count = 1

        self._last_f12_time = time.monotonic()
        self._convert_last_n_words(self._f12_repeat_count)

    def _convert_last_sentence(self: Any) -> None:
        """Convert the last typed sentence/phrase in the active line with instant toggle-back."""
        now = time.monotonic()
        # Toggle back (instant undo / redo) if pressed repeatedly within 2.0 seconds
        if (
            hasattr(self, "_f12_last_converted")
            and self._f12_last_converted is not None
            and now - getattr(self, "_last_f12_time", 0.0) < 2.0
        ):
            prev_conv_len, prev_orig_text = self._f12_last_converted
            self._suppress_until = now + 0.03
            replace_last_n_with(prev_conv_len, prev_orig_text)
            self.journal.pop_last_n_chars(prev_conv_len)
            for ch in prev_orig_text:
                self.journal.push(ch)
            self._last_f12_time = now
            from ravan.core.layout import is_persian_or_arabic

            target_lang = "fa" if any(is_persian_or_arabic(c) for c in prev_orig_text) else "en"
            self._maybe_switch_keyboard_layout(target_lang)
            self._f12_last_converted = None
            log.info("Toggled last sentence back to: %r", prev_orig_text)
            return

        span_text, span_len = (
            self.journal.last_sentence_span()
            if hasattr(self.journal, "last_sentence_span")
            else self.journal.last_n_words_span(1)
        )
        if not span_text or span_len <= 0:
            self._f12_last_converted = None
            return

        converted = self.mapper.convert_text(span_text)
        if not converted or converted == span_text:
            log.info("No conversion for sentence %r", span_text)
            self._f12_last_converted = None
            return

        log.info("Convert sentence: %r → %r", span_text, converted)
        self._suppress_until = time.monotonic() + 0.03
        replace_last_n_with(span_len, converted)
        self.journal.pop_last_n_chars(span_len)
        for ch in converted:
            self.journal.push(ch)
        self._f12_last_converted = (len(converted), span_text)
        self._last_f12_time = now

        # Switch keyboard layout to match converted text
        from ravan.core.layout import is_persian_or_arabic

        target_lang = "fa" if any(is_persian_or_arabic(c) for c in converted) else "en"
        self._maybe_switch_keyboard_layout(target_lang)

    def _maybe_switch_keyboard_layout(self: Any, lang_tag: str) -> bool:
        """Switch active Windows keyboard layout to 'fa' or 'en'."""
        try:
            from ravan.platform.lang import switch_to_language

            return switch_to_language(lang_tag)
        except Exception:
            log.debug("Failed switching keyboard layout to %s", lang_tag, exc_info=True)
            return False

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
        self._suppress_until = time.monotonic() + 0.03
        replace_last_n_with(span_len, converted)
        self.journal.pop_last_n_chars(span_len)
        for ch in converted:
            self.journal.push(ch)
        self._f12_last_converted = (len(converted), span_text)

        # Switch keyboard layout to match converted text
        from ravan.core.layout import is_persian_or_arabic

        target_lang = "fa" if any(is_persian_or_arabic(c) for c in converted) else "en"
        self._maybe_switch_keyboard_layout(target_lang)

    def _normalize_selection_or_last_word(self: Any) -> None:
        """Normalize Persian text in selection or the last typed word."""
        from ravan.core.transform import normalize_text
        from ravan.platform.clipboard import try_convert_selection

        self._suppress_until = time.monotonic() + 0.03
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
        self._suppress_until = time.monotonic() + 0.03
        trailing_str = " " * trailing
        replace_last_n_with(len(word) + trailing, normalized + trailing_str)
        self.journal.pop_last_word_info(allow_trailing_spaces=True)
        for ch in normalized + trailing_str:
            self.journal.push(ch)

    def _toggle_digits_selection_or_last_word(self: Any) -> None:
        """Toggle digits between English and Persian in selection or the last typed word."""
        from ravan.core.normalizer import toggle_digits
        from ravan.platform.clipboard import try_convert_selection

        self._suppress_until = time.monotonic() + 0.03
        if try_convert_selection(toggle_digits):
            log.info("Toggled digits of selected text")
            return
        self._toggle_digits_last_word()

    def _toggle_digits_last_word(self: Any) -> None:
        from ravan.core.normalizer import toggle_digits

        word, trailing = self.journal.last_word_info(allow_trailing_spaces=True)
        if not word:
            return
        converted = toggle_digits(word)
        if not converted or converted == word:
            return
        log.info("Toggle digits %r → %r (trailing: %d)", word, converted, trailing)
        self._suppress_until = time.monotonic() + 0.03
        trailing_str = " " * trailing
        replace_last_n_with(len(word) + trailing, converted + trailing_str)
        self.journal.pop_last_word_info(allow_trailing_spaces=True)
        for ch in converted + trailing_str:
            self.journal.push(ch)

    def _cycle_case_selection_or_last_word(self: Any) -> None:
        """Cycle case (UPPER -> lower -> Title) of selection or last typed word."""
        from ravan.core.transform import cycle_case
        from ravan.platform.clipboard import try_convert_selection

        self._suppress_until = time.monotonic() + 0.03
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
        self._suppress_until = time.monotonic() + 0.03
        trailing_str = " " * trailing
        replace_last_n_with(len(word) + trailing, cased + trailing_str)
        self.journal.pop_last_word_info(allow_trailing_spaces=True)
        for ch in cased + trailing_str:
            self.journal.push(ch)

    def _show_lang_indicator(self: Any, use_mouse_pos: bool = False) -> None:
        lang = current_language()
        if lang is None:
            return
        label = language_label(lang)
        if getattr(self.cfg, "translit_enabled", False):
            label = f"{label}-TL"
        placement = getattr(self.cfg, "lang_indicator_placement", "bottom_right")
        if placement in ("bottom_right", "bottom_left", "top_right", "top_left"):
            # Fixed anchor (default: bottom-right, just above the tray icons).
            self.overlay.show_language(label, -1, -1, 16, placement=placement)
            self._popup_shown_at = time.monotonic()
            return
        if use_mouse_pos:
            try:
                from ravan.platform.caret import _cursor_position

                cp = _cursor_position()
                cx, cy, ch = cp.x, cp.y, cp.height
            except Exception:
                caret = get_caret_rect()
                cx, cy, ch = caret.x, caret.y, caret.height
        else:
            caret = get_caret_rect()
            cx, cy, ch = caret.x, caret.y, caret.height
            if cx <= 1 and cy <= 1:
                try:
                    from ravan.platform.caret import _cursor_position

                    cp = _cursor_position()
                    cx, cy, ch = cp.x, cp.y, cp.height
                except Exception:
                    pass
        self.overlay.show_language(label, cx, cy, ch)
        # Stamp the popup timer so _maybe_timeout_popup does not hide the chip
        # on the next loop tick (hotkey and mouse-click paths both come here).
        self._popup_shown_at = time.monotonic()

    def _show_clipboard_popup(self: Any) -> None:
        from ravan.platform.hook import set_popup_visible

        items = self.clip_history.items()
        if not items:
            self.tray.notify("Clipboard history is empty")
            return
        caret = get_caret_rect()
        self.overlay.show_clipboard(items, caret.x, caret.y, caret.height)
        is_horiz = getattr(self.cfg, "prediction_layout", "vertical") == "horizontal"
        set_popup_visible(
            True,
            swallow_digits=self.cfg.quickpick_digits,
            swallow_arrow="both" if is_horiz else None,
        )
        self._popup_shown_at = time.monotonic()
        log.info("Showing clipboard popup with %d items", len(items))

    def _paste_clipboard_item(self: Any, text: str) -> None:
        from ravan.platform.clipboard import set_clipboard_text
        from ravan.platform.hook import set_popup_visible
        from ravan.platform.inject import send_shortcut

        self._suppress_until = time.monotonic() + 0.03
        self._just_pasted = True
        self._journal_desynced = True
        self._pending_predict = False
        self._last_autocorrect = None
        if hasattr(self, "journal"):
            self.journal.clear()
        if hasattr(self, "overlay") and getattr(self.overlay, "visible", False):
            self.overlay.hide()
            set_popup_visible(False)
        set_clipboard_text(text)
        time.sleep(0.02)
        send_shortcut([w.VK_CONTROL], ord("V"))
        log.info("Pasted clipboard item (%d chars)", len(text))

    def _clean_clipboard_text(self: Any) -> bool:
        from ravan.core.normalizer import clean_pasted_text
        from ravan.platform.clipboard import get_clipboard_text, set_clipboard_text

        raw = get_clipboard_text()
        if not raw or not raw.strip():
            self._show_toast("کلیپ‌بورد خالی است")
            return False

        raw_digit_mode = getattr(self.cfg, "digit_mode", "auto")
        digit_mode = raw_digit_mode if raw_digit_mode in ("auto", "fa", "en", "keep") else "auto"
        cleaned = clean_pasted_text(raw, digit_mode=digit_mode)
        if cleaned == raw:
            self._show_toast("متن کلیپ‌بورد از قبل استاندارد است")
            return True

        set_clipboard_text(cleaned)
        self._record_event(f"Cleaned clipboard text ({len(raw)} -> {len(cleaned)} chars)")
        self._show_toast("متن کلیپ‌بورد پاک‌سازی و استاندارد شد")
        log.info("Cleaned clipboard text: %d chars -> %d chars", len(raw), len(cleaned))
        return True

    def _current_profile(self: Any):
        from ravan.core.profiles import resolve_effective_profile

        cfg = getattr(self, "cfg", None)
        if cfg is None:
            from ravan.core.config import Config

            cfg = Config()
        return resolve_effective_profile(cfg, getattr(self, "_current_exe", None))

    def _effective_auto_zwnj(self: Any) -> bool:
        return self._current_profile().auto_zwnj

    def _effective_orthography_guard(self: Any) -> bool:
        return self._current_profile().orthography_guard

    def _effective_smart_punctuation(self: Any) -> bool:
        return self._current_profile().smart_punctuation

    def _effective_prediction_enabled(self: Any) -> bool:
        return self._current_profile().prediction_enabled

    def _effective_autofix_enabled(self: Any) -> bool:
        return self._current_profile().autofix_enabled

    def _effective_selection_toolbar(self: Any) -> bool:
        return self._current_profile().selection_toolbar

    def _hide_selection_toolbar(self: Any) -> None:
        tb = getattr(self, "selection_toolbar", None)
        if tb is not None and getattr(tb, "visible", False) is True and callable(getattr(tb, "hide", None)):
            tb.hide()

    def _hide_undo_chip(self: Any) -> None:
        chip = getattr(self, "undo_chip", None)
        if chip is not None and getattr(chip, "visible", False) is True and callable(getattr(chip, "hide", None)):
            chip.hide()

    def _popup_avoid_rects(self: Any, exclude: Any = None) -> list[tuple[int, int, int, int]]:
        rects: list[tuple[int, int, int, int]] = []
        for attr in ("overlay", "undo_chip", "selection_toolbar"):
            w_obj = getattr(self, attr, None)
            if w_obj is None or w_obj is exclude:
                continue
            if getattr(w_obj, "visible", False) is not True:
                continue
            bounds_fn = getattr(w_obj, "bounds", None)
            if callable(bounds_fn):
                b = bounds_fn()
                if isinstance(b, tuple) and len(b) == 4:
                    rects.append(b)
                    continue
            top = getattr(w_obj, "_top", None)
            if top is not None:
                try:
                    rx, ry = int(top.winfo_rootx()), int(top.winfo_rooty())
                    rw, rh = int(top.winfo_width()), int(top.winfo_height())
                    if rw > 0 and rh > 0:
                        rects.append((rx, ry, rx + rw, ry + rh))
                except Exception:
                    pass
        return rects

    def _record_quick_undo(
        self: Any,
        *,
        kind: str,
        original: str,
        replacement: str,
        delimiter: str,
        blacklist_token: str = "",
    ) -> None:
        self._last_quick_undo = {
            "kind": kind,
            "original": original,
            "replacement": replacement,
            "delimiter": delimiter,
            "blacklist_token": blacklist_token or original,
            "timestamp": time.monotonic(),
        }
        cfg = getattr(self, "cfg", None)
        if not bool(getattr(cfg, "quick_undo_chip_enabled", True)):
            return
        chip = getattr(self, "undo_chip", None)
        if chip is None or not callable(getattr(chip, "show", None)):
            return
        if hasattr(chip, "parent"):
            ov_root = getattr(getattr(self, "overlay", None), "_root", None)
            if ov_root is not None:
                chip.parent = ov_root
        try:
            from ravan.platform.caret import get_caret_rect

            rect = get_caret_rect()
            cx = getattr(rect, "x", None)
            cy = getattr(rect, "y", None)
        except Exception:
            cx, cy = None, None
        avoid = self._popup_avoid_rects(exclude=chip)
        chip.show(
            replacement=replacement,
            original=original,
            x=cx if isinstance(cx, int) else None,
            y=cy if isinstance(cy, int) else None,
            avoid_rect=avoid[0] if avoid else None,
            duration_ms=2600,
            theme_mode=getattr(cfg, "theme_mode", "auto"),
        )

    def _undo_quick_fix(self: Any) -> bool:
        """Revert the latest ZWNJ/orthography auto-change and persist it to blacklist."""
        rec = getattr(self, "_last_quick_undo", None)
        if not isinstance(rec, dict):
            return False
        self._last_quick_undo = None
        self._hide_undo_chip()

        original = str(rec.get("original", ""))
        replacement = str(rec.get("replacement", ""))
        delimiter = str(rec.get("delimiter", ""))
        token = str(rec.get("blacklist_token", original))
        kind = str(rec.get("kind", "zwnj"))
        if not replacement:
            return False

        delete_n = len(replacement) + len(delimiter)
        self._replace_journal_span(delete_n, f"{original}{delimiter}")

        cfg = getattr(self, "cfg", None)
        if cfg is not None and kind in ("zwnj", "orthography"):
            from ravan.core.orthography import add_blacklist_token

            cur_bl = list(getattr(cfg, "zwnj_orthography_blacklist", []))
            updated_bl = add_blacklist_token(cur_bl, token)
            cfg.zwnj_orthography_blacklist = updated_bl
            try:
                from ravan.core.config import save_config

                save_config(cfg)
            except Exception as exc:  # noqa: BLE001
                log.debug("Failed to save ZWNJ/orthography blacklist: %s", exc)
        return True

    def _on_selection_toolbar_action(self: Any, action_id: str) -> None:
        """Handle clicks from Floating Selection Mini-Toolbar without stealing focus."""
        self._suppress_until = time.monotonic() + 0.15
        if action_id == "convert":
            self._convert_selection_or_last_word()
        elif action_id == "normalize":
            from ravan.core.normalizer import normalize_persian
            from ravan.platform.clipboard import try_convert_selection

            smart_punct = self._effective_smart_punctuation()
            use_grammar = self._effective_orthography_guard()

            def _polish(txt: str) -> str:
                return normalize_persian(
                    txt,
                    digits="keep",
                    fix_zwnj=True,
                    fix_spacing=True,
                    fix_punctuation=smart_punct,
                    fix_grammar=use_grammar,
                )

            try_convert_selection(_polish)
        elif action_id == "digits":
            self._toggle_digits_selection_or_last_word()
        elif action_id == "ai":
            if hasattr(self, "_trigger_ai_assistant"):
                self._trigger_ai_assistant()

    def _replace_journal_span(self: Any, delete_n: int, replacement: str) -> None:
        """Replace trailing characters in both active app and journal cleanly."""
        self._suppress_until = time.monotonic() + 0.03
        replace_last_n_with(delete_n, replacement)
        for _ in range(delete_n):
            if self.journal._chars:
                self.journal._chars.pop()
        for c in replacement:
            self.journal.push(c)

    def _dict_contains_fn(self: Any):
        """Return a real Dictionary.contains callable, or None if unavailable/mocked."""
        predictor = getattr(self, "predictor", None)
        fa_dict = getattr(predictor, "persian", None) if predictor is not None else None
        contains_fn = getattr(fa_dict, "contains", None)
        if callable(contains_fn) and isinstance(contains_fn(""), bool):
            return contains_fn
        return None

    def _maybe_apply_live_zwnj(self: Any, word: str, delimiter: str = " ") -> bool:
        """Apply live Persian ZWNJ rules for compounds, spaced suffixes, and joined words."""
        if not self._effective_auto_zwnj():
            return False
        if not word or delimiter in ("\n", "\r"):
            return False
        if not any("\u0600" <= c <= "\u06ff" for c in word):
            return False
        from ravan.core.orthography import is_token_blacklisted
        from ravan.core.zwnj import (
            ZWNJ,
            fix_joined_zwnj,
            match_trailing_compound,
            should_attach_suffix,
        )

        blacklist = getattr(getattr(self, "cfg", None), "zwnj_orthography_blacklist", [])
        if is_token_blacklisted(word, blacklist):
            return False

        text = self.journal.text()
        if not text or (delimiter and not text.endswith(delimiter)):
            return False
        text_before_delim = text[: -len(delimiter)] if delimiter else text

        # 1. Multi-word spaced compounds (e.g. برنامه نویس -> برنامه‌نویس, گفت و گو -> گفت‌وگو)
        comp = match_trailing_compound(text_before_delim)
        if comp is not None:
            phrase, fixed_comp = comp
            if fixed_comp != phrase and not is_token_blacklisted(phrase, blacklist):
                delete_n = len(phrase) + len(delimiter)
                self._replace_journal_span(delete_n, f"{fixed_comp}{delimiter}")
                self._record_quick_undo(
                    kind="zwnj",
                    original=phrase,
                    replacement=fixed_comp,
                    delimiter=delimiter,
                    blacklist_token=phrase,
                )
                log.info("Attached compound ZWNJ: %r -> %r", phrase, fixed_comp)
                return True

        # 2. Spaced suffix attached to previous word (e.g. کتاب ها، -> کتاب‌ها،)
        if word and word.strip() == word and text_before_delim.endswith(f" {word}"):
            before_space = text_before_delim[: -len(word) - 1]
            i = len(before_space) - 1
            while i >= 0 and not before_space[i].isspace():
                i -= 1
            prev_word = before_space[i + 1 :]
            orig_span = f"{prev_word} {word}"
            if (
                prev_word
                and should_attach_suffix(prev_word, word)
                and not is_token_blacklisted(orig_span, blacklist)
            ):
                delete_n = len(word) + 1 + len(delimiter)
                self._replace_journal_span(delete_n, f"{ZWNJ}{word}{delimiter}")
                self._record_quick_undo(
                    kind="zwnj",
                    original=orig_span,
                    replacement=f"{prev_word}{ZWNJ}{word}",
                    delimiter=delimiter,
                    blacklist_token=orig_span,
                )
                log.info("Attached suffix ZWNJ: %r + %r", prev_word, word)
                return True

        # 3. Joined words typed without space (e.g. میروم -> می‌روم, برنامهها -> برنامه‌ها)
        if word and text_before_delim.endswith(word):
            fixed_joined = fix_joined_zwnj(word, dict_contains=self._dict_contains_fn())
            if fixed_joined and fixed_joined != word:
                delete_n = len(word) + len(delimiter)
                self._replace_journal_span(delete_n, f"{fixed_joined}{delimiter}")
                self._record_quick_undo(
                    kind="zwnj",
                    original=word,
                    replacement=fixed_joined,
                    delimiter=delimiter,
                    blacklist_token=word,
                )
                log.info("Fixed joined ZWNJ: %r -> %r", word, fixed_joined)
                return True

        return False

    def _maybe_apply_live_orthography(self: Any, word: str, delimiter: str = " ") -> bool:
        """Apply real-time Persian Orthography Guard rules on completed words."""
        if not self._effective_orthography_guard():
            return False
        if not word or delimiter in ("\n", "\r"):
            return False
        cfg = getattr(self, "cfg", None)
        if cfg is not None and callable(getattr(cfg, "is_word_ignored", None)) and cfg.is_word_ignored(word):
            return False

        from ravan.core.orthography import check_live_orthography

        text = self.journal.text()
        if not text or (delimiter and not text.endswith(delimiter)):
            return False
        text_before_delim = text[: -len(delimiter)] if delimiter else text
        recent_words = text_before_delim.split()[-4:]

        mode = str(getattr(cfg, "orthography_guard_mode", "safe"))
        blacklist = getattr(cfg, "zwnj_orthography_blacklist", [])
        sug = check_live_orthography(
            word,
            recent_words=recent_words,
            mode=mode,
            blacklist=blacklist,
        )
        if sug is None or sug.replacement == sug.original:
            return False
        if not text_before_delim.endswith(sug.original):
            return False

        delete_n = len(sug.original) + len(delimiter)
        self._replace_journal_span(delete_n, f"{sug.replacement}{delimiter}")
        self._record_quick_undo(
            kind="orthography",
            original=sug.original,
            replacement=sug.replacement,
            delimiter=delimiter,
            blacklist_token=sug.original,
        )
        log.info("Orthography Guard (%s): %r -> %r", sug.reason, sug.original, sug.replacement)
        return True

    def _maybe_attach_suffix_zwnj(self: Any, suffix: str, delimiter: str = " ") -> bool:
        return self._maybe_apply_live_zwnj(suffix, delimiter=delimiter)

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
        self._suppress_until = time.monotonic() + 0.03

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

    def toggle_power_mode(
        self: Any, duration_min: int | None = None, force_state: bool | None = None
    ) -> bool:
        """Toggle Power Mode (Focus Typing) to suppress all popups."""
        self.power_mode_active = (
            bool(force_state)
            if force_state is not None
            else not getattr(self, "power_mode_active", False)
        )
        from ravan.core.i18n import t

        if self.power_mode_active:
            self._pending_predict = False
            self.overlay.hide()
            from ravan.ui.app import set_popup_visible

            set_popup_visible(False)
            if hasattr(self, "_hide_selection_toolbar"):
                self._hide_selection_toolbar()
            if hasattr(self, "_hide_undo_chip"):
                self._hide_undo_chip()
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
            if hasattr(self, "_ui_queue") and self._ui_queue is not None:
                self._ui_queue.put(("toggle_power_mode", None))
            else:
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


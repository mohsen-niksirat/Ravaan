"""Autofix and unified undo mixin for RavanApp."""

from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger(__name__)


class AppAutofixMixin:
    """Mixin containing automatic wrong-layout correction and undo handling."""

    def _init_autofix(self: Any) -> None:
        from ravan.core.autofix import AutoFixEngine
        from ravan.ui.toast import ToastPopup

        self.autofix = AutoFixEngine(
            mapper=self.mapper,
            en_dict=getattr(self.predictor, "english", None),
            fa_dict=getattr(self.predictor, "persian", None),
            user_dict=getattr(self.predictor, "user_dict", None),
            mode=getattr(self.cfg, "autofix_mode", "safe"),
        )
        self.autofix.load_blacklist(getattr(self.cfg, "autofix_blacklist", []))
        self.autofix.app_modes = dict(getattr(self.cfg, "autofix_app_modes", {}))
        self._toast = ToastPopup(
            parent=getattr(self.overlay, "_root", None),
            theme_mode=getattr(self.cfg, "theme_mode", "auto"),
        )
        self._last_autofix_time = 0.0
        from ravan.core.config import config_dir
        from ravan.core.translit import TranslitEngine

        self.translit = TranslitEngine(
            user_dict_path=config_dir() / "user_translit.json"
        )

    def _toggle_translit(self: Any) -> None:
        self.cfg.translit_enabled = not getattr(self.cfg, "translit_enabled", False)
        from ravan.core.config import save_config

        save_config(self.cfg)
        status = "فعال" if self.cfg.translit_enabled else "غیرفعال"
        msg = f"حالت فینگلیش به فارسی {status} شد (Ctrl+Alt+T)"
        self._show_toast(msg)
        self._record_event(f"Toggled transliteration: {status}")

    def _maybe_translit_word(self: Any, word: str, delimiter: str = "") -> bool:
        if not hasattr(self, "translit") or self.translit is None:
            return False
        if not word or any(ord(c) > 127 for c in word):
            return False
        if getattr(self, "power_mode_active", False) or (
            hasattr(self, "_is_excluded") and self._is_excluded()
        ):
            return False

        cands = self.translit.transliterate(word)
        if not cands:
            return False

        top = cands[0]
        self._last_translit_word = (word, top)
        self._last_translit_record = (word, top, delimiter, time.monotonic())
        self._record_event(f"Transliterated: '{word}' -> '{top}'", char=top)
        self._replace_word(word, top, delimiter=delimiter)

        if len(cands) > 1 and hasattr(self, "overlay") and self.overlay is not None:
            from ravan.core.events import Candidate, CandidateKind
            from ravan.platform.caret import get_caret_rect
            from ravan.platform.hook import set_popup_visible

            cand_objs = [
                Candidate(text=c, score=1.0 - i * 0.1, kind=CandidateKind.COMPLETION)
                for i, c in enumerate(cands[:5])
            ]
            caret = get_caret_rect()
            if caret:
                state = {"current_fa": top}

                def _on_pick(cand: Any) -> None:
                    chosen_fa = cand.text
                    curr_fa = state["current_fa"]
                    if chosen_fa != curr_fa:
                        self._accept_translit_candidate(
                            word, curr_fa, chosen_fa, delimiter=delimiter
                        )
                        state["current_fa"] = chosen_fa

                self.overlay.show_predictions(
                    cand_objs,
                    caret.x,
                    caret.y,
                    height=caret.height,
                    on_accept=_on_pick,
                )
                set_popup_visible(True, swallow_digits=self.cfg.quickpick_digits)

        return True

    def _accept_translit_candidate(
        self: Any,
        orig_word: str,
        current_or_chosen_fa: str,
        chosen_fa: str | None = None,
        delimiter: str = "",
    ) -> None:
        if chosen_fa is None:
            current_fa = getattr(self, "_last_translit_word", ("", orig_word))[1] or orig_word
            actual_chosen = current_or_chosen_fa
        else:
            current_fa = current_or_chosen_fa
            actual_chosen = chosen_fa

        if hasattr(self, "translit") and self.translit is not None:
            self.translit.record_pick(orig_word, actual_chosen)
        self._replace_word(current_fa, actual_chosen, delimiter=delimiter)
        self._last_translit_word = (orig_word, actual_chosen)
        self._last_translit_record = (orig_word, actual_chosen, delimiter, time.monotonic())
        self._record_event(
            f"Accepted translit: '{orig_word}' -> '{actual_chosen}'", char=actual_chosen
        )

    def _undo_last_transliteration(self: Any, from_backspace: bool = False) -> bool:
        """Revert the last transliterated word back to its original Finglish."""
        rec = getattr(self, "_last_translit_record", None)
        if rec is None:
            return False
        orig_word, inserted_fa, delimiter, t_done = rec
        self._last_translit_record = None

        max_elapsed = 4.0 if from_backspace else 10.0
        if time.monotonic() - t_done > max_elapsed:
            return False

        del_len = len(inserted_fa) + len(delimiter)
        replace_text = orig_word + delimiter
        self._suppress_until = time.monotonic() + 0.08
        from ravan.platform.inject import replace_last_n_with

        replace_last_n_with(del_len, replace_text)
        for _ in range(del_len):
            if self.journal._chars:
                self.journal._chars.pop()
        for ch in replace_text:
            self.journal.push(ch)

        from ravan.core.i18n import t

        msg = t("toast.translit_undo", f"لغو فینگلیش: {inserted_fa} ← {orig_word}", orig=orig_word)
        self._show_toast(msg)
        self._record_event(f"Undone transliteration: {inserted_fa} -> {orig_word}")
        log.info("Undid transliteration: reverted %r back to %r", inserted_fa, orig_word)
        return True

    def _maybe_autofix_word(self: Any, word: str, delimiter: str = "") -> bool:
        if not hasattr(self, "autofix") or self.autofix is None:
            return False
        if not word or getattr(self, "power_mode_active", False):
            return False
        if hasattr(self, "_is_excluded") and self._is_excluded():
            return False
        from ravan.platform.focus import is_password_focused

        if is_password_focused():
            return False

        active_lang = getattr(self, "_active_layout_tag", "en") or "en"
        app_name = getattr(self, "_current_exe", "") or ""
        prev_context = (
            self.journal.previous_context(2)
            if hasattr(self.journal, "previous_context")
            else None
        )

        fix_res = self.autofix.detect(
            word,
            active_layout=active_lang,
            app_name=app_name,
            context=prev_context,
        )
        if fix_res is None:
            return False

        replacement, target_lang = fix_res
        log.info(
            "Auto-fix wrong layout: %r -> %r (%s -> %s)",
            word,
            replacement,
            active_lang,
            target_lang,
        )
        auto_switch = getattr(self.cfg, "auto_layout_switch", False)
        mode = getattr(self.cfg, "auto_layout_mode", "fix_only")

        can_switch = auto_switch
        if can_switch:
            from ravan.platform.focus import is_password_focused
            from ravan.platform.lang import is_ime_composing

            if (
                (hasattr(self, "_is_excluded") and self._is_excluded())
                or is_password_focused()
                or is_ime_composing()
            ):
                can_switch = False

        if mode == "switch_only":
            if can_switch and hasattr(self, "_maybe_switch_keyboard_layout"):
                self._maybe_switch_keyboard_layout(target_lang)
            return True

        self._last_autofix_time = time.monotonic()
        self.autofix.record_fix(
            original=word,
            fixed=replacement,
            app_name=app_name,
            layout_from=active_lang,
            layout_to=target_lang,
            delimiter=delimiter,
        )
        self._record_event(f"Auto-fix: '{word}' -> '{replacement}'", char=replacement)
        self._replace_word(word, replacement, delimiter=delimiter)

        if can_switch and mode == "fix_and_switch" and hasattr(
            self, "_maybe_switch_keyboard_layout"
        ):
            self._maybe_switch_keyboard_layout(target_lang)

        return True

    def _maybe_autofix_mid_word(self: Any, word: str) -> bool:
        """Evaluate and convert word typed in wrong layout while mid-word."""
        if not hasattr(self, "autofix") or self.autofix is None:
            return False
        if not word or len(word) < 4 or getattr(self, "power_mode_active", False):
            return False
        if hasattr(self, "_is_excluded") and self._is_excluded():
            return False
        from ravan.platform.focus import is_password_focused

        if is_password_focused():
            return False

        active_lang = getattr(self, "_active_layout_tag", "en") or "en"
        app_name = getattr(self, "_current_exe", "") or ""
        prev_context = (
            self.journal.previous_context(2)
            if hasattr(self.journal, "previous_context")
            else None
        )

        fix_res = self.autofix.detect(
            word,
            active_layout=active_lang,
            app_name=app_name,
            context=prev_context,
            mid_word=True,
        )
        if fix_res is None:
            return False

        replacement, target_lang = fix_res
        log.info(
            "Auto-fix wrong layout (mid-word): %r -> %r (%s -> %s)",
            word,
            replacement,
            active_lang,
            target_lang,
        )
        auto_switch = getattr(self.cfg, "auto_layout_switch", False)
        mode = getattr(self.cfg, "auto_layout_mode", "fix_only")

        self._last_autofix_time = time.monotonic()
        self.autofix.record_fix(
            original=word,
            fixed=replacement,
            app_name=app_name,
            layout_from=active_lang,
            layout_to=target_lang,
            delimiter="",
        )
        self._record_event(f"Auto-fix mid-word: '{word}' -> '{replacement}'", char=replacement)
        self._replace_word(word, replacement, delimiter="")

        can_switch = auto_switch
        if can_switch:
            from ravan.platform.lang import is_ime_composing

            if (
                (hasattr(self, "_is_excluded") and self._is_excluded())
                or is_password_focused()
                or is_ime_composing()
            ):
                can_switch = False

        if can_switch and (mode in ("switch_only", "fix_and_switch")) and hasattr(
            self, "_maybe_switch_keyboard_layout"
        ):
            self._maybe_switch_keyboard_layout(target_lang)

        return True

    def _undo_last_correction(self: Any) -> bool:
        """Global undo: reverts the last automatic correction (up to 50 steps)."""
        if hasattr(self, "_undo_last_transliteration") and getattr(self, "_last_translit_record", None):
            return self._undo_last_transliteration(from_backspace=False)
        if hasattr(self, "autofix") and self.autofix is not None:
            rec = self.autofix.pop_last_correction()
            if rec is not None:
                del_len = len(rec.fixed) + len(rec.delimiter)
                replace_text = rec.original + rec.delimiter
                self._suppress_until = time.monotonic() + 0.08
                from ravan.platform.inject import replace_last_n_with

                replace_last_n_with(del_len, replace_text)
                for _ in range(del_len):
                    if self.journal._chars:
                        self.journal._chars.pop()
                for ch in replace_text:
                    self.journal.push(ch)

                blacklisted = self.autofix.record_undo(rec)
                if blacklisted:
                    from ravan.core.config import save_config

                    self.cfg.autofix_blacklist = self.autofix.export_blacklist()
                    save_config(self.cfg)

                msg = f"لغو تصحیح: {rec.fixed} ← {rec.original}"
                self._show_toast(msg)
                self._record_event(f"Undone auto-fix: {rec.fixed} -> {rec.original}")
                log.info("Undid auto-fix: reverted %r back to %r", rec.fixed, rec.original)
                return True

        if hasattr(self, "_undo_last_autocorrect"):
            return self._undo_last_autocorrect()
        return False

    def _undo_last_correction_from_backspace(self: Any) -> bool:
        """Revert the last auto-fix when Backspace is typed immediately (< 2.5s)."""
        if hasattr(self, "_undo_last_transliteration") and getattr(self, "_last_translit_record", None):
            rec = self._last_translit_record
            if time.monotonic() - rec[3] <= 4.0:
                return self._undo_last_transliteration(from_backspace=True)
        if not hasattr(self, "autofix") or self.autofix is None:
            return False
        elapsed = time.monotonic() - getattr(self, "_last_autofix_time", 0.0)
        if not (0.0 <= elapsed <= 2.5):
            return False
        rec = self.autofix.pop_last_correction()
        if rec is None:
            return False

        self.autofix.on_manual_edit(elapsed)
        del_len = len(rec.fixed)
        self._suppress_until = time.monotonic() + 0.08
        from ravan.platform.inject import replace_last_n_with

        replace_last_n_with(del_len, rec.original)
        total_pop = del_len + (1 if rec.delimiter else 0)
        for _ in range(total_pop):
            if self.journal._chars:
                self.journal._chars.pop()
        for ch in rec.original:
            self.journal.push(ch)

        blacklisted = self.autofix.record_undo(rec)
        if blacklisted:
            from ravan.core.config import save_config

            self.cfg.autofix_blacklist = self.autofix.export_blacklist()
            save_config(self.cfg)

        msg = f"لغو تصحیح: {rec.fixed} ← {rec.original}"
        self._show_toast(msg)
        self._record_event(f"Undone auto-fix (backspace): {rec.fixed} -> {rec.original}")
        log.info("Undid auto-fix (backspace): reverted %r back to %r", rec.fixed, rec.original)
        return True

    def _undo_last_autocorrect(self: Any) -> bool:
        if getattr(self, "_last_autocorrect", None) is None:
            return False
        orig, corrected, t_done, delim = self._last_autocorrect
        self._last_autocorrect = None
        if time.monotonic() - t_done > 10.0:
            return False

        delete_len = len(corrected) + len(delim)
        replace_text = orig + delim
        self._suppress_until = time.monotonic() + 0.08
        from ravan.platform.inject import replace_last_n_with

        replace_last_n_with(delete_len, replace_text)

        for _ in range(delete_len):
            if self.journal._chars:
                self.journal._chars.pop()
        for ch in replace_text:
            self.journal.push(ch)

        if hasattr(self, "predictor") and self.predictor:
            self.predictor.suppress_session_word(orig)

        log.info("Undid autocorrect: reverted %r back to %r", corrected, orig)
        self._record_event(f"Undid autocorrect: reverted '{corrected}' -> '{orig}'")
        from ravan.core.i18n import t

        msg = t("notifications.autocorrect_undone", "Reverted to '{orig}'", orig=orig)
        self.tray.notify(msg)
        return True

    def _show_toast_sync(self: Any, message: str) -> None:
        if hasattr(self, "_toast") and self._toast is not None:
            from ravan.platform.caret import get_caret_rect

            rc = get_caret_rect()
            if rc:
                self._toast.show(message, x=rc.x, y=rc.y)
            else:
                self._toast.show(message)
        elif hasattr(self, "tray") and self.tray is not None:
            self.tray.notify(message)

    def _show_toast(self: Any, message: str) -> None:
        import threading
        if threading.current_thread() is not threading.main_thread() and hasattr(self, "_ui_queue"):
            self._ui_queue.put(("toast", message))
            return
        if hasattr(self, "_toast") and self._toast is not None:
            from ravan.platform.caret import get_caret_rect

            rc = get_caret_rect()
            if rc:
                self._toast.show(message, x=rc.x, y=rc.y)
            else:
                self._toast.show(message)
        elif hasattr(self, "tray") and self.tray is not None:
            self.tray.notify(message)

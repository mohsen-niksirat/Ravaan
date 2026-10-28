"""Main Ravan application loop."""

from __future__ import annotations

import logging
import os
import queue
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any

from ravan.core.config import Config, load_config
from ravan.core.events import Candidate
from ravan.core.journal import KeystrokeJournal
from ravan.core.layout import LayoutMapper
from ravan.core.predictor import DictPredictor
from ravan.core.snippet import SnippetEngine
from ravan.platform import winapi as w
from ravan.platform.hook import KeyboardHook, set_popup_visible
from ravan.platform.inject import replace_last_n_with
from ravan.platform.lang import current_language
from ravan.ui.app_accent import AppAccentMixin
from ravan.ui.app_actions import AppActionsMixin
from ravan.ui.app_ai import AppAIMixin
from ravan.ui.app_autofix import AppAutofixMixin
from ravan.ui.app_dialogs import AppDialogsMixin
from ravan.ui.app_polling import AppPollingMixin
from ravan.ui.app_voice import AppVoiceMixin
from ravan.ui.key_handler import KeyHandlerMixin
from ravan.ui.log_setup import setup_logging
from ravan.ui.overlay import OverlayWindow

log = logging.getLogger(__name__)


class RavanApp(
    AppAccentMixin,
    AppActionsMixin,
    AppAIMixin,
    AppAutofixMixin,
    AppDialogsMixin,
    AppPollingMixin,
    AppVoiceMixin,
    KeyHandlerMixin,
):
    def __init__(self, cfg: Config | None = None, overlay: OverlayWindow | None = None) -> None:
        w.enable_dpi_awareness()
        self.cfg = cfg or load_config()
        self.mapper = LayoutMapper()
        self.predictor = DictPredictor.from_config(self.cfg)
        self.snippets = SnippetEngine.from_config(self.cfg)
        self.journal = KeystrokeJournal()
        from ravan.core.cliphistory import ClipboardHistory
        from ravan.core.config import config_dir

        self.clip_history = ClipboardHistory(maxlen=50, storage_path=config_dir() / "clipboard_history.json")
        self.overlay = (
            overlay
            if overlay is not None
            else OverlayWindow(
                self.cfg.theme,
                theme_mode=getattr(self.cfg, "theme_mode", "auto"),
                cfg=self.cfg,
                on_position_changed=self._on_overlay_moved,
            )
        )
        self.hook = KeyboardHook()
        self._ui_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        from ravan.ui.app_tray import create_app_tray

        self.tray = create_app_tray(self)
        self._settings_window: Any = None
        self._diagnostics_window: Any = None
        self._snippet_window: Any = None
        self._wizard_window: Any = None
        self._quick_tips_window: Any = None
        self.recent_events: deque[dict[str, Any]] = deque(maxlen=50)

        self._last_lang_hkl: Any = None
        self._active_layout_tag: Any = None
        self._last_key_time = self._suppress_until = self._last_convert_at = 0.0
        self._popup_shown_at = self._last_focus_poll = self._last_lang_poll = self._last_clip_poll = 0.0
        self._pending_predict = self._running = False
        self._current_exe: Any = None
        self._last_autocorrect: Any = None
        self._own_pid = os.getpid()
        self.is_paused = False
        self._pause_timer: Any = None
        from ravan.ui.hint_manager import HintManager

        self.hint_manager = HintManager(self.cfg, on_show_toast=getattr(self, "_show_toast", None))
        self._init_autofix()
        self._init_accent()
        self._init_ai()
        self._init_voice()

    def start(self) -> None:
        t0 = time.perf_counter()
        setup_logging()
        from ravan.ui.log_setup import install_crash_handler

        install_crash_handler(on_crash=lambda msg: self.tray.notify(msg, title="Ravaan Error"))
        log.info("Starting Ravan")
        log.info(
            "Suggestions: type 2+ letters → ↑/↓ select → Enter/Tab accept "
            "(or press 1–5). Esc closes. %s converts layout.",
            self.cfg.convert_hotkey.key,
        )
        self._running = True
        self.hook.start()
        self.tray.start()
        lang = current_language()
        if lang:
            self._last_lang_hkl = lang.hkl
            self._active_layout_tag = lang.tag
        if not self.cfg.has_seen_onboarding:
            self._show_onboarding()
        startup_ms = (time.perf_counter() - t0) * 1000
        log.info("RavanApp startup completed in %.1f ms", startup_ms)
        try:
            while self._running:
                try:
                    self._drain_ui_actions()
                    self._drain_hook_events()
                    self._poll_focus()
                    self._poll_hook_health()
                    self._poll_language()
                    self._poll_clipboard()
                    self._poll_background_sync()
                    self._maybe_predict()
                    self._maybe_timeout_popup()
                    self.overlay.tick()
                    for win in (self._settings_window, self._diagnostics_window, self._snippet_window, self._wizard_window, self._quick_tips_window):
                        if win is not None:
                            win.tick()
                except Exception:  # noqa: BLE001
                    log.exception("Main loop iteration failed")
                time.sleep(0.008)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        if threading.current_thread() is not threading.main_thread():
            self._ui_queue.put(("quit", None))
            return
        if not self._running:
            return
        log.info("Stopping Ravan")
        self._running = False
        set_popup_visible(False)
        self.overlay.hide()
        self.hook.stop()
        self.tray.stop()
        try:
            self.overlay.destroy()
        except Exception:  # noqa: BLE001
            pass

    def _record_event(self, action: str, vk: int = 0, char: str = "") -> None:
        now_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        vk_str = f"0x{vk:02X}" if vk else ""
        lang = current_language()
        tag = (lang.tag if lang else "en").upper()
        self.recent_events.append(
            {"time": now_str, "vk": vk_str, "char": char, "layout": tag, "action": action}
        )

    def _on_settings_saved(self, cfg: Config) -> None:
        self.cfg = cfg
        self.predictor = DictPredictor.from_config(cfg)
        self.snippets = SnippetEngine.from_config(cfg)
        if hasattr(self.overlay, "apply_config"):
            self.overlay.apply_config(cfg)
        elif hasattr(self.overlay, "set_theme_mode"):
            self.overlay.set_theme_mode(cfg.theme_mode)
        if hasattr(self, "autofix") and self.autofix is not None:
            self.autofix.mode = getattr(cfg, "autofix_mode", "safe")
            self.autofix.load_blacklist(getattr(cfg, "autofix_blacklist", []))
            self.autofix.app_modes = dict(getattr(cfg, "autofix_app_modes", {}))
        self._init_accent()
        log.info("Settings updated")

    def _undo_last_autocorrect(self) -> bool:
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

        if hasattr(self, "predictor") and self.predictor:
            self.predictor.suppress_session_word(orig)

        log.info("Undid autocorrect: reverted %r back to %r", corrected, orig)
        self._record_event(f"Undid autocorrect: reverted '{corrected}' -> '{orig}'")
        from ravan.core.i18n import t

        msg = t("notifications.autocorrect_undone", "Reverted to '{orig}'", orig=orig)
        self.tray.notify(msg)
        return True

    def _erase_word_and_delimiter(self, word: str, delimiter: str = "") -> None:
        del_len = len(word) + len(delimiter)
        self._suppress_until = time.monotonic() + 0.1
        replace_last_n_with(del_len, "")
        for _ in range(del_len):
            if self.journal._chars:
                self.journal._chars.pop()

    def _expand_snippet_match(
        self, snip_match: tuple[Any, str], word: str, delimiter: str = ""
    ) -> bool:
        snippet, repl_text = snip_match
        from ravan.core.snippet import resolve_image_snippet

        is_img, img_path = resolve_image_snippet(repl_text, getattr(snippet, "is_image", False))
        if is_img:
            from ravan.platform.clipboard import set_clipboard_image

            if set_clipboard_image(img_path):
                self._erase_word_and_delimiter(word, delimiter)
                from ravan.platform.inject import send_ctrl_v

                send_ctrl_v()
            else:
                from ravan.core.i18n import t

                msg = t("snippets.image_not_found", "Image not found: {path}", path=img_path)
                self.tray.notify(msg)
            return True

        from ravan.core.snippet import (
            extract_form_fields,
            parse_cursor_placeholder,
            render_template,
        )

        fields = extract_form_fields(repl_text, snippet_trigger=snippet.trigger)
        if fields:
            from ravan.ui.form_dialog import QuickFormDialog

            def _on_form_submit(rendered_text: str) -> None:
                self._erase_word_and_delimiter(word, delimiter)
                cl, off = parse_cursor_placeholder(rendered_text)
                self._suppress_until = time.monotonic() + 0.03
                replace_last_n_with(0, cl, cursor_offset=off)
                for c in cl:
                    self.journal.push(c)

            QuickFormDialog(
                parent=getattr(self.overlay, "_root", None),
                template=repl_text,
                fields=fields,
                snippet_trigger=snippet.trigger,
                on_submit=_on_form_submit,
                theme_mode=getattr(self.cfg, "theme_mode", "auto"),
            ).show()
            return True

        expansion, cursor_offset = parse_cursor_placeholder(render_template(repl_text))
        from ravan.core.macro import is_macro_snippet, parse_macro_snippet

        if is_macro_snippet(expansion):
            macro_data = parse_macro_snippet(expansion)
            if macro_data:
                self._erase_word_and_delimiter(word, delimiter)
                from ravan.core.macro import MacroPlayer

                MacroPlayer.play(
                    macro_data,
                    on_suppress=lambda d: setattr(self, "_suppress_until", time.monotonic() + d),
                )
                return True
        self._replace_word(word, expansion, delimiter=delimiter, cursor_offset=cursor_offset)
        return True

    def _on_word_completed(self, word: str, delimiter: str = "") -> bool:
        if not word or self._is_excluded():
            return False

        app_name = getattr(self, "_current_exe", "")
        win_cls = getattr(self, "_current_window_class", None)
        # 1. Exact snippets (exclude regex triggers)
        snip_match = self.snippets.find_matching_snippet(
            word, app_name, include_regex=False, window_class=win_cls
        )
        if snip_match is not None:
            return self._expand_snippet_match(snip_match, word, delimiter)

        res = self.snippets.expand_with_cursor(
            word, app_name=app_name, include_regex=False, window_class=win_cls
        )
        if res is not None:
            self._replace_word(word, res[0], delimiter=delimiter, cursor_offset=res[1])
            return True

        lang_tag = self._active_layout_tag
        prev_context = (
            self.journal.previous_context(2)
            if hasattr(self.journal, "previous_context")
            else getattr(self.journal, "previous_word", lambda: None)()
        )
        # 2. Autocorrect
        if self.cfg.autocorrect_enabled:
            cand = self.predictor.correct(word, lang=lang_tag)
            if cand is not None and cand.text != word:
                log.info("Autocorrect %r → %r (lang: %s)", word, cand.text, lang_tag)
                self._last_autocorrect = (word, cand.text, time.monotonic(), delimiter)
                self._record_event(f"Autocorrect '{word}' -> '{cand.text}'", char=cand.text)
                self._replace_word(word, cand.text, delimiter=delimiter)
                self.predictor.record_selection(cand.text, context=prev_context)
                return True

        # 3. Auto-fix (wrong keyboard layout e.g. sghl -> سلام)
        if self._maybe_autofix_word(word, delimiter=delimiter):
            return True

        # 4. Transliteration (e.g. ketab -> کتاب)
        if getattr(self.cfg, "translit_enabled", False):
            if hasattr(self, "_maybe_translit_word") and self._maybe_translit_word(
                word, delimiter=delimiter
            ):
                return True

        # 5. Regex snippets! (Runs AFTER auto-fix/translit in priority chain)
        regex_match = self.snippets.find_matching_regex_snippet(
            word, app_name, window_class=win_cls
        )
        if regex_match is not None:
            return self._expand_snippet_match(regex_match, word, delimiter)

        if word:
            self.predictor.record_selection(word, context=prev_context)
        return False

    def _on_overlay_moved(self, x: int, y: int) -> None:
        self.cfg.overlay_pos_x = x
        self.cfg.overlay_pos_y = y
        self.cfg.overlay_custom_pos = True
        try:
            from ravan.core.config import save_config

            save_config(self.cfg)
            log.info("Saved custom overlay position: (%d, %d)", x, y)
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not persist overlay position: %s", exc)

    def _accept_candidate(self, cand: Candidate) -> None:
        from ravan.core.events import CandidateKind

        word = self.journal.last_word()
        prev_context = (
            self.journal.previous_context(2)
            if hasattr(self.journal, "previous_context")
            else getattr(self.journal, "previous_word", lambda: None)()
        )
        log.info("Accepted suggestion: %r → %r (kind=%s)", word, cand.text, cand.kind)
        self._record_event(f"Accepted candidate '{cand.text}'", char=cand.text)
        app_name = getattr(self, "_current_exe", None)
        self.predictor.record_selection(cand.text, context=prev_context, app_name=app_name)

        auto_space = " " if getattr(self.cfg, "prediction_auto_space", True) else ""
        if cand.kind in (CandidateKind.SENTENCE, CandidateKind.NEXT_WORD) or not word:
            del_len = (
                (cand.replace_len if cand.replace_len is not None else len(word))
                if cand.kind == CandidateKind.SENTENCE
                else 0
            )
            self._suppress_until = time.monotonic() + 0.03
            replace_text = cand.text + auto_space
            replace_last_n_with(del_len, replace_text)
            for _ in range(del_len):
                if self.journal._chars:
                    self.journal._chars.pop()
            for ch in replace_text:
                self.journal.push(ch)
            self.overlay.hide()
            set_popup_visible(False)
        else:
            self._replace_word(word, cand.text + auto_space)

    def _replace_word(
        self,
        old: str,
        new: str,
        delimiter: str = "",
        cursor_offset: int | None = None,
    ) -> None:
        # Brief mute so echoed / overlapping keys don't corrupt the journal
        self._suppress_until = time.monotonic() + 0.03
        delete_len = len(old) + len(delimiter)
        replace_text = new + delimiter
        total_cursor_offset = None
        if cursor_offset is not None and cursor_offset >= 0:
            total_cursor_offset = cursor_offset + len(delimiter)
        replace_last_n_with(delete_len, replace_text, cursor_offset=total_cursor_offset)
        self.journal.pop_last_word()
        for ch in replace_text:
            self.journal.push(ch)
        self.overlay.hide()
        set_popup_visible(False)

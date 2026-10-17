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
from ravan.ui.app_actions import AppActionsMixin
from ravan.ui.app_polling import AppPollingMixin
from ravan.ui.key_handler import KeyHandlerMixin
from ravan.ui.log_setup import setup_logging
from ravan.ui.overlay import OverlayWindow
from ravan.ui.tray import TrayIcon

log = logging.getLogger(__name__)


class RavanApp(AppActionsMixin, AppPollingMixin, KeyHandlerMixin):
    def __init__(self, cfg: Config | None = None, overlay: OverlayWindow | None = None) -> None:
        w.enable_dpi_awareness()
        self.cfg = cfg or load_config()
        self.mapper = LayoutMapper()
        self.predictor = DictPredictor.from_config(self.cfg)
        self.snippets = SnippetEngine.from_config(self.cfg)
        self.journal = KeystrokeJournal()
        from ravan.core.cliphistory import ClipboardHistory
        from ravan.core.config import config_dir

        self.clip_history = ClipboardHistory(
            maxlen=50, storage_path=config_dir() / "clipboard_history.json"
        )
        self.overlay = overlay if overlay is not None else OverlayWindow(self.cfg.theme)
        self.hook = KeyboardHook()
        self._ui_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.tray = TrayIcon(
            on_quit=lambda: self._ui_queue.put(("quit", None)),
            on_show_lang=lambda: self._ui_queue.put(("show_lang", None)),
            on_settings=lambda: self._ui_queue.put(("settings", None)),
            on_snippets=lambda: self._ui_queue.put(("snippets", None)),
            on_diagnostics=lambda: self._ui_queue.put(("diagnostics", None)),
            on_toggle_prediction=lambda val: self._ui_queue.put(("set_prediction", val)),
            is_prediction_enabled=lambda: self.cfg.prediction_enabled,
        )
        self._settings_window = None
        self._diagnostics_window = None
        self._snippet_window = None
        self.recent_events: deque[dict[str, Any]] = deque(maxlen=50)

        self._last_lang_hkl: int | None = None
        self._active_layout_tag: str | None = None
        self._last_key_time = 0.0
        self._pending_predict = False
        self._running = False
        self._suppress_until = 0.0  # ignore real keys briefly after inject
        self._last_convert_at = 0.0  # hotkey repeat throttle
        self._popup_shown_at = 0.0
        self._current_exe: str | None = None
        self._last_focus_poll = 0.0
        self._last_lang_poll = 0.0
        self._last_clip_poll = 0.0
        self._last_autocorrect: tuple[str, str, float, str] | None = None
        self._own_pid = os.getpid()

    def start(self) -> None:
        t0 = time.perf_counter()
        setup_logging()
        from ravan.ui.log_setup import install_crash_handler

        install_crash_handler(
            on_crash=lambda msg: self.tray.notify(msg, title="Ravaan Error")
        )
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
                    self._poll_language()
                    self._poll_clipboard()
                    self._maybe_predict()
                    self._maybe_timeout_popup()
                    self.overlay.tick()
                    if self._settings_window is not None:
                        self._settings_window.tick()
                    if self._diagnostics_window is not None:
                        self._diagnostics_window.tick()
                    if self._snippet_window is not None:
                        self._snippet_window.tick()
                except Exception:  # noqa: BLE001
                    log.exception("Main loop iteration failed")
                time.sleep(0.008)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def _drain_ui_actions(self) -> None:
        while True:
            try:
                action, arg = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            if action == "quit":
                self.stop()
                break
            elif action == "show_lang":
                self._show_lang_indicator()
            elif action == "settings":
                self.open_settings()
            elif action == "snippets":
                self.open_snippet_editor()
            elif action == "diagnostics":
                self.open_diagnostics()
            elif action == "set_prediction":
                self.set_prediction_enabled(bool(arg))
            elif action == "quick_stats":
                self._show_quick_text_stats()


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

    # ── Tray actions ────────────────────────────────────────────────

    def open_settings(self) -> None:
        if self._settings_window is not None and self._settings_window.open:
            return
        from ravan.ui.settings import SettingsWindow

        self._settings_window = SettingsWindow(
            self.cfg, on_saved=self._on_settings_saved
        )
        self._settings_window.show()

    def open_snippet_editor(self) -> None:
        if self._snippet_window is not None and self._snippet_window.open:
            return
        from ravan.ui.snippet_editor import SnippetEditorWindow

        self._snippet_window = SnippetEditorWindow(
            self.cfg.snippets, on_saved=self._on_snippets_saved
        )
        self._snippet_window.show()

    def _on_snippets_saved(self, snippets: list[Any]) -> None:
        self.cfg.snippets = snippets
        from ravan.core.config import save_config

        save_config(self.cfg)
        from ravan.core.i18n import t

        self.tray.notify(t("notifications.snippets_saved", "Saved {count} snippets", count=len(snippets)))

    def open_diagnostics(self) -> None:
        if self._diagnostics_window is not None and self._diagnostics_window.open:
            return
        from ravan.ui.diagnostics import DiagnosticsWindow

        self._diagnostics_window = DiagnosticsWindow(
            snapshot_fn=self._get_diagnostics_snapshot
        )
        self._diagnostics_window.show()

    def _record_event(self, action: str, vk: int = 0, char: str = "") -> None:
        now_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        vk_str = f"0x{vk:02X}" if vk else ""
        lang = current_language()
        tag = (lang.tag if lang else "en").upper()
        self.recent_events.append(
            {
                "time": now_str,
                "vk": vk_str,
                "char": char,
                "layout": tag,
                "action": action,
            }
        )

    def _on_settings_saved(self, cfg: Config) -> None:
        self.cfg = cfg
        self.predictor = DictPredictor.from_config(cfg)
        self.snippets = SnippetEngine.from_config(cfg)
        log.info("Settings updated")

    def set_prediction_enabled(self, enabled: bool) -> None:
        self.cfg.prediction_enabled = enabled
        from ravan.core.config import save_config

        save_config(self.cfg)
        if not enabled:
            self.overlay.hide()

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

    def _show_onboarding(self) -> None:
        self.cfg.has_seen_onboarding = True
        from ravan.core.config import save_config
        from ravan.core.i18n import t

        save_config(self.cfg)
        msg = t("onboarding.body", "Welcome to Ravaan!")
        title = t("onboarding.title", "Welcome to Ravaan (روان)!")
        self.tray.notify(msg, title=title)

    def _on_word_completed(self, word: str, delimiter: str = "") -> bool:
        if not word:
            return False
        if self._is_excluded():
            return False

        res = self.snippets.expand_with_cursor(word)
        if res is not None:
            expansion, cursor_offset = res
            self._replace_word(
                word, expansion, delimiter=delimiter, cursor_offset=cursor_offset
            )
            return True

        if not self.cfg.autocorrect_enabled:
            return False

        lang_tag = self._active_layout_tag
        prev_context = (
            self.journal.previous_context(2)
            if hasattr(self.journal, "previous_context")
            else (
                self.journal.previous_word()
                if hasattr(self.journal, "previous_word")
                else None
            )
        )
        cand = self.predictor.correct(word, lang=lang_tag)
        if cand is not None and cand.text != word:
            log.info("Autocorrect %r → %r (lang: %s)", word, cand.text, lang_tag)
            self._last_autocorrect = (word, cand.text, time.monotonic(), delimiter)
            self._record_event(f"Autocorrect '{word}' -> '{cand.text}'", char=cand.text)
            self._replace_word(word, cand.text, delimiter=delimiter)
            self.predictor.record_selection(cand.text, context=prev_context)
            return True

        if word:
            self.predictor.record_selection(word, context=prev_context)
        return False

    def _accept_candidate(self, cand: Candidate) -> None:
        from ravan.core.events import CandidateKind

        word = self.journal.last_word()
        prev_context = (
            self.journal.previous_context(2)
            if hasattr(self.journal, "previous_context")
            else (
                self.journal.previous_word()
                if hasattr(self.journal, "previous_word")
                else None
            )
        )
        log.info("Accepted suggestion: %r → %r (kind=%s)", word, cand.text, cand.kind)
        self._record_event(f"Accepted candidate '{cand.text}'", char=cand.text)
        self.predictor.record_selection(cand.text, context=prev_context)

        if cand.kind == CandidateKind.NEXT_WORD or not word:
            self._suppress_until = time.monotonic() + 0.08
            replace_last_n_with(0, cand.text)
            for ch in cand.text:
                self.journal.push(ch)
            self.overlay.hide()
            set_popup_visible(False)
        else:
            self._replace_word(word, cand.text)

    def _replace_word(
        self,
        old: str,
        new: str,
        delimiter: str = "",
        cursor_offset: int | None = None,
    ) -> None:
        # Brief mute so echoed / overlapping keys don't corrupt the journal
        self._suppress_until = time.monotonic() + 0.08
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

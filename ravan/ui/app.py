"""Main Ravan application loop."""

from __future__ import annotations

import logging
import os
import queue
import threading
import time

from ravan.core.config import Config, config_dir, load_config
from ravan.core.events import Candidate
from ravan.core.journal import KeystrokeJournal
from ravan.core.layout import LayoutMapper
from ravan.core.predictor import DictPredictor
from ravan.core.snippet import SnippetEngine
from ravan.platform.caret import get_caret_rect
from ravan.platform.focus import foreground_exe
from ravan.platform.hook import LLKHF_INJECTED, HookEvent, KeyboardHook, set_popup_visible
from ravan.platform.inject import replace_last_n_with
from ravan.platform.keys import is_modifier, matches_hotkey, vk_to_unicode
from ravan.platform.lang import current_language, language_label
from ravan.platform import winapi as w
from ravan.platform.winapi import wintypes
from ravan.ui.overlay import OverlayWindow
from ravan.ui.tray import TrayIcon

log = logging.getLogger(__name__)


def setup_logging() -> None:
    log_dir = config_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "ravan.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


class RavanApp:
    def __init__(self, cfg: Config | None = None, overlay: OverlayWindow | None = None) -> None:
        self.cfg = cfg or load_config()
        self.mapper = LayoutMapper()
        self.predictor = DictPredictor.from_config(self.cfg)
        self.snippets = SnippetEngine.from_config(self.cfg)
        self.journal = KeystrokeJournal()
        from ravan.core.cliphistory import ClipboardHistory

        self.clip_history = ClipboardHistory(maxlen=25)
        self.overlay = overlay if overlay is not None else OverlayWindow(self.cfg.theme)
        self.hook = KeyboardHook()
        self._ui_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.tray = TrayIcon(
            on_quit=lambda: self._ui_queue.put(("quit", None)),
            on_show_lang=lambda: self._ui_queue.put(("show_lang", None)),
            on_settings=lambda: self._ui_queue.put(("settings", None)),
            on_toggle_prediction=lambda val: self._ui_queue.put(("set_prediction", val)),
            is_prediction_enabled=lambda: self.cfg.prediction_enabled,
        )
        self._settings_window = None

        self._last_lang_hkl: int | None = None
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
        self._own_pid = os.getpid()

    def start(self) -> None:
        setup_logging()
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
            elif action == "set_prediction":
                self.set_prediction_enabled(bool(arg))

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
            set_popup_visible(False)
        self.tray.notify(
            "Word prediction ON" if enabled else "Word prediction OFF"
        )

    # ── Event drain ─────────────────────────────────────────────────

    def _drain_hook_events(self) -> None:
        # When our own overlay/settings window has focus, don't drive typing
        # features from these captured keys (prevents popups while editing settings).
        if self._is_foreground_self():
            while True:
                try:
                    self.hook.events.get_nowait()
                except queue.Empty:
                    break
            return
        while True:
            try:
                event = self.hook.events.get_nowait()
            except queue.Empty:
                break
            if not event.is_key_down:
                continue
            if event.flags & LLKHF_INJECTED:
                continue
            if time.monotonic() < self._suppress_until:
                continue
            self._handle_key(event)

    def _handle_key(self, event: HookEvent) -> None:
        vk = event.vk_code

        # ── Popup navigation (predicting or clipboard) ──
        if self.overlay.active_popup:
            if vk == w.VK_ESCAPE:
                self.overlay.hide()
                set_popup_visible(False)
                log.info("Popup dismissed")
                return
            if vk == w.VK_UP:
                self.overlay.move_selection(-1)
                return
            if vk == w.VK_DOWN:
                self.overlay.move_selection(1)
                return
            if vk in (w.VK_RETURN, w.VK_TAB):
                if self.overlay.clipboard_open:
                    item = self.overlay.accept_clipboard_selected()
                    if item:
                        self._paste_clipboard_item(item)
                else:
                    cand = self.overlay.accept_selected()
                    if cand:
                        self._accept_candidate(cand)
                set_popup_visible(False)
                return
            if self.cfg.quickpick_digits and ord("1") <= vk <= ord("5"):
                if self.overlay.clipboard_open:
                    item = self.overlay.accept_clipboard_index(vk - ord("1"))
                    if item:
                        self._paste_clipboard_item(item)
                else:
                    cand = self.overlay.accept_index(vk - ord("1"))
                    if cand:
                        self._accept_candidate(cand)
                set_popup_visible(False)
                return
            # Any other key closes the popup and continues normal typing
            self.overlay.hide()
            set_popup_visible(False)

        # Hotkeys
        if self.cfg.clipboard_history_enabled and matches_hotkey(
            vk, self.cfg.clipboard_history_hotkey
        ):
            self._show_clipboard_popup()
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

        if vk == w.VK_BACK:
            self.journal.push("\b")
            self._schedule_predict()
            return

        # Shift+Space manual ZWNJ hotkey
        if self.cfg.shift_space_zwnj and vk == w.VK_SPACE:
            from ravan.platform.keys import modifiers_down
            if modifiers_down(["shift"]):
                from ravan.core.zwnj import ZWNJ
                self._suppress_until = time.monotonic() + 0.05
                replace_last_n_with(1, ZWNJ)
                self.journal.push(ZWNJ)
                self.overlay.hide()
                set_popup_visible(False)
                return

        ch = vk_to_unicode(vk, event.scan_code)
        if ch is None:
            return

        # Inline calculator (e.g. 1200*1.09= -> 1308)
        if ch == "=" and self.cfg.inline_calc_enabled:
            from ravan.core.calc import calculate, extract_math_expression

            text = self.journal.text()
            expr = extract_math_expression(text)
            if expr:
                res = calculate(expr)
                if res is not None:
                    delete_n = len(expr) + 1
                    self._suppress_until = time.monotonic() + 0.05
                    replace_last_n_with(delete_n, res)
                    for _ in range(len(expr)):
                        if self.journal._chars:
                            self.journal._chars.pop()
                    for c in res:
                        self.journal.push(c)
                    self.overlay.hide()
                    set_popup_visible(False)
                    log.info("Inline calc: %r= → %r", expr, res)
                    return

        if ch.isspace() or ch in ".,;:!?\n\r\t":
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
            return

        self.journal.push(ch)
        self._schedule_predict()

    def _maybe_attach_suffix_zwnj(self, suffix: str) -> bool:
        from ravan.core.zwnj import ZWNJ, should_attach_suffix

        text = self.journal.text()
        suffix_with_spaces = f" {suffix} "
        if not text.endswith(suffix_with_spaces):
            return False
        before = text[: -len(suffix_with_spaces)]
        i = len(before) - 1
        while i >= 0 and not before[i].isspace():
            i -= 1
        prev_word = before[i + 1 :]
        if not prev_word or not should_attach_suffix(prev_word, suffix):
            return False

        delete_n = len(suffix) + 2
        replace_text = f"{ZWNJ}{suffix} "
        self._suppress_until = time.monotonic() + 0.05
        replace_last_n_with(delete_n, replace_text)
        for _ in range(delete_n):
            if self.journal._chars:
                self.journal._chars.pop()
        for c in replace_text:
            self.journal.push(c)
        log.info("Attached suffix ZWNJ: %r + %r", prev_word, suffix)
        return True

    def _on_word_completed(self, word: str, delimiter: str = "") -> bool:
        if not word:
            return False
        expansion = self.snippets.expand(word)
        if expansion is not None:
            self._replace_word(word, expansion, delimiter=delimiter)
            return True

        if not self.cfg.autocorrect_enabled:
            return False
        cand = self.predictor.correct(word)
        if cand is not None and cand.text != word:
            log.info("Autocorrect %r → %r", word, cand.text)
            self._replace_word(word, cand.text, delimiter=delimiter)
            return True
        return False

    def _convert_selection_or_last_word(self) -> None:
        """Convert selected text if any exists; otherwise convert the last typed word."""
        from ravan.platform.clipboard import try_convert_selection

        self._suppress_until = time.monotonic() + 0.12
        if try_convert_selection(self.mapper.convert_text):
            log.info("Converted selected text layout")
            return
        self._convert_last_word()

    def _convert_last_word(self) -> None:
        word, trailing = self.journal.last_word_info(allow_trailing_spaces=True)
        if not word:
            return
        converted = self.mapper.convert_word(word)
        if not converted or converted == word:
            log.info("No conversion for %r", word)
            return
        log.info("Convert %r → %r (trailing spaces: %d)", word, converted, trailing)
        self._suppress_until = time.monotonic() + 0.05
        trailing_str = " " * trailing
        replace_last_n_with(len(word) + trailing, converted + trailing_str)
        self.journal.pop_last_word_info(allow_trailing_spaces=True)
        for ch in converted + trailing_str:
            self.journal.push(ch)

    def _normalize_selection_or_last_word(self) -> None:
        """Normalize Persian text in selection or the last typed word."""
        from ravan.core.transform import normalize_text
        from ravan.platform.clipboard import try_convert_selection

        self._suppress_until = time.monotonic() + 0.12
        if try_convert_selection(normalize_text):
            log.info("Normalized selected text")
            return
        self._normalize_last_word()

    def _normalize_last_word(self) -> None:
        from ravan.core.transform import normalize_text

        word, trailing = self.journal.last_word_info(allow_trailing_spaces=True)
        if not word:
            return
        normalized = normalize_text(word)
        if not normalized or normalized == word:
            return
        log.info("Normalize %r → %r (trailing: %d)", word, normalized, trailing)
        self._suppress_until = time.monotonic() + 0.05
        trailing_str = " " * trailing
        replace_last_n_with(len(word) + trailing, normalized + trailing_str)
        self.journal.pop_last_word_info(allow_trailing_spaces=True)
        for ch in normalized + trailing_str:
            self.journal.push(ch)

    def _cycle_case_selection_or_last_word(self) -> None:
        """Cycle case (UPPER -> lower -> Title) of selection or last typed word."""
        from ravan.core.transform import cycle_case
        from ravan.platform.clipboard import try_convert_selection

        self._suppress_until = time.monotonic() + 0.12
        if try_convert_selection(cycle_case):
            log.info("Cycled case of selected text")
            return
        self._cycle_case_last_word()

    def _cycle_case_last_word(self) -> None:
        from ravan.core.transform import cycle_case

        word, trailing = self.journal.last_word_info(allow_trailing_spaces=True)
        if not word:
            return
        cased = cycle_case(word)
        if not cased or cased == word:
            return
        log.info("Cycle case %r → %r (trailing: %d)", word, cased, trailing)
        self._suppress_until = time.monotonic() + 0.05
        trailing_str = " " * trailing
        replace_last_n_with(len(word) + trailing, cased + trailing_str)
        self.journal.pop_last_word_info(allow_trailing_spaces=True)
        for ch in cased + trailing_str:
            self.journal.push(ch)

    def _show_lang_indicator(self) -> None:
        lang = current_language()
        if lang is None:
            return
        caret = get_caret_rect()
        self.overlay.show_language(
            language_label(lang), caret.x, caret.y, caret.height
        )

    def _poll_focus(self) -> None:
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

    def _is_foreground_self(self) -> bool:
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

    def _is_excluded(self) -> bool:
        exe = self._current_exe
        if not exe:
            return False
        return any(exe == e.lower() or exe.endswith(e.lower()) for e in self.cfg.excluded_apps)

    def _poll_language(self) -> None:
        now = time.monotonic()
        if now - self._last_lang_poll < 0.15:
            return
        self._last_lang_poll = now
        lang = current_language()
        if lang is None:
            return
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

    def _poll_clipboard(self) -> None:
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

    def _show_clipboard_popup(self) -> None:
        items = self.clip_history.items()
        if not items:
            self.tray.notify("Clipboard history is empty")
            return
        caret = get_caret_rect()
        self.overlay.show_clipboard(items, caret.x, caret.y, caret.height)
        set_popup_visible(True, swallow_digits=self.cfg.quickpick_digits)
        self._popup_shown_at = time.monotonic()
        log.info("Showing clipboard popup with %d items", len(items))

    def _paste_clipboard_item(self, text: str) -> None:
        from ravan.platform.clipboard import set_clipboard_text
        from ravan.platform.inject import send_shortcut

        self._suppress_until = time.monotonic() + 0.1
        set_clipboard_text(text)
        time.sleep(0.02)
        send_shortcut([w.VK_CONTROL], ord("V"))
        log.info("Pasted clipboard item (%d chars)", len(text))

    def _schedule_predict(self) -> None:
        self._last_key_time = time.monotonic()
        self._pending_predict = True

    def _maybe_predict(self) -> None:
        if not self._pending_predict or not self.cfg.prediction_enabled:
            return
        if self._is_excluded():
            return
        elapsed_ms = (time.monotonic() - self._last_key_time) * 1000
        if elapsed_ms < self.cfg.prediction_debounce_ms:
            return
        self._pending_predict = False
        prefix = self.journal.last_word()
        if len(prefix) < self.cfg.min_prefix_len:
            if self.overlay.predicting:
                self.overlay.hide()
                set_popup_visible(False)
            return
        cands = self.predictor.predict(
            prefix, "", self.cfg.prediction_max_candidates
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

    def _maybe_timeout_popup(self) -> None:
        """Auto-hide a stale prediction popup (e.g. user switched to mouse)."""
        if not self.overlay.predicting:
            return
        timeout_s = self.cfg.popup_timeout_ms / 1000.0
        if timeout_s <= 0:
            return
        if time.monotonic() - self._popup_shown_at > timeout_s:
            self.overlay.hide()
            set_popup_visible(False)

    def _accept_candidate(self, cand: Candidate) -> None:
        word = self.journal.last_word()
        if not word:
            return
        log.info("Accepted suggestion: %r → %r", word, cand.text)
        self._replace_word(word, cand.text)

    def _replace_word(self, old: str, new: str, delimiter: str = "") -> None:
        # Brief mute so echoed / overlapping keys don't corrupt the journal
        self._suppress_until = time.monotonic() + 0.05
        delete_len = len(old) + len(delimiter)
        replace_text = new + delimiter
        replace_last_n_with(delete_len, replace_text)
        self.journal.pop_last_word()
        for ch in replace_text:
            self.journal.push(ch)
        self.overlay.hide()
        set_popup_visible(False)

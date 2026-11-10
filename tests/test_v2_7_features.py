"""Tests for the v2.6.1 UX round: language chip placement, sticky prediction
popup, deferred learning/clipboard persistence, and the macOS material style."""

from __future__ import annotations

import sys
import time
from types import SimpleNamespace

import pytest

from ravan.core.cliphistory import ClipboardHistory
from ravan.core.config import config_from_dict
from ravan.core.config_migration import migrate_config_dict
from ravan.core.learning import UserLearningEngine
from ravan.ui.overlay import OverlayWindow

# ── Config defaults & migrations ────────────────────────────────────────────


def test_v2_7_config_defaults():
    cfg = config_from_dict({})
    assert cfg.lang_indicator_placement == "bottom_right"  # above the tray icons
    assert cfg.popup_timeout_ms == 8000  # longer suggestion persistence
    assert cfg.prediction_ui_style == "macos"  # macOS material style


def test_v2_7_migrations_are_idempotent():
    raw = {"popup_timeout_ms": 4000, "prediction_ui_style": "modern"}
    migrated = migrate_config_dict(dict(raw))
    assert migrated["popup_timeout_ms"] == 8000
    assert migrated["prediction_ui_style"] == "macos"
    assert migrated["lang_indicator_placement"] == "bottom_right"
    assert migrated["schema_version"] == 3  # schema not bumped

    again = migrate_config_dict(dict(migrated))
    assert again["popup_timeout_ms"] == 8000
    assert again["prediction_ui_style"] == "macos"
    # Explicit user choices other than the old defaults survive untouched.
    custom = migrate_config_dict({"popup_timeout_ms": 3000, "prediction_ui_style": "compact"})
    assert custom["popup_timeout_ms"] == 3000
    assert custom["prediction_ui_style"] == "compact"


def test_invalid_lang_placement_falls_back():
    cfg = config_from_dict({"lang_indicator_placement": "somewhere_else"})
    assert cfg.lang_indicator_placement == "bottom_right"
    assert config_from_dict({"lang_indicator_placement": "click"}).lang_indicator_placement == "click"


# ── Language chip corner anchoring ──────────────────────────────────────────


def test_corner_position_anchors():
    area = (0, 0, 1920, 1040)  # work area above the taskbar
    w, h = 120, 40

    x, y = OverlayWindow.corner_position("bottom_right", area, w, h)
    assert x == 1920 - 120 - 12
    assert y == 1040 - 40 - 8  # directly above the taskbar/tray icons

    x, y = OverlayWindow.corner_position("top_left", area, w, h)
    assert (x, y) == (12, 8)

    x, y = OverlayWindow.corner_position("bottom_left", area, w, h)
    assert x == 12 and y == 1040 - 48

    x, y = OverlayWindow.corner_position("top_right", area, w, h)
    assert x == 1920 - 132 and y == 8


# ── Sticky prediction popup ─────────────────────────────────────────────────


class _FakeOverlay:
    def __init__(self) -> None:
        self.visible = False
        self.hide_calls = 0
        self.shown: list[tuple] = []

    @property
    def predicting(self) -> bool:
        return bool(self.shown) and self.visible

    def hide(self) -> None:
        self.hide_calls += 1
        self.visible = False
        self.shown.clear()

    def show_predictions(self, cands, x, y, height, on_accept=None):  # noqa: ANN001
        self.shown.append(tuple(c.text for c in cands))
        self.visible = True


class _StickyApp:
    """Minimal stub exercising AppPollingMixin._maybe_predict."""

    from ravan.ui.app_polling import AppPollingMixin as _M

    # Mix in only the method under test to keep the stub independent.
    _maybe_predict = _M._maybe_predict

    def __init__(self) -> None:
        self.overlay = _FakeOverlay()
        self.cfg = SimpleNamespace(
            prediction_enabled=True,
            prediction_debounce_ms=0,
            min_prefix_len=1,
            next_word_prediction=False,
            quickpick_digits=False,
            suggestion_accept_arrow="none",
            prediction_max_candidates=5,
        )
        self.journal = SimpleNamespace(last_word=lambda *a, **k: "xyz", previous_context=lambda n: "")
        self.predictor = SimpleNamespace(
            predict=lambda *a, **k: [],  # no candidates for this prefix
            suppress_session_word=lambda w: None,
        )
        self._pending_predict = True
        self._last_key_time = time.monotonic() - 1.0
        self._current_exe = "notepad.exe"
        self._popup_shown_at = time.monotonic()


def test_sticky_popup_survives_candidate_gap(monkeypatch):
    import ravan.platform.focus as focus_mod
    import ravan.platform.lang as lang_mod

    app = _StickyApp()
    monkeypatch.setattr(focus_mod, "is_password_focused", lambda: False)
    monkeypatch.setattr(focus_mod, "is_numeric_focused", lambda: False)
    monkeypatch.setattr(lang_mod, "is_ime_composing", lambda: False)
    monkeypatch.setattr(app, "_is_excluded", lambda: False, raising=False)

    app.overlay.shown = ("old", "candidates")
    app.overlay.visible = True  # popup currently on screen from the previous prefix

    app._maybe_predict()  # new prefix yields no candidates

    assert app.overlay.hide_calls == 0  # sticky: not flickered away


def test_hidden_popup_stays_hidden_without_candidates(monkeypatch):
    import ravan.platform.focus as focus_mod
    import ravan.platform.lang as lang_mod

    app = _StickyApp()
    monkeypatch.setattr(focus_mod, "is_password_focused", lambda: False)
    monkeypatch.setattr(focus_mod, "is_numeric_focused", lambda: False)
    monkeypatch.setattr(lang_mod, "is_ime_composing", lambda: False)
    monkeypatch.setattr(app, "_is_excluded", lambda: False, raising=False)

    app.overlay.visible = False
    app._maybe_predict()
    assert app.overlay.hide_calls == 0 and not app.overlay.shown


# ── Deferred persistence ────────────────────────────────────────────────────


def test_learning_lazy_save_defers_disk_write(tmp_path):
    engine = UserLearningEngine(storage_path=tmp_path / "learning.json", auto_load=False)
    engine.learn_transition("سلام", "عزیز")
    engine.save(lazy=True)  # deferred right after session start: dirty, no write
    assert engine._dirty is True
    assert not (tmp_path / "learning.json").exists()

    engine.flush()
    assert engine._dirty is False
    assert (tmp_path / "learning.json").is_file()  # DPAPI-protected blob written

    # A lazy save shortly after a real write is again deferred, but flush persists.
    engine.learn_transition("دوباره", "تلاش")
    engine.save(lazy=True)
    assert engine._dirty is True
    engine.flush()
    assert engine._dirty is False


def test_clipboard_history_lazy_save(tmp_path):
    hist = ClipboardHistory(maxlen=5, storage_path=tmp_path / "clip.json")
    hist.add("hello world", ignore_passwords=True)
    assert hist._dirty is True  # deferred by add()
    assert not (tmp_path / "clip.json").exists()

    hist.flush()
    assert (tmp_path / "clip.json").is_file()
    assert "hello world" in hist.items()


# ── Settings: live preview, apply-on-change, save-keeps-open ──────────────────


@pytest.mark.skipif(sys.platform != "win32", reason="Tkinter settings window")
def test_settings_apply_on_change_and_close_with_change(monkeypatch):
    import ravan.core.user_dict as user_dict_mod
    import ravan.ui.settings_save as settings_save_mod

    # Keep the real user config / user words untouched.
    monkeypatch.setattr(settings_save_mod, "save_config", lambda cfg: None)
    monkeypatch.setattr(user_dict_mod, "save_user_words", lambda words: None)

    from ravan.core.config import Config as Cfg
    from ravan.ui.settings import SettingsWindow

    cfg = Cfg()
    applied: list[int] = []
    win = SettingsWindow(cfg, on_saved=lambda c: applied.append(1))
    win.show()
    try:
        for _ in range(60):
            win.tick()

        # Live preview of the suggestion-box design is rendered inside Settings.
        assert win._style_preview is not None
        assert len(win._style_preview.winfo_children()) > 0

        # Apply-on-change: selecting a style updates cfg + live popup instantly.
        win._prediction_ui_style_var.set("classic")
        win.on_prediction_style_changed()
        assert cfg.prediction_ui_style == "classic"
        assert len(applied) == 1
        assert len(win._style_preview.winfo_children()) > 0  # re-rendered

        # Save applies and persists WITHOUT closing the window.
        win._save()
        assert win.open and win._root is not None

        # Apply-on-change for the language chip placement too.
        label = list(win._lang_placement_map.keys())[1]
        win._lang_placement_var.set(label)
        win.on_lang_placement_changed()
        assert cfg.lang_indicator_placement == "bottom_left"

        # Close-with-change: closing the window saves + applies, then closes.
        win._save_then_close()
        assert not win.open and win._root is None
    finally:
        if win._root is not None:
            win._close()


@pytest.mark.skipif(sys.platform != "win32", reason="Tkinter settings window")
def test_settings_preview_is_distinct_per_style(monkeypatch):
    import ravan.core.user_dict as user_dict_mod
    import ravan.ui.settings_save as settings_save_mod

    monkeypatch.setattr(settings_save_mod, "save_config", lambda cfg: None)
    monkeypatch.setattr(user_dict_mod, "save_user_words", lambda words: None)

    from ravan.core.config import Config as Cfg
    from ravan.ui.settings import SettingsWindow

    cfg = Cfg()
    win = SettingsWindow(cfg, on_saved=lambda c: None)
    win.show()
    try:
        for _ in range(60):
            win.tick()

        chassis_bytes: dict[str, bytes] = {}
        for style in ("macos", "glass", "classic"):
            win._prediction_ui_style_var.set(style)
            win.on_prediction_style_changed()
            win._root.update()
            container = win._style_preview.winfo_children()[0]
            canvas = container.winfo_children()[0]  # [0] is the backdrop canvas
            assert canvas.find_all(), "Canvas must have rendered graphical elements"
            assert win._preview_chassis_img is not None
            chassis_bytes[style] = win._preview_chassis_img.tobytes()

        # The three translucent/opaque styles must render clearly different
        # graphical materials (macos tinted acrylic, glass specular refraction,
        # classic opaque window) — each chassis image must be distinct.
        assert chassis_bytes["macos"] != chassis_bytes["glass"]
        assert chassis_bytes["glass"] != chassis_bytes["classic"]
        assert chassis_bytes["macos"] != chassis_bytes["classic"]
    finally:
        if win._root is not None:
            win._close()

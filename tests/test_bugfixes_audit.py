"""Regression tests for bug fixes uncovered during project audit."""

from __future__ import annotations

import ctypes
import json
import queue
from unittest.mock import MagicMock, patch

from ravan.core.config import Config, Snippet
from ravan.core.sync import (
    dict_to_snippet,
    make_local_backup,
    pull_from_gist,
    restore_backup,
    snippet_to_dict,
)
from ravan.platform import winapi as w
from ravan.platform.hook import KeyboardHook, set_popup_visible
from ravan.ui.app_actions import AppActionsMixin
from ravan.ui.app_polling import AppPollingMixin
from ravan.ui.settings_reset import reset_tab_defaults
from ravan.ui.theme import get_prediction_style


def test_hook_swallow_arrow_both_for_horizontal_ribbon():
    """WH_KEYBOARD_LL swallows both VK_LEFT and VK_RIGHT when swallow_arrow='both'."""
    hook = KeyboardHook()
    set_popup_visible(True, swallow_digits=True, swallow_arrow="both", swallow_enter=False)
    try:
        kb_left = w.KBDLLHOOKSTRUCT(vkCode=w.VK_LEFT, scanCode=0, flags=0, time=0, dwExtraInfo=0)
        kb_right = w.KBDLLHOOKSTRUCT(vkCode=w.VK_RIGHT, scanCode=0, flags=0, time=0, dwExtraInfo=0)

        res_left = hook._callback(
            w.HC_ACTION, w.WM_KEYDOWN, ctypes.addressof(kb_left)
        )
        res_right = hook._callback(
            w.HC_ACTION, w.WM_KEYDOWN, ctypes.addressof(kb_right)
        )
        assert res_left == 1
        assert res_right == 1
    finally:
        set_popup_visible(False)


def test_effective_swallow_arrow_layout_and_direction():
    """AppPollingMixin._effective_swallow_arrow returns 'both' for horizontal and resolves vertical arrow."""

    class DummyPolling(AppPollingMixin):
        def __init__(self, cfg: Config):
            self.cfg = cfg

    cfg_h = Config(prediction_layout="horizontal", suggestion_accept_arrow="none")
    assert DummyPolling(cfg_h)._effective_swallow_arrow() == "both"

    cfg_v_right = Config(prediction_layout="vertical", suggestion_accept_arrow="right")
    assert DummyPolling(cfg_v_right)._effective_swallow_arrow() == "right"

    cfg_v_left = Config(prediction_layout="vertical", suggestion_accept_arrow="left")
    assert DummyPolling(cfg_v_left)._effective_swallow_arrow() == "left"

    cfg_v_none = Config(prediction_layout="vertical", suggestion_accept_arrow="none")
    assert DummyPolling(cfg_v_none)._effective_swallow_arrow() is None


def test_custom_colors_acrylic_colorkey_and_accessible_highlight_fg():
    """Acrylic styles (macos/ios) keep card_bg != bg and auto-adjust highlight_fg for bright highlights."""
    custom_neon = {
        "bg": "#080811",
        "fg": "#F0F6FC",
        "accent": "#00F5D4",
        "border": "#00F5D4",
        "highlight": "#00F5D4",
        "highlight_fg": "#FFFFFF",  # Default uncontrasted white on bright cyan
    }
    tok = get_prediction_style("macos", mode="dark", custom_colors=custom_neon)
    assert tok.acrylic is True
    assert tok.palette.bg == "#080811"
    # card_bg must differ from bg so Win32 -transparentcolor does not punch through rows
    assert tok.palette.card_bg.lower() != tok.palette.bg.lower()
    # Bright cyan highlight must switch from unreadable white to high-contrast dark text
    assert tok.palette.highlight_fg == "#11111B"

    # When highlight matches bg in acrylic style, highlight is nudged off colorkey too
    same_hl = {
        "bg": "#202024",
        "fg": "#F5F5F7",
        "highlight": "#202024",
    }
    tok_same = get_prediction_style("ios", mode="dark", custom_colors=same_hl)
    assert tok_same.palette.highlight.lower() != tok_same.palette.bg.lower()


def test_sync_preserves_snippets_v3_metadata(tmp_path, monkeypatch):
    """Backup, restore, and Gist pull preserve Snippets 3.0 regex, app_filter, is_image, and groups."""
    monkeypatch.setattr("ravan.core.sync.config_dir", lambda: tmp_path)
    monkeypatch.setattr("ravan.core.config.config_dir", lambda: tmp_path)
    monkeypatch.setattr("ravan.core.user_dict.config_dir", lambda: tmp_path)

    orig = Snippet(
        trigger=r"^inv(\d+)$",
        replacement=r"Invoice #\1",
        enabled=True,
        is_regex=True,
        app_filter="excel.exe",
        is_image=False,
        groups=["finance", "work"],
    )
    as_dict = snippet_to_dict(orig)
    assert as_dict["is_regex"] is True
    assert as_dict["app_filter"] == "excel.exe"
    assert as_dict["groups"] == ["finance", "work"]

    roundtrip = dict_to_snippet(as_dict)
    assert roundtrip == orig

    # Verify backup & restore keep all 7 fields
    bfile = make_local_backup(user_words=["سلام"], snippets=[as_dict])
    restored = restore_backup(bfile)
    assert restored is not None
    _, snips_loaded = restored
    assert snips_loaded[0]["is_regex"] is True
    assert snips_loaded[0]["groups"] == ["finance", "work"]

    # Verify pull_from_gist does not strip Snippets 3.0 metadata
    fake_gist_payload = {
        "files": {
            "user_words.txt": {"content": "روان\n"},
            "snippets.json": {"content": json.dumps([as_dict], ensure_ascii=False)},
        }
    }
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(fake_gist_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = pull_from_gist("ghp_dummy_token", "gist123", current_words=[], current_snippets=[])
    assert res["ok"] is True
    pulled = res["snippets"][0]
    assert pulled["is_regex"] is True
    assert pulled["app_filter"] == "excel.exe"
    assert pulled["groups"] == ["finance", "work"]


def test_auto_disable_power_mode_dispatches_via_ui_queue():
    """Timer thread must enqueue toggle_power_mode onto _ui_queue instead of calling Tk directly."""

    class DummyPowerApp(AppActionsMixin):
        def __init__(self):
            self.power_mode_active = True
            self._ui_queue: queue.Queue = queue.Queue()
            self.direct_called = False

        def toggle_power_mode(self):
            self.direct_called = True

    app = DummyPowerApp()
    app._auto_disable_power_mode()
    assert app.direct_called is False
    assert app._ui_queue.get_nowait() == ("toggle_power_mode", None)


def test_settings_reset_covers_new_general_and_prediction_fields():
    """reset_tab_defaults resets newly added style, layout, color, zwnj, and placement variables."""

    class FakeVar:
        def __init__(self, val=None):
            self._val = val

        def get(self):
            return self._val

        def set(self, val):
            self._val = val

    class DummyWin:
        def __init__(self):
            self._zwnj_var = FakeVar(False)
            self._shift_space_var = FakeVar(False)
            self._punct_spacing_var = FakeVar(False)
            self._cliphist_var = FakeVar(False)
            self._lang_placement_map = {"Bottom Right": "bottom_right", "Click": "click"}
            self._lang_placement_var = FakeVar("Click")

            self._prediction_ui_style_var = FakeVar("neon")
            self._prediction_layout_var = FakeVar("horizontal")
            self._prediction_use_custom_colors_var = FakeVar(True)
            self._prediction_custom_bg_var = FakeVar("#000000")
            self._prediction_font_size_var = FakeVar(18)
            self._prediction_opacity_var = FakeVar(65)
            self._overlay_custom_pos_var = FakeVar(True)
            self._learning_enabled_var = FakeVar(False)
            self._prediction_auto_space_var = FakeVar(False)

    win = DummyWin()
    defaults = Config()
    with patch("tkinter.messagebox.askyesno", return_value=True):
        reset_tab_defaults(win, "general")
        assert win._zwnj_var.get() == defaults.auto_zwnj_enabled
        assert win._shift_space_var.get() == defaults.shift_space_zwnj
        assert win._punct_spacing_var.get() == defaults.fix_punctuation_spacing
        assert win._cliphist_var.get() == defaults.clipboard_history_enabled
        assert win._lang_placement_var.get() == "Bottom Right"

        reset_tab_defaults(win, "prediction")
        assert win._prediction_ui_style_var.get() == defaults.prediction_ui_style
        assert win._prediction_layout_var.get() == defaults.prediction_layout
        assert win._prediction_use_custom_colors_var.get() is False
        assert win._prediction_custom_bg_var.get() == defaults.prediction_custom_bg
        assert win._prediction_font_size_var.get() == defaults.prediction_font_size
        assert win._prediction_opacity_var.get() == int(defaults.prediction_opacity * 100)
        assert win._overlay_custom_pos_var.get() is False
        assert win._learning_enabled_var.get() is True
        assert win._prediction_auto_space_var.get() is True


def test_on_settings_saved_flushes_learning_and_preserves_session_state():
    """RavanApp._on_settings_saved flushes deferred learning and keeps session suppression state."""
    from ravan.ui.app import RavanApp

    app = RavanApp.__new__(RavanApp)
    old_predictor = MagicMock()
    old_predictor.session_suppressed = {"customtoken"}
    old_predictor._selection_counts = {"سلام": 4}
    app.predictor = old_predictor
    app.overlay = MagicMock()
    app.overlay.predicting = False
    app.autofix = None
    app.tray = None
    app._init_accent = MagicMock()

    new_predictor = MagicMock()
    new_predictor.session_suppressed = set()
    new_predictor._selection_counts = {}

    with patch("ravan.ui.app.DictPredictor.from_config", return_value=new_predictor):
        app._on_settings_saved(Config())

    old_predictor.flush_learning.assert_called_once()
    assert "customtoken" in new_predictor.session_suppressed
    assert new_predictor._selection_counts["سلام"] == 4

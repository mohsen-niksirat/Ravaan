"""Tests for Phase 5 Power-User Features: Math v2, Macro Recorder, Power Mode, and ZIP Backup."""

from __future__ import annotations

import json

import pytest

from ravan.core.backup_zip import export_user_data, import_user_data
from ravan.core.calc import (
    calculate,
    extract_math_expression,
    extract_math_query,
    parse_calc_query,
    safe_eval,
)
from ravan.core.config import Config
from ravan.core.macro import (
    MacroPlayer,
    MacroRecorder,
    is_macro_snippet,
    parse_macro_snippet,
    serialize_macro,
)
from ravan.platform import winapi as w
from ravan.platform.focus import is_password_focused, set_mock_password_focused


def test_math_v2_percentages():
    # Multiplicative percentage
    assert safe_eval("100 * 20%") == 20
    assert calculate("100 * 20%") == "20"

    # Markup & discount percentages
    assert safe_eval("500 + 10%") == 550
    assert calculate("500 + 10%") == "550"
    assert safe_eval("500 - 10%") == 450
    assert calculate("500 - 10%") == "450"

    # Division and standalone percentage
    assert safe_eval("1000 / 50%") == 2000
    assert safe_eval("50%") == 0.5

    # Persian digits with Persian percent symbol
    assert calculate("۵۰۰ + ۱۰٪") == "۵۵۰"


def test_math_v2_rounding_macro():
    assert calculate("10 / 3=2") == "3.33"
    assert calculate("10 / 3=0") == "3"
    assert calculate("10 / 3=4") == "3.3333"
    assert calculate("1200 * 1.09=2") == "1308.00"

    # Query extraction with rounding
    q = extract_math_query("1200*1.09=2")
    assert q is not None
    expr, dec, curr, mlen = q
    assert expr == "1200*1.09"
    assert dec == 2
    assert curr is None


def test_math_v2_currency_output():
    # Toman (=t and =ت)
    res_t = calculate("12000=t")
    assert res_t == "12,000 تومان"
    res_fa_t = calculate("۱۲۰۰۰=ت")
    assert res_fa_t == "۱۲,۰۰۰ تومان"

    # Rial (=r and =ر)
    res_r = calculate("120000=r")
    assert res_r == "120,000 ریال"
    res_fa_r = calculate("۱۲۰۰۰۰=ر")
    assert res_fa_r == "۱۲۰,۰۰۰ ریال"

    # Single number with currency
    q_curr = extract_math_query("15000=t")
    assert q_curr is not None
    expr, dec, curr, _ = q_curr
    assert expr == "15000"
    assert curr == "toman"


def test_math_query_parsing():
    assert parse_calc_query("100+20=2") == ("100+20", 2, None)
    assert parse_calc_query("5000=t") == ("5000", None, "toman")
    assert parse_calc_query("5000=r") == ("5000", None, "rial")
    assert parse_calc_query("12+3=") == ("12+3", None, None)
    assert parse_calc_query("12+3") == ("12+3", None, None)
    assert extract_math_expression("price is 1200*1.09") == "1200*1.09"


def test_password_field_detection():
    try:
        set_mock_password_focused(True)
        assert is_password_focused() is True

        set_mock_password_focused(False)
        assert is_password_focused() is False
    finally:
        set_mock_password_focused(None)


def test_macro_recorder_and_serialization():
    rec = MacroRecorder()
    assert not rec.is_recording

    rec.start()
    assert rec.is_recording

    rec.record(ord("H"), "H")
    rec.record(ord("I"), "I")
    rec.record(w.VK_ESCAPE, "")  # Esc must be ignored

    events = rec.stop()
    assert not rec.is_recording
    assert len(events) == 2
    assert events[0]["char"] == "H"
    assert events[1]["char"] == "I"

    # Serialization
    encoded = serialize_macro(events, preserve_timing=True)
    assert is_macro_snippet(encoded)

    parsed = parse_macro_snippet(encoded)
    assert parsed is not None
    assert parsed["preserve_timing"] is True
    assert len(parsed["events"]) == 2


@pytest.mark.windows
def test_macro_player_dry_run(monkeypatch):
    injected: list[str] = []
    monkeypatch.setattr("ravan.core.macro.inject_text", lambda text: injected.append(text))
    monkeypatch.setattr(w.user32, "SendInput", lambda *args, **kwargs: 1)

    events = [
        {"vk": ord("A"), "char": "A", "delay_ms": 10.0},
        {"vk": ord("B"), "char": "B", "delay_ms": 10.0},
    ]
    macro_data = {"events": events, "preserve_timing": False}

    suppressed: list[float] = []

    def _on_suppress(dur: float) -> None:
        suppressed.append(dur)

    t = MacroPlayer.play(macro_data, on_suppress=_on_suppress)
    assert len(suppressed) == 1
    assert suppressed[0] > 0
    if t is not None:
        t.join(timeout=2.0)
    assert injected == ["A", "B"]


def test_power_mode_configuration_and_toggle(monkeypatch):
    cfg = Config()
    assert cfg.power_mode_hotkey.key.upper() == "P"
    assert "Ctrl" in cfg.power_mode_hotkey.modifiers
    assert "Alt" in cfg.power_mode_hotkey.modifiers

    # Test toggle logic on dummy app
    class DummyApp:
        def __init__(self):
            self.cfg = Config()
            self.power_mode_active = False
            self.overlay = type("Overlay", (), {"hide": lambda self: None})()
            self.tray = type("Tray", (), {"set_power_mode": lambda self, active: None, "notify": lambda self, msg, title=None: None})()

        from ravan.ui.app_actions import AppActionsMixin
        toggle_power_mode = AppActionsMixin.toggle_power_mode
        _auto_disable_power_mode = AppActionsMixin._auto_disable_power_mode

    app = DummyApp()
    assert not app.power_mode_active

    # Toggle ON
    state = app.toggle_power_mode(duration_min=0)
    assert state is True
    assert app.power_mode_active is True

    # Toggle OFF
    state = app.toggle_power_mode()
    assert state is False
    assert app.power_mode_active is False


def test_zip_export_and_import(tmp_path, monkeypatch):
    # Mock config_dir to tmp_path across config, backup_zip, and data_manifest
    mock_appdata = tmp_path / "RavanAppdata"
    mock_appdata.mkdir(parents=True)
    monkeypatch.setattr("ravan.core.config.config_dir", lambda: mock_appdata)
    monkeypatch.setattr("ravan.core.backup_zip.config_dir", lambda: mock_appdata)
    monkeypatch.setattr("ravan.core.data_manifest.config_dir", lambda: mock_appdata)

    # Populate mock user data
    (mock_appdata / "user_words.txt").write_text("سیب\nگلابی\n", encoding="utf-8")
    (mock_appdata / "config.json").write_text(json.dumps({"snippets": [{"trigger": "//sig", "replacement": "Best regards"}]}), encoding="utf-8")
    (mock_appdata / "learned_corpus.json").write_text(json.dumps({"سلام": 5}), encoding="utf-8")

    # Export to zip
    zip_dest = tmp_path / "export_test.zip"
    exported = export_user_data(zip_dest)
    assert exported.is_file()

    # Modify existing data
    (mock_appdata / "user_words.txt").write_text("انار\n", encoding="utf-8")
    (mock_appdata / "learned_corpus.json").write_text(json.dumps({"سلام": 2, "صبح": 3}), encoding="utf-8")

    # Import with merge=True
    res = import_user_data(exported, merge=True)
    assert res["ok"] is True
    assert "user_words.txt (merged)" in res["restored_files"]

    # Verify merged user words contains both
    merged_words = (mock_appdata / "user_words.txt").read_text(encoding="utf-8")
    assert "سیب" in merged_words
    assert "انار" in merged_words

    # Verify learned corpus merged with max frequencies
    merged_corpus = json.loads((mock_appdata / "learned_corpus.json").read_text(encoding="utf-8"))
    assert merged_corpus["سلام"] == 5
    assert merged_corpus["صبح"] == 3

    # Import with merge=False (clean restore)
    res_clean = import_user_data(exported, merge=False)
    assert res_clean["ok"] is True
    restored_words = (mock_appdata / "user_words.txt").read_text(encoding="utf-8")
    assert "سیب" in restored_words
    assert "انار" not in restored_words

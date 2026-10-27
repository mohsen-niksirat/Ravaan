"""Tests verifying specific bug fixes and regression prevention."""

from __future__ import annotations

import json
from unittest.mock import patch

from ravan.core.config import Config, Snippet
from ravan.core.learning import UserLearningEngine
from ravan.core.snippet import render_template
from ravan.core.sync import make_local_backup
from ravan.platform.protocol import sanitize_param_value


def test_clipboard_regex_backreference_injection():
    """Ensure clipboard containing regex backreferences doesn't cause re.error or corruption."""
    malicious_clips = [
        r"\1\2\3",
        r"\g<0>",
        r"\g<unknown>",
        r"hello \9 world",
    ]
    for clip in malicious_clips:
        with patch("ravan.core.snippet._fetch_clipboard", return_value=clip):
            result = render_template("Prefix: {{clipboard}} :Suffix")
            assert result == f"Prefix: {clip} :Suffix"


def test_protocol_url_sanitizes_bidi_overrides():
    """Ensure bidirectional override characters like RLO/LRO are stripped from protocol params."""
    # U+202E is RIGHT-TO-LEFT OVERRIDE
    param_with_rlo = "test\u202Eevil\u202Cend"
    clean = sanitize_param_value(param_with_rlo)
    assert "\u202E" not in clean
    assert "\u202C" not in clean
    assert clean == "testevilend"


def test_sync_backup_and_restore_preserves_all_snippet_fields(tmp_path):
    """Ensure is_regex, app_filter, and is_image are preserved in sync backups."""
    snippets = [

        Snippet(
            trigger="re:^bug[0-9]+$",
            replacement="Issue #",
            enabled=True,
            is_regex=True,
            app_filter="notepad.exe",
            is_image=False,
        ),
        Snippet(
            trigger="/logo",
            replacement="data:image/png;base64,...",
            enabled=False,
            is_regex=False,
            app_filter="",
            is_image=True,
        ),
    ]
    cfg = Config(snippets=snippets)

    with patch("ravan.core.sync.config_dir", return_value=tmp_path), \
         patch("ravan.core.config.config_dir", return_value=tmp_path), \
         patch("ravan.core.config.load_config", return_value=cfg), \
         patch("ravan.core.config.save_config"):
        backup_file = make_local_backup(user_words=["تست"], snippets=[
            {
                "trigger": s.trigger,
                "replacement": s.replacement,
                "enabled": s.enabled,
                "is_regex": s.is_regex,
                "app_filter": s.app_filter,
                "is_image": s.is_image,
            }
            for s in snippets
        ])
        assert backup_file.is_file()

        # Read JSON directly from backup to verify fields
        data = json.loads(backup_file.read_text(encoding="utf-8"))
        saved_snips = data["snippets"]
        assert len(saved_snips) == 2
        assert saved_snips[0]["is_regex"] is True
        assert saved_snips[0]["app_filter"] == "notepad.exe"
        assert saved_snips[1]["is_image"] is True


def test_learning_import_profile_handles_corrupt_entries(tmp_path):
    """Ensure non-numeric entries in learning profile do not crash import_profile."""
    engine = UserLearningEngine(storage_path=tmp_path / "learning.json", auto_load=False)
    corrupted_data = {
        "word_counts": {
            "valid": 5.0,
            "corrupt_str": "not_a_number",
            "corrupt_none": None,
        },
        "transitions": {
            "hello": {
                "world": 2.0,
                "broken": "invalid",
            }
        },
    }
    # Should not raise ValueError or TypeError
    count = engine.import_profile(corrupted_data, merge=False)
    assert count == 1
    assert engine.word_counts.get("valid") == 5.0
    assert "corrupt_str" not in engine.word_counts
    assert engine.transitions["hello"]["world"] == 2.0
    assert "broken" not in engine.transitions["hello"]


def test_package_import_path_traversal_prevention(tmp_path):
    """Ensure malicious paths in package archives cannot escape the target images directory."""
    from ravan.core.package import import_package

    pkg_file = tmp_path / "malicious.ravaanpack"
    payload = {
        "format": "ravaanpack",
        "version": 1,
        "title": "Exploit Package",
        "author": "Attacker",
        "description": "Attempts path traversal",
        "snippets": [
            {
                "trigger": ":evil",
                "replacement": "",
                "is_image": True,
                "image_data_b64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
                "image_filename": "../../escaped.txt",
            }
        ],
    }

    images_dir = tmp_path / "snippets" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    pkg_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    imported = import_package(pkg_file, image_dest_dir=images_dir)
    assert len(imported) == 1
    # File must not exist outside images directory
    assert not (tmp_path / "escaped.txt").exists()
    # Instead, it should be contained safely inside images directory
    assert (images_dir / "escaped.txt").is_file()


def test_calc_negative_power_complex_rejected():
    """Ensure mathematical expressions resulting in complex numbers return None safely."""
    from ravan.core.calc import calculate

    # (-4)**0.5 is 2j in Python; calculate should return None, not crash or return complex
    res = calculate("(-4)**0.5")
    assert res is None


def test_calc_persian_decimal_percentage():
    """Ensure Persian decimal separator works combined with percentage calculation."""
    from ravan.core.calc import calculate

    res = calculate("۱۲٫۵%")
    assert res is not None
    # Result should represent 0.125 in Persian digits
    from ravan.core.normalizer import fa_to_en_digits

    assert fa_to_en_digits(res) == "0.125"


def test_cliphistory_prunes_evicted_timestamps(tmp_path):
    """Ensure evicted items from deque do not accumulate in _timestamps dict."""
    from ravan.core.cliphistory import ClipboardHistory

    hist_file = tmp_path / "clip.json"
    hist = ClipboardHistory(maxlen=3, storage_path=hist_file)

    for i in range(10):
        hist.add(f"item_{i}", ignore_passwords=False)

    # Deque maxlen is 3, so only 3 items should be present
    assert len(hist.items()) == 3
    # Timestamps should be strictly pruned to the 3 active items
    assert len(hist._timestamps) == 3
    assert set(hist._timestamps.keys()) == set(hist.items())

    # Reload from disk and verify disk storage is also clean
    loaded = ClipboardHistory(maxlen=3, storage_path=hist_file)
    assert len(loaded._timestamps) == 3


def test_cliphistory_oversized_item_rejected(tmp_path):
    """Ensure items larger than 20,000 characters are rejected from history."""
    from ravan.core.cliphistory import ClipboardHistory

    hist = ClipboardHistory(maxlen=10, storage_path=tmp_path / "clip.json")
    giant_string = "a" * 25_000
    added = hist.add(giant_string)
    assert added is False
    assert len(hist.items()) == 0


def test_send_ctrl_v_invokes_shortcut():
    """Ensure send_ctrl_v exists in ravan.platform.inject and dispatches Ctrl+V."""
    from ravan.platform import winapi as w
    from ravan.platform.inject import send_ctrl_v

    with patch("ravan.platform.inject.send_shortcut") as mock_shortcut:
        send_ctrl_v()
        mock_shortcut.assert_called_once_with([w.VK_CONTROL], ord("V"))


def test_config_backward_compatibility_properties():
    """Ensure properties aliasing legacy wizard fields properly read and mutate config state."""
    cfg = Config()

    # Word prediction property
    cfg.word_prediction_enabled = False
    assert cfg.prediction_enabled is False
    cfg.word_prediction_enabled = True
    assert cfg.prediction_enabled is True
    assert cfg.word_prediction_enabled is True

    # Autofix wrong layout property
    cfg.autofix_wrong_layout = False
    assert cfg.autofix_mode == "off"
    assert cfg.autofix_wrong_layout is False
    cfg.autofix_wrong_layout = True
    assert cfg.autofix_mode == "safe"
    assert cfg.autofix_wrong_layout is True

    # Fix punctuation property
    cfg.fix_punctuation = False
    assert cfg.fix_punctuation_spacing is False
    cfg.fix_punctuation = True
    assert cfg.fix_punctuation_spacing is True
    assert cfg.fix_punctuation is True

    # Language property
    cfg.language = "fa"
    assert cfg.ui_language == "fa"
    assert cfg.language == "fa"



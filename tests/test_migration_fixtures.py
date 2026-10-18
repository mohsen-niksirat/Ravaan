"""Comprehensive migration test harness verifying lossless config upgrade across legacy versions."""

from __future__ import annotations

import json
from pathlib import Path

from ravan.core.config import Config, config_from_dict, migrate_config_dict
from ravan.core.data_manifest import (
    get_data_manifest,
    get_storage_summary,
    reset_data_file,
    validate_backup_manifest,
)

V04_CONFIG_FIXTURE = {
    "convert_hotkey": {"key": "F12", "modifiers": []},
    "prediction_enabled": True,
    "autocorrect_enabled": False,
    "excluded_apps": ["cmd.exe", "powershell.exe"],
    "snippets": [
        {"trigger": "eml", "replacement": "user@example.com", "enabled": True}
    ],
}

V05_CONFIG_FIXTURE = {
    "schema_version": 1,
    "convert_hotkey": {"key": "Space", "modifiers": ["shift"]},
    "prediction_enabled": True,
    "prediction_debounce_ms": 75,
    "auto_zwnj_enabled": True,
    "shift_space_zwnj": True,
    "inline_calc_enabled": True,
    "quickpick_digits": True,
    "english_dict_enabled": True,
    "persian_dict_enabled": True,
    "excluded_apps": ["code.exe", "sublime_text.exe"],
    "snippets": [
        {"trigger": "addr", "replacement": "Tehran, Iran", "enabled": True}
    ],
}

V07_CONFIG_FIXTURE = {
    "schema_version": 2,
    "convert_hotkey": {"key": "F8", "modifiers": ["ctrl"]},
    "quick_stats_hotkey": {"key": "F9", "modifiers": ["ctrl", "alt"]},
    "theme_mode": "dark",
    "sync_backend": "webdav",
    "webdav_url": "https://nextcloud.mycompany.org/remote.php/webdav",
    "webdav_username": "ravaan_user",
    "cloud_sync_enabled": True,
    "sync_interval_min": 15,
    "excluded_apps": ["keepass.exe", "1password.exe"],
    "snippets": [
        {"trigger": "phn", "replacement": "+989120000000", "enabled": True}
    ],
}


def test_v04_to_v10_migration():
    """Verify v0.4 legacy config (no schema_version) migrates losslessly to schema 3."""
    raw = dict(V04_CONFIG_FIXTURE)
    migrated = migrate_config_dict(raw)

    assert migrated["schema_version"] == 3
    assert migrated["prediction_enabled"] is True
    assert migrated["autocorrect_enabled"] is False
    assert migrated["convert_hotkey"] == {"key": "F12", "modifiers": []}
    assert migrated["excluded_apps"] == ["cmd.exe", "powershell.exe"]
    assert len(migrated["snippets"]) == 1
    assert migrated["snippets"][0]["trigger"] == "eml"

    # Default values filled correctly
    assert migrated["sync_backend"] == "gist"
    assert migrated["sync_interval_min"] == 0
    assert migrated["sync_learning_profile"] is False
    assert migrated["theme_mode"] == "auto"

    cfg = config_from_dict(migrated)
    assert isinstance(cfg, Config)
    assert cfg.convert_hotkey.key == "F12"


def test_v05_to_v10_migration():
    """Verify v0.5 config (schema_version 1) migrates losslessly to schema 3."""
    raw = dict(V05_CONFIG_FIXTURE)
    migrated = migrate_config_dict(raw)

    assert migrated["schema_version"] == 3
    assert migrated["convert_hotkey"] == {"key": "Space", "modifiers": ["shift"]}
    assert migrated["prediction_debounce_ms"] == 75
    assert migrated["auto_zwnj_enabled"] is True
    assert migrated["shift_space_zwnj"] is True
    assert migrated["inline_calc_enabled"] is True
    assert migrated["excluded_apps"] == ["code.exe", "sublime_text.exe"]
    assert migrated["sync_learning_profile"] is False

    cfg = config_from_dict(migrated)
    assert isinstance(cfg, Config)
    assert cfg.auto_zwnj_enabled is True
    assert cfg.prediction_debounce_ms == 75


def test_v07_to_v10_migration():
    """Verify v0.7 config (schema_version 2) preserves sync credentials and theme mode."""
    raw = dict(V07_CONFIG_FIXTURE)
    migrated = migrate_config_dict(raw)

    assert migrated["schema_version"] == 3
    assert migrated["convert_hotkey"] == {"key": "F8", "modifiers": ["ctrl"]}
    assert migrated["quick_stats_hotkey"] == {"key": "F9", "modifiers": ["ctrl", "alt"]}
    assert migrated["theme_mode"] == "dark"
    assert migrated["sync_backend"] == "webdav"
    assert migrated["webdav_url"] == "https://nextcloud.mycompany.org/remote.php/webdav"
    assert migrated["webdav_username"] == "ravaan_user"
    assert migrated["cloud_sync_enabled"] is True
    assert migrated["sync_interval_min"] == 15
    assert migrated["sync_learning_profile"] is False
    assert "keepass.exe" in migrated["excluded_apps"]

    cfg = config_from_dict(migrated)
    assert isinstance(cfg, Config)
    assert cfg.theme_mode == "dark"
    assert cfg.sync_backend == "webdav"
    assert cfg.sync_interval_min == 15


def test_data_manifest_and_storage_summary(tmp_path: Path, monkeypatch):
    """Test data manifest inspection, storage summary, and backup manifest validator."""
    monkeypatch.setattr("ravan.core.data_manifest.config_dir", lambda: tmp_path)

    # Initially empty dir
    manifest = get_data_manifest()
    assert manifest["app"] == "Ravaan"
    assert manifest["schema_version"] == 3
    assert "config.json" in manifest["files"]
    assert manifest["files"]["config.json"]["exists"] is False

    summary = get_storage_summary()
    assert summary["total_files"] == 0
    assert summary["total_bytes"] == 0

    # Write sample files
    (tmp_path / "config.json").write_text(json.dumps(V07_CONFIG_FIXTURE), encoding="utf-8")
    (tmp_path / "user_words.txt").write_text("کلمه۱\nکلمه۲\n", encoding="utf-8")

    manifest2 = get_data_manifest()
    assert manifest2["files"]["config.json"]["exists"] is True
    assert manifest2["files"]["user_words.txt"]["exists"] is True
    assert manifest2["files"]["config.json"]["size_bytes"] > 0

    summary2 = get_storage_summary()
    assert summary2["total_files"] == 2
    assert summary2["total_bytes"] > 0


def test_validate_backup_manifest():
    """Verify backup manifest validation handles both Ravan and Ravaan archives up to schema 3."""
    # Valid v0.7 manifest
    ok, msg = validate_backup_manifest({
        "app": "Ravan",
        "schema_version": 2,
        "files": ["config.json", "user_words.txt"],
    })
    assert ok is True
    assert "Valid" in msg

    # Valid v1.0 manifest
    ok, msg = validate_backup_manifest({
        "app": "Ravaan",
        "schema_version": 3,
        "files": ["config.json", "user_words.txt", "learning_profile.json"],
    })
    assert ok is True

    # Invalid app
    ok, msg = validate_backup_manifest({"app": "OtherApp", "schema_version": 3, "files": []})
    assert ok is False
    assert "Unsupported application" in msg

    # Invalid schema version
    ok, msg = validate_backup_manifest({"app": "Ravaan", "schema_version": 99, "files": []})
    assert ok is False
    assert "Unsupported backup schema version" in msg


def test_reset_data_file(tmp_path: Path, monkeypatch):
    """Verify resetting a data file restores default content and creates a safety backup."""
    monkeypatch.setattr("ravan.core.data_manifest.config_dir", lambda: tmp_path)

    words_file = tmp_path / "user_words.txt"
    words_file.write_text("custom_word_1\ncustom_word_2\n", encoding="utf-8")

    assert reset_data_file("user_words.txt") is True
    assert words_file.read_text(encoding="utf-8") == ""

    # Non-resettable or nonexistent
    assert reset_data_file("unknown_file.xyz") is False

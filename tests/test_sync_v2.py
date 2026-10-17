"""Comprehensive unit tests for Sync 2.0 & Settings Robustness (Phase 3)."""

from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

from ravan.core.config import (
    DEFAULT_EXCLUDED_APPS,
    Config,
    load_config,
    migrate_config_dict,
)
from ravan.core.sync import (
    merge_dictionaries,
    merge_snippets,
    pull_sync,
    push_sync,
)
from ravan.core.webdav import WebDAVClient
from ravan.ui.app_polling import AppPollingMixin
from ravan.ui.settings_reset import reset_tab_defaults


def test_config_schema_migration():
    v1_data = {
        "schema_version": 1,
        "prediction_enabled": True,
        "convert_hotkey": {"key": "F12", "modifiers": []},
    }
    migrated = migrate_config_dict(dict(v1_data))
    assert migrated["schema_version"] == 2
    assert migrated["sync_backend"] == "gist"
    assert migrated["sync_interval_min"] == 0
    assert migrated["webdav_url"] == ""


def test_config_corruption_recovery(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text("{this is corrupt json: bad syntax", encoding="utf-8")

    with patch("ravan.core.config.config_path", return_value=cfg_file):
        loaded = load_config()
        assert isinstance(loaded, Config)
        # Verify corrupt file was moved aside
        corrupt_files = list(tmp_path.glob("config.json.corrupt.*"))
        assert len(corrupt_files) == 1
        # And fresh valid config was created
        assert cfg_file.is_file()
        assert json.loads(cfg_file.read_text(encoding="utf-8"))["schema_version"] == 2


def test_config_corruption_non_dict_root(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text("[\"not\", \"a\", \"dict\"]", encoding="utf-8")

    with patch("ravan.core.config.config_path", return_value=cfg_file):
        loaded = load_config()
        assert isinstance(loaded, Config)
        corrupt_files = list(tmp_path.glob("config.json.corrupt.*"))
        assert len(corrupt_files) == 1


def test_merge_dictionaries_union_and_deduplication():
    local = ["سلام", "روان", "Python", "# comment", ""]
    remote = ["روان", "python", "توسعه", "دانشگاه"]

    merged = merge_dictionaries(local, remote)
    assert "سلام" in merged
    assert "روان" in merged
    assert "Python" in merged
    assert "توسعه" in merged
    assert "دانشگاه" in merged
    assert "# comment" not in merged
    assert "" not in merged
    # Deduplication is case-insensitive, preserves local casing
    assert sum(1 for w in merged if w.lower() == "python") == 1
    assert "Python" in merged


def test_merge_snippets_conflict_keep_both():
    local = [
        {"trigger": "@@", "replacement": "local@mail.com", "enabled": True},
        {"trigger": "/w", "replacement": "welcome", "enabled": True},
    ]
    remote = [
        {"trigger": "@@", "replacement": "remote@mail.com", "enabled": True},
        {"trigger": "/bye", "replacement": "goodbye", "enabled": True},
    ]

    merged, conflicts = merge_snippets(local, remote, resolution_strategy="keep_both")
    assert len(conflicts) == 1
    assert conflicts[0]["trigger"] == "@@"

    trigs = {s["trigger"]: s["replacement"] for s in merged}
    assert trigs["@@"] == "local@mail.com"
    assert trigs["@@_remote"] == "remote@mail.com"
    assert trigs["/w"] == "welcome"
    assert trigs["/bye"] == "goodbye"


def test_merge_snippets_conflict_remote_override():
    local = [{"trigger": "@@", "replacement": "local@mail.com", "enabled": True}]
    remote = [{"trigger": "@@", "replacement": "remote@mail.com", "enabled": True}]

    merged, conflicts = merge_snippets(local, remote, resolution_strategy="remote")
    assert len(conflicts) == 1
    assert len(merged) == 1
    assert merged[0]["replacement"] == "remote@mail.com"


def test_in_memory_fake_webdav_client():
    fake_server: dict[str, bytes] = {}

    def fake_urlopen(req, timeout=8.0):
        url = req.full_url
        method = req.get_method()
        if method == "PUT":
            fake_server[url] = req.data
            resp = MagicMock()
            resp.status = 201
            resp.__enter__.return_value = resp
            return resp
        elif method == "GET":
            if url in fake_server:
                resp = MagicMock()
                resp.status = 200
                resp.read.return_value = fake_server[url]
                resp.__enter__.return_value = resp
                return resp
            err = urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO())
            raise err
        raise ValueError(f"Unexpected method: {method}")

    client = WebDAVClient(
        url="https://cloud.example.com/remote.php/dav/files/user/Ravaan",
        username="testuser",
        password="supersecretpassword",
    )

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        # 1. Pull on empty server returns empty without error
        pull_empty = client.pull()
        assert pull_empty["ok"] is True
        assert pull_empty["user_words"] == []
        assert pull_empty["snippets"] == []

        # 2. Push words and snippets
        words = ["سلام", "روان"]
        snips = [{"trigger": "@@", "replacement": "user@test.org", "enabled": True}]
        push_res = client.push(words, snips)
        assert push_res["ok"] is True
        assert "user_words.txt" in list(fake_server.keys())[0]

        # 3. Pull retrieves exact data pushed
        pull_res = client.pull()
        assert pull_res["ok"] is True
        assert pull_res["user_words"] == words
        assert pull_res["snippets"] == snips


def test_webdav_password_sanitization_in_errors():
    client = WebDAVClient(
        url="https://cloud.example.com/dav",
        username="u",
        password="MySecretPassword123",
    )

    def failing_urlopen(req, timeout=8.0):
        raise RuntimeError("Connection failed with credentials MySecretPassword123")

    with patch("urllib.request.urlopen", side_effect=failing_urlopen):
        res = client.push(["word"], [])
        assert res["ok"] is False
        assert "MySecretPassword123" not in res["error"]
        assert "[REDACTED_TOKEN]" in res["error"]


def test_push_and_pull_sync_dispatch():
    cfg_gist = Config(sync_backend="gist", gist_token="tok", gist_id="gid")
    cfg_webdav = Config(
        sync_backend="webdav",
        webdav_url="https://dav.test/Ravaan",
        webdav_username="u",
        webdav_password="p",
    )

    with patch("ravan.core.sync.push_to_gist") as mock_gist_push, \
         patch("ravan.core.webdav.WebDAVClient.push") as mock_dav_push:
        mock_gist_push.return_value = {"ok": True}
        mock_dav_push.return_value = {"ok": True}

        push_sync(cfg_gist, ["w"], [])
        assert mock_gist_push.called

        push_sync(cfg_webdav, ["w"], [])
        assert mock_dav_push.called

    with patch("ravan.core.sync.pull_from_gist") as mock_gist_pull, \
         patch("ravan.core.webdav.WebDAVClient.pull") as mock_dav_pull:
        mock_gist_pull.return_value = {"ok": True, "user_words": [], "snippets": []}
        mock_dav_pull.return_value = {"ok": True, "user_words": [], "snippets": []}

        pull_sync(cfg_gist)
        assert mock_gist_pull.called

        pull_sync(cfg_webdav)
        assert mock_dav_pull.called


def test_background_sync_debounce_and_offline():
    class DummyApp(AppPollingMixin):
        def __init__(self):
            self.cfg = Config(
                cloud_sync_enabled=True,
                sync_interval_min=15,
                sync_backend="gist",
                gist_token="dummy",
                gist_id="dummy",
            )
            self._last_key_time = 0.0
            self._last_bg_sync_poll = 0.0
            self._last_sync_attempt = 0.0
            self._sync_backoff_delay = 0.0
            self._sync_in_progress = False
            self._pending_sync_queued = True

    app = DummyApp()
    import time

    now = time.monotonic()

    # 1. When user just typed 2s ago -> debounced, no sync attempt
    app._last_key_time = now - 2.0
    app._last_bg_sync_poll = 0.0
    with patch("threading.Thread") as mock_thread:
        app._poll_background_sync()
        assert not mock_thread.called

    # 2. When idle for >15s -> triggers sync
    app._last_key_time = now - 20.0
    app._last_bg_sync_poll = 0.0
    with patch("threading.Thread") as mock_thread:
        app._poll_background_sync()
        assert mock_thread.called


def test_settings_reset_tab_defaults():
    class FakeVar:
        def __init__(self, val=None):
            self._val = val

        def get(self):
            return self._val

        def set(self, val):
            self._val = val

    class FakeText:
        def __init__(self):
            self._content = ""

        def get(self, *args):
            return self._content

        def delete(self, *args):
            self._content = ""

        def insert(self, idx, text):
            self._content = text

    class DummySettingsWin:
        def __init__(self):
            self._ui_language_var = FakeVar("فارسی")
            self._prediction_var = FakeVar(False)
            self._autocorrect_var = FakeVar(False)
            self._convert_var = FakeVar("Ctrl+Shift+K")
            self._excl_text = FakeText()
            self._excl_text.insert("1.0", "custom_app.exe")
            self._managed_snippets = [{"trigger": "custom"}]
            self._update_snip_display = MagicMock()
            self._sync_backend_var = FakeVar("webdav")
            self._gist_token_var = FakeVar("secret")

    win = DummySettingsWin()

    with patch("tkinter.messagebox.askyesno", return_value=True):
        # Reset prediction
        reset_tab_defaults(win, "prediction")
        assert win._prediction_var.get() is True
        assert win._autocorrect_var.get() is True

        # Reset hotkeys
        reset_tab_defaults(win, "hotkeys")
        assert win._convert_var.get() == "F12"

        # Reset exclusions
        reset_tab_defaults(win, "exclusions")
        assert DEFAULT_EXCLUDED_APPS[0] in win._excl_text.get("1.0", "end")

        # Reset sync
        reset_tab_defaults(win, "sync")
        assert win._sync_backend_var.get() == "gist"
        assert win._gist_token_var.get() == ""

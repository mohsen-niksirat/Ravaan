"""Unit tests for Quick text stats (M15) and GitHub Gist Cloud Sync."""

from __future__ import annotations

import concurrent.futures
import json
from unittest.mock import MagicMock, patch

from ravan.core.sync import make_local_backup, pull_from_gist, push_to_gist
from ravan.core.text_stats import calculate_text_stats, format_stats_summary


def test_calculate_text_stats_persian_and_english():
    text = "سلام دوستان عزیز! Welcome to Ravaan assistant."
    stats = calculate_text_stats(text)

    assert stats["word_count"] == 7
    assert stats["char_count"] == len(text)
    assert stats["char_no_spaces"] < stats["char_count"]
    assert stats["reading_time_sec"] >= 1
    # Check Persian & English ratio
    assert stats["persian_pct"] > 0
    assert stats["english_pct"] > 0
    assert "فارسی" in stats["ratio_str"]
    assert "English" in stats["ratio_str"]

    summary = format_stats_summary(stats)
    assert "Text Statistics" in summary
    assert "7" in summary


def test_calculate_text_stats_empty():
    stats = calculate_text_stats("")
    assert stats["word_count"] == 0
    assert stats["char_count"] == 0
    assert stats["ratio_str"] == "—"


def test_sync_make_local_backup(tmp_path):
    user_words = ["روان", "تست", "کلمه"]
    snippets = [{"trigger": "@@", "replacement": "test@domain.com", "enabled": True}]

    with patch("ravan.core.sync.config_dir", return_value=tmp_path):
        backup_file = make_local_backup(user_words, snippets)
        assert backup_file.is_file()
        data = json.loads(backup_file.read_text(encoding="utf-8"))
        assert data["user_words"] == user_words
        assert data["snippets"] == snippets
        assert "timestamp" in data


def test_push_to_gist_success(tmp_path):
    user_words = ["واژه"]
    snippets = [{"trigger": "@@", "replacement": "val", "enabled": True}]

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp

    with patch("ravan.core.sync.config_dir", return_value=tmp_path), \
         patch("urllib.request.urlopen", return_value=mock_resp):
        res = push_to_gist("ghp_fake_token", "gist_fake_id_123", user_words, snippets)
        assert res["ok"] is True
        assert res["error"] is None
        assert "timestamp" in res


def test_pull_from_gist_success():
    fake_body = json.dumps({
        "files": {
            "user_words.txt": {
                "content": "سلام\nروان\n# comment line\nامروز\n"
            },
            "snippets.json": {
                "content": json.dumps([
                    {"trigger": "/w", "replacement": "welcome", "enabled": True},
                    {"trigger": "/d", "replacement": "disabled", "enabled": False},
                ])
            },
        }
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = fake_body
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = pull_from_gist("ghp_fake_token", "gist_fake_id_123")
        assert res["ok"] is True
        assert res["user_words"] == ["سلام", "روان", "امروز"]
        assert len(res["snippets"]) == 2
        assert res["snippets"][0]["trigger"] == "/w"
        assert res["snippets"][1]["enabled"] is False


def test_sync_missing_credentials():
    res1 = push_to_gist("", "", [], [])
    assert res1["ok"] is False
    assert "Missing" in res1["error"]

    res2 = pull_from_gist("", "")
    assert res2["ok"] is False
    assert "Missing" in res2["error"]


def test_restore_backup(tmp_path):
    from ravan.core.sync import restore_backup

    with patch("ravan.core.sync.config_dir", return_value=tmp_path):
        # 1. No backup initially
        assert restore_backup() is None

        # 2. Create a backup
        words = ["تست", "بازیابی"]
        snippets = [{"trigger": "/r", "replacement": "restored", "enabled": True}]
        backup_file = make_local_backup(words, snippets)
        assert backup_file.is_file()

        # 3. Restore from backup
        res = restore_backup(backup_file)
        assert res is not None
        restored_words, restored_snips = res
        assert restored_words == words
        assert len(restored_snips) == 1
        assert restored_snips[0]["trigger"] == "/r"


def test_pull_from_gist_creates_backup(tmp_path):
    fake_body = json.dumps({
        "files": {
            "user_words.txt": {"content": "کلمه\n"},
            "snippets.json": {"content": "[]"},
        }
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = fake_body
    mock_resp.__enter__.return_value = mock_resp

    with patch("ravan.core.sync.config_dir", return_value=tmp_path), \
         patch("urllib.request.urlopen", return_value=mock_resp):
        pull_from_gist(
            "ghp_fake_token",
            "gist_fake_id_123",
            current_words=["قدیمی"],
            current_snippets=[{"trigger": "/o", "replacement": "old", "enabled": True}],
        )

        backup_dir = tmp_path / "backups"
        backups = list(backup_dir.glob("sync_backup_*.json"))
        assert len(backups) == 1
        content = json.loads(backups[0].read_text(encoding="utf-8"))
        assert content["user_words"] == ["قدیمی"]


def test_sanitize_error_redacts_tokens():
    from ravan.core.sync import _sanitize_error

    secret = "ghp_VerySecretToken123456789"
    msg = f"Failed to authenticate with bearer {secret} at endpoint"
    sanitized = _sanitize_error(msg, secret)
    assert secret not in sanitized
    assert "[REDACTED_TOKEN]" in sanitized


def test_dict_predictor_thread_safe_lazy_loading():
    from ravan.core.config import Config
    from ravan.core.predictor import DictPredictor

    cfg = Config()
    pred = DictPredictor.from_config(cfg)

    def access_dictionaries():
        en = pred.english
        fa = pred.persian
        lrn = pred.learning
        return (en is not None, fa is not None, lrn is not None)

    # Launch 10 concurrent threads simultaneously accessing lazy loaders
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(access_dictionaries) for _ in range(10)]
        results = [f.result() for f in futures]

    assert all(r == (True, True, True) for r in results)


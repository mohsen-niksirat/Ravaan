"""Unit tests for Quick text stats (M15) and GitHub Gist Cloud Sync."""

from __future__ import annotations

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

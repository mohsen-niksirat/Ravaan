"""Unit tests for GitHub release update checker and version parsing."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from ravan.core.updater import check_for_updates, parse_version


def test_parse_version():
    assert parse_version("0.4.0") == (0, 4, 0)
    assert parse_version("v0.4.1") == (0, 4, 1)
    assert parse_version("v1.2.3-alpha") == (1, 2, 3)
    assert parse_version("2.0") == (2, 0)
    assert parse_version("") == (0, 0, 0)


def test_check_for_updates_available():
    fake_body = json.dumps({
        "tag_name": "v0.5.0",
        "html_url": "https://github.com/mohsen-niksirat/Ravaan/releases/tag/v0.5.0",
        "body": "Major improvements in speed and accuracy.",
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = fake_body
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = check_for_updates(current_ver="0.4.0")
        assert res["has_update"] is True
        assert res["latest_version"] == "0.5.0"
        assert res["release_url"] == "https://github.com/mohsen-niksirat/Ravaan/releases/tag/v0.5.0"
        assert "Major improvements" in res["release_notes"]
        assert res["error"] is None


def test_check_for_updates_already_latest():
    fake_body = json.dumps({
        "tag_name": "v0.4.0",
        "html_url": "https://github.com/mohsen-niksirat/Ravaan/releases/tag/v0.4.0",
        "body": "Current release.",
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = fake_body
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = check_for_updates(current_ver="0.4.0")
        assert res["has_update"] is False
        assert res["latest_version"] == "0.4.0"
        assert res["error"] is None


def test_check_for_updates_network_error():
    import urllib.error

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        res = check_for_updates(current_ver="0.4.0")
        assert res["has_update"] is False
        assert res["error"] == "Connection refused"


def test_lazy_loading_dict_predictor():
    from ravan.core.config import Config
    from ravan.core.predictor import DictPredictor

    cfg = Config()
    pred = DictPredictor.from_config(cfg)

    # Initial state: dictionaries should not be instantiated yet
    assert pred._english is None
    assert pred._persian is None

    # First access loads English dictionary
    en = pred.english
    assert en is not None
    assert pred._english is not None

    # Accessing again returns cached instance
    assert pred.english is en

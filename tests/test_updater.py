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


def test_check_for_updates_404_no_releases():
    import urllib.error

    http_404 = urllib.error.HTTPError(
        url="https://api.github.com/repos/mohsen-niksirat/Ravaan/releases/latest",
        code=404,
        msg="Not Found",
        hdrs=None,  # type: ignore[arg-type]
        fp=None,
    )
    with patch("urllib.request.urlopen", side_effect=http_404):
        res = check_for_updates(current_ver="0.5.0")
        assert res["has_update"] is False
        assert res["error"] is None
        assert "No published releases" in res["release_notes"]


def test_check_for_updates_empty_tag():
    fake_body = json.dumps({"tag_name": ""}).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = fake_body
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = check_for_updates(current_ver="0.5.0")
        assert res["has_update"] is False
        assert res["error"] is None
        assert "No published releases" in res["release_notes"]


def test_is_prerelease():
    from ravan.core.updater import is_prerelease

    assert is_prerelease("1.0.0-rc1") is True
    assert is_prerelease("v1.0.0-rc2") is True
    assert is_prerelease("v1.0.0-beta") is True
    assert is_prerelease("1.0.0-alpha.1") is True
    assert is_prerelease("0.7.0") is False
    assert is_prerelease("v1.0.0") is False


def test_compare_versions():
    from ravan.core.updater import compare_versions

    assert compare_versions("1.0.0", "0.7.0") > 0
    assert compare_versions("1.0.0-rc1", "0.7.0") > 0
    assert compare_versions("1.0.0-rc2", "1.0.0-rc1") > 0
    assert compare_versions("1.0.0", "1.0.0-rc2") > 0
    assert compare_versions("1.0.0-rc1", "1.0.0") < 0
    assert compare_versions("1.0.0", "1.0.0") == 0


def test_check_for_updates_prerelease_ignored_for_stable_user():
    fake_body = json.dumps({
        "tag_name": "v1.0.0-rc1",
        "prerelease": True,
        "html_url": "https://github.com/mohsen-niksirat/Ravaan/releases/tag/v1.0.0-rc1",
        "body": "Release candidate 1",
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = fake_body
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = check_for_updates(current_ver="0.7.0")
        # Stable users should NOT be offered -rc1
        assert res["has_update"] is False


def test_check_for_updates_prerelease_offered_when_allowed():
    fake_body = json.dumps({
        "tag_name": "v1.0.0-rc1",
        "prerelease": True,
        "html_url": "https://github.com/mohsen-niksirat/Ravaan/releases/tag/v1.0.0-rc1",
        "body": "Release candidate 1",
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = fake_body
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = check_for_updates(current_ver="0.7.0", allow_prereleases=True)
        assert res["has_update"] is True
        assert res["latest_version"] == "1.0.0-rc1"


def test_check_for_updates_prerelease_user_gets_newer_rc():
    fake_body = json.dumps([
        {
            "tag_name": "v1.0.0-rc2",
            "prerelease": True,
            "html_url": "https://github.com/mohsen-niksirat/Ravaan/releases/tag/v1.0.0-rc2",
            "body": "Release candidate 2",
        },
        {
            "tag_name": "v1.0.0-rc1",
            "prerelease": True,
            "html_url": "https://github.com/mohsen-niksirat/Ravaan/releases/tag/v1.0.0-rc1",
            "body": "Release candidate 1",
        },
    ]).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = fake_body
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = check_for_updates(current_ver="1.0.0-rc1")
        assert res["has_update"] is True
        assert res["latest_version"] == "1.0.0-rc2"


def test_check_for_updates_multiple_releases_stable_fallback():
    fake_body = json.dumps([
        {
            "tag_name": "v1.0.0-rc1",
            "prerelease": True,
            "html_url": "https://github.com/mohsen-niksirat/Ravaan/releases/tag/v1.0.0-rc1",
            "body": "Release candidate 1",
        },
        {
            "tag_name": "v0.7.0",
            "prerelease": False,
            "html_url": "https://github.com/mohsen-niksirat/Ravaan/releases/tag/v0.7.0",
            "body": "Stable 0.7.0",
        },
    ]).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = fake_body
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        # User on 0.6.0 should skip rc1 and update to 0.7.0
        res = check_for_updates(current_ver="0.6.0")
        assert res["has_update"] is True
        assert res["latest_version"] == "0.7.0"

        # User on 0.7.0 should skip rc1 and stay on 0.7.0
        res2 = check_for_updates(current_ver="0.7.0")
        assert res2["has_update"] is False


def test_in_app_updater_1_0_0_sees_2_0_0_update():
    """Verify in-app updater running v1.0.0 detects v2.0.0 and offers installer download."""
    fake_body = json.dumps([
        {
            "tag_name": "v2.0.0",
            "prerelease": False,
            "html_url": "https://github.com/mohsen-niksirat/Ravaan/releases/tag/v2.0.0",
            "body": "Ravaan v2.0.0 - Major milestone with Snippets 3.0, .ravaanpack, and AI Assistant.",
            "assets": [
                {
                    "name": "Ravaan-Setup-2.0.0.exe",
                    "browser_download_url": "https://github.com/mohsen-niksirat/Ravaan/releases/download/v2.0.0/Ravaan-Setup-2.0.0.exe",
                }
            ],
        }
    ]).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = fake_body
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = check_for_updates(current_ver="1.0.0")
        assert res["has_update"] is True
        assert res["latest_version"] == "2.0.0"
        assert res["installer_url"] == "https://github.com/mohsen-niksirat/Ravaan/releases/download/v2.0.0/Ravaan-Setup-2.0.0.exe"
        assert "v2.0.0" in res["release_notes"]


"""Unit tests for Installer, In-App Updater, Protocol Handler, and Distribution (Phase 4)."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

from ravan.core.updater import (
    check_for_updates,
    download_and_launch_installer,
    extract_changelog_summary,
    find_installer_asset,
    parse_version,
)
from ravan.platform.protocol import (
    is_protocol_registered,
    parse_protocol_url,
    register_protocol,
)
from scripts.generate_hashes import format_markdown_table, sha256_file


def test_parse_version():
    assert parse_version("v0.5.0") == (0, 5, 0)
    assert parse_version("0.6.1") == (0, 6, 1)
    assert parse_version("v1.0.0-beta.2") == (1, 0, 0)
    assert parse_version("v0.6.0") > parse_version("v0.5.0")
    assert parse_version("v0.5.1") > parse_version("0.5.0")
    assert parse_version("invalid") == (0, 0, 0)


def test_extract_changelog_summary():
    body = (
        "# Release v0.6.0\n"
        "---\n"
        "• Added Inno Setup installer\n"
        "• Added in-app updater\n"
        "• Added WebDAV support\n"
        "\n"
        "Full changelog available at..."
    )
    summary = extract_changelog_summary(body, max_lines=3)
    assert "Added Inno Setup installer" in summary
    assert "Added in-app updater" in summary
    assert "Added WebDAV support" in summary
    assert "# Release" not in summary

    assert extract_changelog_summary("") == "Bug fixes and performance improvements."


def test_find_installer_asset():
    assets = [
        {"name": "checksums.txt", "browser_download_url": "https://test/checksums.txt"},
        {"name": "Ravaan.exe", "browser_download_url": "https://test/Ravaan.exe"},
        {"name": "Ravaan-Setup-0.6.0.exe", "browser_download_url": "https://test/setup.exe"},
    ]
    installer = find_installer_asset(assets)
    assert installer is not None
    assert installer["name"] == "Ravaan-Setup-0.6.0.exe"
    assert installer["browser_download_url"] == "https://test/setup.exe"

    # Fallback to portable exe if no setup in name
    assets_no_setup = [
        {"name": "Ravaan.exe", "browser_download_url": "https://test/Ravaan.exe"}
    ]
    assert find_installer_asset(assets_no_setup)["name"] == "Ravaan.exe"
    assert find_installer_asset([]) is None


def test_check_for_updates_available():
    payload = json.dumps({
        "tag_name": "v0.9.0",
        "html_url": "https://github.com/mohsen-niksirat/Ravaan/releases/tag/v0.9.0",
        "body": "Major improvements\n• Fast typing\n• Smart sync",
        "assets": [
            {
                "name": "Ravaan-Setup-0.9.0.exe",
                "browser_download_url": "https://github.com/mohsen-niksirat/Ravaan/releases/download/v0.9.0/Ravaan-Setup-0.9.0.exe",
            }
        ],
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = payload
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = check_for_updates(current_ver="0.5.0")
        assert res["has_update"] is True
        assert res["latest_version"] == "0.9.0"
        assert res["installer_url"] == "https://github.com/mohsen-niksirat/Ravaan/releases/download/v0.9.0/Ravaan-Setup-0.9.0.exe"
        assert "Major improvements" in res["changelog_summary"]
        assert res["error"] is None


def test_check_for_updates_up_to_date():
    payload = json.dumps({
        "tag_name": "v0.5.0",
        "html_url": "https://github.com/mohsen-niksirat/Ravaan/releases/tag/v0.5.0",
        "body": "Current release",
        "assets": [],
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = payload
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = check_for_updates(current_ver="0.5.0")
        assert res["has_update"] is False
        assert res["latest_version"] == "0.5.0"


def test_download_and_launch_installer(tmp_path):
    fake_exe_bytes = b"MZ" + b"\x00" * 1024

    mock_resp = MagicMock()
    mock_resp.headers = {"Content-Length": str(len(fake_exe_bytes))}
    mock_resp.read.side_effect = [fake_exe_bytes, b""]
    mock_resp.__enter__.return_value = mock_resp

    progress_values = []
    exit_called = []

    def on_progress(pct: float) -> None:
        progress_values.append(pct)

    def on_exit() -> None:
        exit_called.append(True)

    with patch("urllib.request.urlopen", return_value=mock_resp), \
         patch("subprocess.Popen") as mock_popen, \
         patch("tempfile.gettempdir", return_value=str(tmp_path)):

        ok = download_and_launch_installer(
            download_url="https://test/setup.exe",
            installer_name="Test-Setup.exe",
            on_progress=on_progress,
            on_ready_to_exit=on_exit,
        )
        assert ok is True
        assert mock_popen.called
        assert len(exit_called) == 1
        assert len(progress_values) >= 1
        assert (tmp_path / "Test-Setup.exe").is_file()


def test_download_insecure_url_rejected():
    import pytest

    with pytest.raises(ValueError, match="only HTTPS is permitted"):
        download_and_launch_installer(download_url="http://insecure.test/setup.exe")


def test_download_sha256_verification(tmp_path):
    import hashlib

    fake_exe = b"MZ" + b"\x01" * 512
    valid_hash = hashlib.sha256(fake_exe).hexdigest()

    mock_resp = MagicMock()
    mock_resp.headers = {"Content-Length": str(len(fake_exe))}
    mock_resp.read.side_effect = [fake_exe, b""]
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp), \
         patch("subprocess.Popen"), \
         patch("tempfile.gettempdir", return_value=str(tmp_path)):

        # 1. Matching SHA256 passes
        ok = download_and_launch_installer(
            download_url="https://test/setup.exe",
            installer_name="Verified-Setup.exe",
            expected_sha256=valid_hash,
        )
        assert ok is True
        assert (tmp_path / "Verified-Setup.exe").is_file()

        # 2. Mismatched SHA256 fails and removes file
        mock_resp.read.side_effect = [fake_exe, b""]
        bad_ok = download_and_launch_installer(
            download_url="https://test/setup.exe",
            installer_name="Bad-Setup.exe",
            expected_sha256="0000000000000000000000000000000000000000000000000000000000000000",
        )
        assert bad_ok is False
        assert not (tmp_path / "Bad-Setup.exe").is_file()


def test_download_invalid_pe_magic_rejected(tmp_path):
    fake_non_exe = b"NOT_A_PE_BINARY" + b"\x00" * 100

    mock_resp = MagicMock()
    mock_resp.headers = {"Content-Length": str(len(fake_non_exe))}
    mock_resp.read.side_effect = [fake_non_exe, b""]
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp), \
         patch("subprocess.Popen"), \
         patch("tempfile.gettempdir", return_value=str(tmp_path)):

        ok = download_and_launch_installer(
            download_url="https://test/fake.exe",
            installer_name="Fake.exe",
        )
        assert ok is False
        assert not (tmp_path / "Fake.exe").is_file()


def test_extract_sha256_for_installer_helper():
    from ravan.core.updater import extract_sha256_for_installer

    body = (
        "## Release v1.1.0\n"
        "SHA256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n"
        "Download below:"
    )
    extracted = extract_sha256_for_installer([], "Ravaan-Setup.exe", body)
    assert extracted == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_parse_protocol_url():
    # Simple action
    p1 = parse_protocol_url("ravan://settings")
    assert p1["action"] == "settings"
    assert p1["params"] == {}

    # Action with query params
    p2 = parse_protocol_url("ravan://settings?tab=sync&dark=1")
    assert p2["action"] == "settings"
    assert p2["params"] == {"tab": "sync", "dark": "1"}

    # Stats and snippet actions
    p3 = parse_protocol_url("ravan://stats")
    assert p3["action"] == "stats"

    p4 = parse_protocol_url("ravan://snippet?trigger=@@")
    assert p4["action"] == "snippet"
    assert p4["params"]["trigger"] == "@@"

    # Non-ravan scheme rejected
    p5 = parse_protocol_url("https://github.com/mohsen-niksirat/Ravaan")
    assert p5["action"] == ""
    assert p5["params"] == {}


def test_protocol_registration_mock():
    fake_reg: dict[str, Any] = {}

    class MockKey:
        def __init__(self, path):
            self.path = path
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    def mock_create_key(root, subkey):
        fake_reg[subkey] = {}
        return MockKey(subkey)

    def mock_set_value(key, name, reserved, type_, val):
        fake_reg[key.path][name] = val

    def mock_open_key(root, subkey):
        if subkey in fake_reg:
            return MockKey(subkey)
        raise OSError("Key not found")

    def mock_query_val(key, name):
        if key.path in fake_reg and name in fake_reg[key.path]:
            return fake_reg[key.path][name], 1
        raise OSError("Value not found")

    mock_winreg = MagicMock()
    mock_winreg.HKEY_CURRENT_USER = 1
    mock_winreg.REG_SZ = 1
    mock_winreg.CreateKey = mock_create_key
    mock_winreg.SetValueEx = mock_set_value
    mock_winreg.OpenKey = mock_open_key
    mock_winreg.QueryValueEx = mock_query_val

    with patch("sys.platform", "win32"), patch.dict("sys.modules", {"winreg": mock_winreg}):
        assert register_protocol("C:\\Apps\\Ravaan.exe") is True
        assert r"Software\Classes\ravan" in fake_reg
        assert is_protocol_registered() is True


def test_sha256_and_markdown_table(tmp_path):
    test_file = tmp_path / "Ravaan.exe"
    test_file.write_bytes(b"Hello Ravaan executable data 12345")

    digest = sha256_file(test_file)
    assert len(digest) == 64
    assert isinstance(digest, str)

    table = format_markdown_table([("Ravaan.exe", digest, len(b"Hello Ravaan executable data 12345"))])
    assert "| `Ravaan.exe` |" in table
    assert digest in table
    assert "SHA256 Checksum" in table

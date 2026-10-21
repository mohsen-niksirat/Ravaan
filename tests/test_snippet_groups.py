"""Tests for Snippets 3.0: Image snippets and per-app snippet groups (Phase 3)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

from ravan.core.config import Config, Snippet, config_from_dict, config_to_dict
from ravan.core.config_types import SnippetGroup
from ravan.core.snippet import (
    SnippetEngine,
    group_matches_app,
    resolve_image_snippet,
    snippet_matches_app,
    snippets_from_json,
    snippets_to_json,
    validate_image_path,
)


def test_group_matches_app_exe():
    grp = SnippetGroup(id="browsers", name="Web Browsers", matchers=["chrome.exe", "msedge.exe", "firefox"])
    assert group_matches_app(grp, "chrome.exe") is True
    assert group_matches_app(grp, "Chrome.EXE") is True
    assert group_matches_app(grp, "firefox.exe") is True
    assert group_matches_app(grp, r"C:\Program Files\Google\Chrome\Application\chrome.exe") is True
    assert group_matches_app(grp, "notepad.exe") is False
    assert group_matches_app(grp, None) is False


def test_group_matches_app_window_class():
    grp = SnippetGroup(id="terminals", name="Terminals", matchers=["class:ConsoleWindowClass", "wt.exe"])
    assert group_matches_app(grp, "cmd.exe", window_class="ConsoleWindowClass") is True
    assert group_matches_app(grp, "cmd.exe", window_class="Notepad") is False
    assert group_matches_app(grp, "wt.exe", window_class="WindowsTerminal") is True


def test_group_disabled_guard():
    grp = SnippetGroup(id="code", name="Code", matchers=["code.exe"], enabled=False)
    assert group_matches_app(grp, "code.exe") is False


def test_group_empty_matchers():
    grp = SnippetGroup(id="empty", name="Empty", matchers=[], enabled=True)
    assert group_matches_app(grp, "code.exe") is False


def test_snippet_matches_app_global():
    s_global = Snippet(trigger=";sig", replacement="Regards", groups=[])
    assert snippet_matches_app(s_global, "notepad.exe") is True
    assert snippet_matches_app(s_global, "chrome.exe") is True
    assert snippet_matches_app(s_global, None) is True


def test_snippet_matches_app_assigned_groups():
    grp_browsers = SnippetGroup(id="browsers", name="Browsers", matchers=["chrome.exe", "msedge.exe"])
    grp_code = SnippetGroup(id="code", name="Code Editors", matchers=["code.exe", "cursor.exe"])
    groups = [grp_browsers, grp_code]

    s_browser = Snippet(trigger=";b", replacement="Browser Snippet", groups=["browsers"])
    s_multi = Snippet(trigger=";m", replacement="Multi Snippet", groups=["browsers", "code"])

    # Browser snippet in Chrome -> matches
    assert snippet_matches_app(s_browser, "chrome.exe", groups=groups) is True
    # Browser snippet in Notepad -> does not match
    assert snippet_matches_app(s_browser, "notepad.exe", groups=groups) is False

    # Multi snippet in Code -> matches
    assert snippet_matches_app(s_multi, "code.exe", groups=groups) is True
    # Multi snippet in Chrome -> matches
    assert snippet_matches_app(s_multi, "chrome.exe", groups=groups) is True
    # Multi snippet in Word -> does not match
    assert snippet_matches_app(s_multi, "winword.exe", groups=groups) is False


def test_snippet_legacy_app_filter_preserved():
    s = Snippet(trigger=";log", replacement="console.log()", app_filter="code.exe,cursor.exe")
    assert snippet_matches_app(s, "code.exe") is True
    assert snippet_matches_app(s, "notepad.exe") is False


def test_resolve_image_snippet():
    is_img1, p1 = resolve_image_snippet("image:C:\\images\\logo.png")
    assert is_img1 is True
    assert p1 == "C:\\images\\logo.png"

    is_img2, p2 = resolve_image_snippet("C:\\images\\photo.png", is_image=True)
    assert is_img2 is True
    assert p2 == "C:\\images\\photo.png"

    is_img3, p3 = resolve_image_snippet("Just plain text")
    assert is_img3 is False
    assert p3 == ""


def test_validate_image_path():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. Non-existent file
        ok, err = validate_image_path(str(tmp_path / "missing.png"))
        assert ok is False
        assert "does not exist" in err

        # 2. Valid image file created via Pillow
        valid_img = tmp_path / "valid.png"
        img = Image.new("RGB", (32, 32), color="red")
        img.save(valid_img, format="PNG")

        ok2, err2 = validate_image_path(str(valid_img))
        assert ok2 is True
        assert err2 == ""

        # 3. Corrupted image file (text masquerading as png)
        corrupt_img = tmp_path / "corrupt.png"
        corrupt_img.write_text("not a real png header", encoding="utf-8")

        ok3, err3 = validate_image_path(str(corrupt_img))
        assert ok3 is False
        assert "Invalid image format" in err3


def test_engine_group_filtering_integration():
    grp_dev = SnippetGroup(id="dev", name="Dev", matchers=["code.exe", "class:ConsoleWindowClass"])
    snippets = [
        Snippet(trigger=";all", replacement="ALL_APPS"),
        Snippet(trigger=";dev", replacement="DEV_ONLY", groups=["dev"]),
    ]
    engine = SnippetEngine(snippets, groups=[grp_dev])

    # Global snippet works everywhere
    assert engine.expand(";all", app_name="notepad.exe") == "ALL_APPS"
    assert engine.expand(";all", app_name="code.exe") == "ALL_APPS"

    # Dev snippet only works in dev apps
    assert engine.expand(";dev", app_name="notepad.exe") is None
    assert engine.expand(";dev", app_name="code.exe") == "DEV_ONLY"
    assert engine.expand(";dev", app_name="cmd.exe", window_class="ConsoleWindowClass") == "DEV_ONLY"


def test_config_roundtrip_groups_and_snippets():
    grp = SnippetGroup(id="chat", name="Chat Apps", matchers=["telegram.exe", "discord.exe"], enabled=True)
    snip1 = Snippet(trigger=";hi", replacement="Hello!", groups=["chat"])
    snip2 = Snippet(trigger=";img", replacement="image:C:\\pic.png", is_image=True, groups=["chat"])

    cfg = Config()
    cfg.snippet_groups = [grp]
    cfg.snippets = [snip1, snip2]

    d = config_to_dict(cfg)
    cfg2 = config_from_dict(d)

    assert len(cfg2.snippet_groups) == 1
    assert cfg2.snippet_groups[0].id == "chat"
    assert cfg2.snippet_groups[0].matchers == ["telegram.exe", "discord.exe"]

    assert len(cfg2.snippets) == 2
    assert cfg2.snippets[0].trigger == ";hi"
    assert cfg2.snippets[0].groups == ["chat"]
    assert cfg2.snippets[1].is_image is True
    assert cfg2.snippets[1].groups == ["chat"]


def test_snippet_json_serialization_roundtrip():
    original = [
        Snippet(trigger=";test", replacement="Replacement", is_regex=False, groups=["g1", "g2"]),
        Snippet(trigger=";logo", replacement="image:C:\\logo.png", is_image=True, groups=[]),
    ]

    json_str = snippets_to_json(original)
    loaded = snippets_from_json(json_str)

    assert len(loaded) == 2
    assert loaded[0].trigger == ";test"
    assert loaded[0].groups == ["g1", "g2"]
    assert loaded[1].trigger == ";logo"
    assert loaded[1].is_image is True
    assert loaded[1].groups == []

"""Tests for Phase 6: Snippets 3.0: Forms, Images, Per-App, Regex (Target F)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from ravan.core.config import Snippet
from ravan.core.package import export_package, import_package
from ravan.core.snippet import (
    SnippetEngine,
    extract_form_fields,
    render_form_template,
    safe_regex_match,
)


def test_regex_snippet_capture_groups():
    snip = Snippet(trigger=r"re:;d(\d+)", replacement="Day $1 report")
    engine = SnippetEngine([snip])

    match = engine.find_matching_snippet(";d25")
    assert match is not None
    s, expanded = match
    assert expanded == "Day 25 report"

    res = engine.expand(";d25")
    assert res == "Day 25 report"


def test_regex_redos_guard():
    # Long text exceeding 100 chars should be dropped by ReDoS guard
    long_input = ";d" + "1" * 120
    m = safe_regex_match(r";d(\d+)", long_input, max_len=100)
    assert m is None

    # Normal input should match
    normal_input = ";d42"
    m2 = safe_regex_match(r";d(\d+)", normal_input, max_len=100)
    assert m2 is not None
    assert m2.group(1) == "42"


def test_form_fields_extraction_and_rendering():
    template = "سلام {{name:علی}}، جلسه در تاریخ {{date:YYYY/MM/DD}} نوع: {{choice:حضوری|آنلاین}} برگزار می‌شود."
    fields = extract_form_fields(template)

    assert len(fields) == 3
    assert fields[0].name == "name"
    assert fields[0].default == "علی"
    assert fields[0].field_type == "text"

    assert fields[1].field_type == "date"

    assert fields[2].field_type == "choice"
    assert fields[2].choices == ["حضوری", "آنلاین"]
    assert fields[2].default == "حضوری"

    # Test template rendering with user inputs
    user_vals = {
        "name": "رضا",
        "date_1": "1405/02/10",
        "choice_1": "آنلاین",
    }
    rendered = render_form_template(template, user_vals)
    assert "سلام رضا" in rendered
    assert "1405/02/10" in rendered
    assert "نوع: آنلاین" in rendered


def test_per_app_filtering():
    snip_code = Snippet(trigger="!log", replacement="console.log()", app_filter="code.exe,cursor.exe")
    snip_general = Snippet(trigger="!log", replacement="General Log")
    engine = SnippetEngine([snip_code, snip_general])

    # In VS Code: matches code-specific snippet
    res_code = engine.expand("!log", app_name="Code.exe")
    assert res_code == "console.log()"

    # Full path should resolve to basename
    res_full = engine.expand("!log", app_name="C:\\Program Files\\VSCode\\Code.exe")
    assert res_full == "console.log()"

    # In Notepad: code snippet filtered out, falls back to general
    res_notepad = engine.expand("!log", app_name="notepad.exe")
    assert res_notepad == "General Log"


def test_package_export_and_import():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pack_file = tmp_path / "test_bundle.ravaanpack"

        # Create dummy image
        img_file = tmp_path / "logo.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest_image_bytes")

        snippets = [
            Snippet(trigger=";hi", replacement="Hello world!"),
            Snippet(trigger=";img", replacement=str(img_file), is_image=True),
            Snippet(trigger=r"re:;t(\d+)", replacement="Ticket #$1", is_regex=True),
        ]

        # Export package
        payload = export_package(snippets, pack_file, title="Test Pack", author="Developer")
        assert pack_file.is_file()
        assert payload["snippet_count"] == 3

        # Import package into a new directory
        extract_dir = tmp_path / "extracted_images"
        imported = import_package(pack_file, image_dest_dir=extract_dir)

        assert len(imported) == 3
        assert imported[0].trigger == ";hi"
        assert imported[0].replacement == "Hello world!"
        assert imported[1].is_image is True
        img_p = imported[1].replacement.removeprefix("image:")
        assert Path(img_p).is_file()
        assert imported[2].is_regex is True


def test_cli_pack_command():
    from ravan.cli import main

    with tempfile.TemporaryDirectory() as tmp_dir:
        pack_path = Path(tmp_dir) / "cli_test.ravaanpack"

        # Test CLI export
        ret_export = main(["pack", "export", str(pack_path)])
        assert ret_export == 0
        assert pack_path.is_file()

        # Test CLI import
        ret_import = main(["pack", "import", str(pack_path)])
        assert ret_import == 0




@pytest.mark.parametrize(
    ("trigger", "replacement", "input_word", "expected"),
    [
        (r"re:;d(\d+)", "Day $1 report", ";d25", "Day 25 report"),
        (r"re:;u:([a-zA-Z]+)", "User: $1", ";u:mohsen", "User: mohsen"),
        (r"re:;date:(\d{4})-(\d{2})-(\d{2})", "$1/$2/$3", ";date:2026-10-21", "2026/10/21"),
        (r"re:([a-zA-Z0-9_.]+)@gm", "$1@gmail.com", "info@gm", "info@gmail.com"),
        (r"re:;price:(\d+)", "$$$1 USD", ";price:50", "$50 USD"),
        (r"re:;sh(\d+)", "شماره $1", ";sh104", "شماره 104"),
        (r"re:;calc:(\d+)\+(\d+)", "{{calc: $1 + $2}}", ";calc:10+20", "30"),
    ],
)
def test_regex_table_driven_cases(
    trigger: str, replacement: str, input_word: str, expected: str
) -> None:
    engine = SnippetEngine([Snippet(trigger=trigger, replacement=replacement)])
    res = engine.expand(input_word)
    assert res == expected


def test_regex_validation_safety_guards() -> None:
    from ravan.core.snippet_regex import validate_regex_trigger

    # 1. Valid patterns
    assert validate_regex_trigger(r"re:;d(\d+)")[0] is True
    assert validate_regex_trigger(r"re:^issue-\d+$")[0] is True

    # 2. Syntax errors
    ok, err = validate_regex_trigger(r"re:[a-z(")
    assert not ok
    assert "Invalid regex syntax" in err

    # 3. Empty patterns
    assert not validate_regex_trigger("re:")[0]
    assert not validate_regex_trigger("")[0]

    # 4. Matches empty string guard (must require at least 1 char)
    ok_empty, err_empty = validate_regex_trigger(r"re:a*")
    assert not ok_empty
    assert "cannot match empty strings" in err_empty

    ok_empty2, err_empty2 = validate_regex_trigger(r"re:^$")
    assert not ok_empty2
    assert "cannot match empty strings" in err_empty2

    # 5. Catastrophic backtracking guard (>1ms ReDoS guard)
    catastrophic_pat = r"re:(a+)+$"
    ok_cat, err_cat = validate_regex_trigger(catastrophic_pat, max_bench_ms=1.0)
    assert not ok_cat
    assert "Catastrophic backtracking detected" in err_cat


def test_regex_live_preview() -> None:
    from ravan.core.snippet_regex import preview_regex_expansion

    # Valid match
    ok, res = preview_regex_expansion(r"re:;t(\d+)", "Ticket #$1", ";t99")
    assert ok is True
    assert res == "Ticket #99"

    # Non-match
    ok, res = preview_regex_expansion(r"re:;t(\d+)", "Ticket #$1", ";other")
    assert ok is False
    assert res == "No match"

    # Invalid regex
    ok, res = preview_regex_expansion(r"re:[unclosed", "text", ";test")
    assert ok is False
    assert "Invalid regex" in res


def test_priority_chain_exact_vs_autofix_vs_translit_vs_regex() -> None:
    from unittest.mock import MagicMock, patch

    from ravan.core.config import Config, Snippet
    from ravan.ui.app import RavanApp

    cfg = Config()
    cfg.autofix_mode = "safe"
    cfg.translit_enabled = True
    cfg.snippets = [
        Snippet(trigger=";exact", replacement="EXACT_EXPANDED"),
        # Loose regex trigger that could match general English words if allowed first
        Snippet(trigger=r"re:([a-z]+)", replacement="REGEX_$1"),
    ]

    with patch("ravan.ui.app.KeyboardHook"):
        app = RavanApp(cfg, overlay=MagicMock())
        app._active_layout_tag = "en"
        replaced: list[tuple[str, str]] = []
        app._replace_word = lambda old, new, **kwargs: replaced.append((old, new))

        # 1. Exact snippet takes priority over everything
        replaced.clear()
        handled = app._on_word_completed(";exact", delimiter=" ")
        assert handled is True
        assert replaced == [(";exact", "EXACT_EXPANDED")]

        # 2. Autofix priority over regex:
        # "sghl" is Persian "سلام" typed on English keyboard layout.
        # Autofix MUST claim "sghl" -> "سلام", rather than the loose regex matching it!
        replaced.clear()
        handled = app._on_word_completed("sghl", delimiter=" ")
        assert handled is True
        assert len(replaced) == 1
        assert replaced[0][0] == "sghl"
        assert replaced[0][1] == "سلام"

        # 3. Regex trigger fires when neither exact snippet nor autofix/translit handled it
        replaced.clear()
        handled = app._on_word_completed("custompattern", delimiter=" ")
        assert handled is True
        assert replaced == [("custompattern", "REGEX_custompattern")]


def test_regex_trigger_does_not_interfere_with_zwnj() -> None:
    from unittest.mock import MagicMock, patch

    from ravan.core.config import Config, Snippet
    from ravan.core.zwnj import ZWNJ
    from ravan.ui.app import RavanApp

    cfg = Config()
    cfg.auto_zwnj_enabled = True
    cfg.snippets = [
        Snippet(trigger=r"re:;sh(\d+)", replacement="شماره $1"),
    ]

    with patch("ravan.ui.app.KeyboardHook"):
        app = RavanApp(cfg, overlay=MagicMock())
        replaced: list[tuple[str, str]] = []
        app._replace_word = lambda old, new, **kwargs: replaced.append((old, new))

        # Expanding regex snippet does not inject unwanted ZWNJ or corrupt text
        handled = app._on_word_completed(";sh55", delimiter=" ")
        assert handled is True
        assert replaced == [(";sh55", "شماره 55")]
        assert ZWNJ not in replaced[0][1]


def test_regex_multi_group_capture_order() -> None:
    # Verify that $10 is not partially replaced by $1
    pattern = r"re:" + "".join(";(\\w)" for _ in range(10))
    replacement = "Group 10 is $10 and Group 1 is $1"
    snip = Snippet(trigger=pattern, replacement=replacement)
    engine = SnippetEngine([snip])

    input_text = ";a;b;c;d;e;f;g;h;i;j"
    expanded = engine.expand(input_text)
    assert expanded == "Group 10 is j and Group 1 is a"

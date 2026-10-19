"""Tests for Phase 6: Snippets 3.0: Forms, Images, Per-App, Regex (Target F)."""

from __future__ import annotations

import tempfile
from pathlib import Path

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
        assert Path(imported[1].replacement).is_file()
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

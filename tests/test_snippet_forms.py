"""Unit tests for Snippets 3.0 Interactive Forms (parser, remember cache, headless controller)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from ravan.core.snippet_forms import (
    FormController,
    clear_remembered_values,
    get_remembered_value,
    parse_form_fields,
    render_form_template_with_specs,
    save_remembered_value,
)


def test_parse_form_fields_basic_and_defaults():
    template = "Hello {{name=Mohsen}}, your project {{project:Ravaan}} is ready."
    fields = parse_form_fields(template)

    assert len(fields) == 2
    assert fields[0].name == "name"
    assert fields[0].label == "Name"
    assert fields[0].default == "Mohsen"
    assert fields[0].field_type == "text"
    assert fields[0].remember is False

    assert fields[1].name == "project"
    assert fields[1].default == "Ravaan"
    assert fields[1].field_type == "text"


def test_parse_form_fields_multiline_and_remember():
    template = "Bug report for {{app:remember=Ravaan}}:\n{{description:multiline=Steps to reproduce}}"
    fields = parse_form_fields(template)

    assert len(fields) == 2
    assert fields[0].name == "app"
    assert fields[0].remember is True
    assert fields[0].default == "Ravaan"
    assert fields[0].field_type == "text"

    assert fields[1].name == "description"
    assert fields[1].field_type == "multiline"
    assert fields[1].default == "Steps to reproduce"
    assert fields[1].remember is False


def test_parse_form_fields_choice_and_date():
    template = "Meeting with {{client}} on {{date:YYYY/MM/DD}}, type: {{format:choice:Online|In-Person}}"
    fields = parse_form_fields(template)

    assert len(fields) == 3
    assert fields[0].name == "client"
    assert fields[0].field_type == "text"

    # Date field
    assert fields[1].name == "date"
    assert fields[1].field_type == "date"
    assert len(fields[1].default) > 0  # Today's Jalali date

    # Choice field
    assert fields[2].name == "format"
    assert fields[2].field_type == "choice"
    assert fields[2].choices == ["Online", "In-Person"]
    assert fields[2].default == "Online"


def test_parse_form_fields_dynamic_macro_defaults():
    with patch("ravan.core.snippet._fetch_clipboard", return_value="https://github.com"):
        template = "Link: {{url={{clipboard}}}}, Generated: {{gen={{shamsi}}}}"
        fields = parse_form_fields(template)

        assert len(fields) == 2
        assert fields[0].name == "url"
        assert fields[0].default == "https://github.com"
        assert fields[1].name == "gen"
        assert len(fields[1].default) >= 8  # e.g. 1405/01/01


def test_parse_form_fields_deduplication():
    template = "Dear {{name}}, this note is for {{name}} regarding {{topic}}."
    fields = parse_form_fields(template)

    assert len(fields) == 2
    assert fields[0].name == "name"
    assert fields[1].name == "topic"

    rendered = render_form_template_with_specs(
        template, {"name": "Sara", "topic": "Release"}, fields
    )
    assert rendered == "Dear Sara, this note is for Sara regarding Release."


def test_remember_cache_lifecycle(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        fake_cache = Path(tmp_dir) / "test_remember.json"
        monkeypatch.setattr("ravan.core.snippet_forms.get_remember_cache_path", lambda: fake_cache)

        clear_remembered_values()
        assert get_remembered_value(";bug", "assignee") is None

        # Save remembered value
        save_remembered_value(";bug", "assignee", "Ali")
        assert get_remembered_value(";bug", "assignee") == "Ali"
        assert fake_cache.is_file()

        # Parse template with remember opt-in: should auto-populate from remember cache!
        template = "Assignee: {{assignee:remember=DefaultUser}}"
        fields = parse_form_fields(template, snippet_trigger=";bug")
        assert fields[0].default == "Ali"

        # Different snippet trigger: uses static default
        fields_other = parse_form_fields(template, snippet_trigger=";feature")
        assert fields_other[0].default == "DefaultUser"


def test_headless_form_controller_validation_and_confirm():
    template = "Invoice for {{client:remember}}: Amount: {{amount}}"
    controller = FormController(template, snippet_trigger=";inv")

    assert len(controller.fields) == 2
    # Initially client has empty default, amount has empty default
    # Validation should fail because required fields are empty
    valid = controller.validate()
    assert valid is False
    assert "client" in controller.errors or "amount" in controller.errors

    ok, err = controller.confirm()
    assert ok is False
    assert "cannot be empty" in err

    # Provide valid values
    controller.set_value("client", "Acme Corp")
    controller.set_value("amount", "500000")

    assert controller.validate() is True
    ok, rendered = controller.confirm()
    assert ok is True
    assert rendered == "Invoice for Acme Corp: Amount: 500000"

    # Verify remember cache was updated
    assert get_remembered_value(";inv", "client") == "Acme Corp"


def test_headless_form_controller_multiline_support():
    template = "Header\n{{body:multiline}}\nFooter"
    controller = FormController(template, snippet_trigger=";ml")

    controller.set_value("body", "Line 1\nLine 2\nLine 3")
    ok, rendered = controller.confirm()

    assert ok is True
    assert rendered == "Header\nLine 1\nLine 2\nLine 3\nFooter"


def test_form_dialog_focus_restoration_and_cancel():
    from ravan.ui.form_dialog import QuickFormDialog

    template = "Message: {{msg}}"
    submitted = []

    dialog = QuickFormDialog(
        parent=None,
        template=template,
        on_submit=lambda text: submitted.append(text),
    )

    # Mock user32 foreground window
    with patch("ravan.platform.winapi.user32.GetForegroundWindow", return_value=0x12345), \
         patch("ravan.platform.winapi.user32.SetForegroundWindow") as mock_set_fg:

        dialog._target_hwnd = 0x12345

        # Test Cancel: closes without submitting, restores focus
        dialog._cancel()
        assert len(submitted) == 0
        mock_set_fg.assert_called_with(0x12345)


def test_multiple_choices_and_dates_preserved_in_order() -> None:
    template = "Mode: {{choice:A|B}} vs {{choice:C|D}}, from {{date:YYYY/MM/DD}} to {{date:YYYY/MM/DD}}"
    fields = parse_form_fields(template)

    assert len(fields) == 4
    assert fields[0].name == "choice"
    assert fields[0].choices == ["A", "B"]
    assert fields[1].name == "choice_2"
    assert fields[1].choices == ["C", "D"]
    assert fields[2].name == "date"
    assert fields[3].name == "date_2"

    values = {
        "choice": "B",
        "choice_2": "C",
        "date": "1405/01/01",
        "date_2": "1405/12/29",
    }
    rendered = render_form_template_with_specs(template, values, fields)
    assert rendered == "Mode: B vs C, from 1405/01/01 to 1405/12/29"

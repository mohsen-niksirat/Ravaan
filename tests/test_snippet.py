import json
from ravan.core.config import Config, Snippet
from ravan.core.jalali import JalaliDate
from ravan.core.snippet import (
    SnippetEngine,
    get_macro_values,
    parse_cursor_placeholder,
    render_template,
    snippets_from_json,
    snippets_to_json,
)


def test_snippet_expansion():
    cfg = Config()
    cfg.snippets.append(Snippet(trigger="@@", replacement="user@example.com"))
    engine = SnippetEngine.from_config(cfg)
    assert engine.expand("@@") == "user@example.com"
    assert engine.expand("@") is None


def test_default_macro_triggers():
    engine = SnippetEngine([])
    today_fa = JalaliDate.today().isoformat_fa()
    assert engine.expand("/today") == today_fa
    assert engine.expand("/shamsi") == today_fa
    assert engine.expand("/امروز") == today_fa

    persian_text = JalaliDate.today().format_persian(include_weekday=False)
    assert engine.expand("/tarikh") == persian_text
    assert engine.expand("/تاریخ") == persian_text

    assert engine.expand("/date") is not None
    assert "-" in engine.expand("/date")

    time_str = engine.expand("/time")
    assert time_str is not None
    assert ":" in time_str

    uuid_str = engine.expand("/uuid")
    assert uuid_str is not None
    assert len(uuid_str) == 36


def test_template_rendering_in_snippets():
    cfg = Config()
    cfg.snippets.append(Snippet(trigger="now", replacement="Time: {{time}}"))
    cfg.snippets.append(Snippet(trigger="sig", replacement="Date: {{shamsi}}"))
    engine = SnippetEngine.from_config(cfg)

    res_now = engine.expand("now")
    assert res_now is not None
    assert "Time: " in res_now
    assert ":" in res_now

    res_sig = engine.expand("sig")
    assert res_sig is not None
    assert "Date: " in res_sig
    assert "/" in res_sig


def test_user_override_macro():
    cfg = Config()
    cfg.snippets.append(Snippet(trigger="/today", replacement="CUSTOM_TODAY"))
    engine = SnippetEngine.from_config(cfg)
    assert engine.expand("/today") == "CUSTOM_TODAY"


def test_multiline_snippet():
    cfg = Config()
    cfg.snippets.append(
        Snippet(
            trigger="hw",
            replacement="Hello World!\nLine 2 of snippet\nLine 3 of snippet",
        )
    )
    engine = SnippetEngine.from_config(cfg)
    res = engine.expand("hw")
    assert res is not None
    lines = res.splitlines()
    assert len(lines) == 3
    assert lines[0] == "Hello World!"
    assert lines[2] == "Line 3 of snippet"


def test_cursor_placeholder_parsing():
    # Test $0
    clean, offset = parse_cursor_placeholder("console.log($0);")
    assert clean == "console.log();"
    assert offset == 2  # ');' is 2 characters

    # Test {{cursor}}
    clean2, offset2 = parse_cursor_placeholder("def {{cursor}}():\n    pass")
    assert clean2 == "def ():\n    pass"
    assert offset2 == len(clean2) - 4

    # Test without placeholder
    clean3, offset3 = parse_cursor_placeholder("simple text")
    assert clean3 == "simple text"
    assert offset3 is None


def test_expand_with_cursor():
    cfg = Config()
    cfg.snippets.append(Snippet(trigger="fn", replacement="def $0():\n    return"))
    engine = SnippetEngine.from_config(cfg)

    # expand_with_cursor returns (clean_text, offset)
    res = engine.expand_with_cursor("fn")
    assert res is not None
    text, offset = res
    assert "$0" not in text
    assert text == "def ():\n    return"
    assert offset == len("():\n    return")

    # Regular expand() strips $0 transparently
    assert engine.expand("fn") == "def ():\n    return"


def test_extended_date_placeholders():
    vals = get_macro_values()
    assert "year" in vals
    assert "month" in vals
    assert "day" in vals
    assert "weekday" in vals
    assert "yesterday" in vals
    assert "tomorrow" in vals
    assert "gregorian" in vals
    assert "timestamp" in vals

    # Test template rendering
    rendered = render_template("Year: {{year}}, Month: {{month}}, Day: {{day}}")
    assert "Year: " in rendered
    assert "Month: " in rendered
    assert "{{" not in rendered


def test_math_placeholders_in_templates():
    # Basic math
    res1 = render_template("Total: {{calc: 100 * 1.09}} Tomans")
    assert res1 == "Total: 109 Tomans"

    # Parentheses and complex arithmetic
    res2 = render_template("Result: {{math: (50 + 30) * 2}}")
    assert res2 == "Result: 160"

    # Persian digits arithmetic
    res3 = render_template("پاسخ: {{calc: ۱۲ * ۵}}")
    assert res3 == "پاسخ: ۶۰"

    # Invalid math is left safely intact
    res4 = render_template("Unknown: {{calc: abc + 123}}")
    assert res4 == "Unknown: {{calc: abc + 123}}"


def test_snippets_json_import_export():
    original = [
        Snippet(trigger="@@", replacement="me@test.com"),
        Snippet(trigger="fn", replacement="def $0():\n    pass"),
        Snippet(trigger="fa", replacement="متن فارسی چند\nخطی با تاریخ {{shamsi}}"),
    ]
    json_str = snippets_to_json(original)
    assert isinstance(json_str, str)
    assert "@@" in json_str
    assert "متن فارسی" in json_str

    imported = snippets_from_json(json_str)
    assert len(imported) == 3
    assert imported[0].trigger == "@@"
    assert imported[0].replacement == "me@test.com"
    assert imported[1].trigger == "fn"
    assert "\n" in imported[1].replacement
    assert imported[2].trigger == "fa"
    assert "متن فارسی" in imported[2].replacement


def test_snippet_excluded_in_app():
    from ravan.ui.app import RavanApp

    class MockOverlay:
        def hide(self):
            pass
        def is_open(self):
            return False

    cfg = Config()
    cfg.excluded_apps = ["secret.exe", "keepass.exe"]
    cfg.snippets.append(Snippet(trigger="@@", replacement="me@test.com"))
    app = RavanApp(cfg, overlay=MockOverlay())

    # In active app: should expand
    app._current_exe = "notepad.exe"
    handled = app._on_word_completed("@@", delimiter=" ")
    assert handled is True

    # In excluded app: must NOT expand
    app._current_exe = "keepass.exe"
    handled_excluded = app._on_word_completed("@@", delimiter=" ")
    assert handled_excluded is False

from ravan.core.config import Config, Snippet
from ravan.core.jalali import JalaliDate
from ravan.core.snippet import SnippetEngine, render_template


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

from ravan.core.config import Snippet, text_to_hotkey, hotkey_to_text


def test_hotkey_roundtrip():
    spec = text_to_hotkey("Ctrl+Shift+C")
    assert spec is not None
    assert spec.key.lower() == "c"
    assert [m.lower() for m in spec.modifiers] == ["ctrl", "shift"]
    text = hotkey_to_text(spec)
    assert text.lower() == "ctrl+shift+c"


def test_hotkey_invalid():
    assert text_to_hotkey("") is None
    assert text_to_hotkey("Bogus+X") is None


def test_snippet_expansion():
    cfg_snip = Snippet(trigger="@@", replacement="user@example.com")
    assert cfg_snip.trigger == "@@"

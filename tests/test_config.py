from ravan.core.config import Snippet, hotkey_to_text, text_to_hotkey


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


def test_is_app_excluded():
    from ravan.core.config import Config, is_app_excluded

    excls = ["explorer.exe", "cmd.exe", "vmware.exe"]
    assert is_app_excluded("explorer.exe", excls) is True
    assert is_app_excluded("Explorer.EXE", excls) is True
    assert is_app_excluded(r"C:\Windows\System32\cmd.exe", excls) is True
    assert is_app_excluded("notepad.exe", excls) is False
    assert is_app_excluded(None, excls) is False
    assert is_app_excluded("", excls) is False

    cfg = Config(excluded_apps=["slack.exe", "teams.exe"])
    assert cfg.is_excluded("slack.exe") is True
    assert cfg.is_excluded("SLACK.EXE") is True
    assert cfg.is_excluded("code.exe") is False


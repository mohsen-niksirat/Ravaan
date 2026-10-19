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
    from ravan.core.snippet import SnippetEngine

    cfg_snip = Snippet(trigger="@@", replacement="user@example.com")
    engine = SnippetEngine([cfg_snip])
    assert engine.expand("@@") == "user@example.com"



def test_is_app_excluded():
    from ravan.core.config import Config, is_app_excluded

    excls = ["explorer.exe", "cmd.exe", "vmware.exe"]
    assert is_app_excluded("explorer.exe", excls) is True
    assert is_app_excluded("Explorer.EXE", excls) is True
    assert is_app_excluded(r"C:\Windows\System32\cmd.exe", excls) is True
    assert is_app_excluded("notepad.exe", excls) is False
    assert is_app_excluded(None, excls) is False
    assert is_app_excluded("", excls) is False

    cfg = Config(excluded_apps=["slack.exe", "teams.exe", "class:custom_wnd"])
    assert cfg.is_excluded("slack.exe") is True
    assert cfg.is_excluded("SLACK.EXE") is True
    assert cfg.is_excluded("code.exe") is False
    assert cfg.is_excluded("other.exe", window_class="custom_wnd") is True
    assert cfg.is_excluded("other.exe", window_class="different_wnd") is False
    assert is_app_excluded("other.exe", ["class:my_window_class"], window_class="My_Window_Class") is True


def test_ignored_words_config():
    from ravan.core.config import Config

    cfg = Config(ignored_words=["Foo", "BAR"])
    assert cfg.is_word_ignored("foo") is True
    assert cfg.is_word_ignored("Bar") is True
    assert cfg.is_word_ignored("baz") is False
    assert cfg.is_word_ignored("") is False


def test_cli_ignore_command(tmp_path):
    from unittest.mock import patch

    from ravan.cli import main
    from ravan.core.config import Config

    cfg_file = tmp_path / "config.json"
    fake_cfg = Config(ignored_words=["preexisting"])

    with patch("ravan.core.config.config_path", return_value=cfg_file):
        with patch("ravan.core.config.load_config", return_value=fake_cfg):
            with patch("ravan.core.config.save_config") as mock_save:
                # Add word
                res = main(["ignore", "add", "myword"])
                assert res == 0
                assert "myword" in fake_cfg.ignored_words
                mock_save.assert_called()

                # Add already existing word
                res = main(["ignore", "add", "myword"])
                assert res == 0

                # List words
                res = main(["ignore", "list"])
                assert res == 0

                # Remove word
                res = main(["ignore", "remove", "myword"])
                assert res == 0
                assert "myword" not in fake_cfg.ignored_words

                # Remove non-existent word
                res = main(["ignore", "remove", "nonexistent"])
                assert res == 1


def test_legacy_appdata_migration(tmp_path):
    from ravan.core.config import migrate_legacy_appdata

    legacy_dir = tmp_path / "Ravan"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    (legacy_dir / "config.json").write_text('{"test": true}', encoding="utf-8")
    (legacy_dir / "user_words.txt").write_text("سلام\nروان\n", encoding="utf-8")

    sub_dir = legacy_dir / "snippets"
    sub_dir.mkdir()
    (sub_dir / "custom.txt").write_text("hello", encoding="utf-8")

    # Run migration
    migrated = migrate_legacy_appdata(tmp_path)
    assert migrated is True

    canonical_dir = tmp_path / "Ravaan"
    assert canonical_dir.is_dir()
    assert (canonical_dir / "config.json").read_text(encoding="utf-8") == '{"test": true}'
    assert (canonical_dir / "user_words.txt").read_text(encoding="utf-8") == "سلام\nروان\n"
    assert (canonical_dir / "snippets" / "custom.txt").read_text(encoding="utf-8") == "hello"

    # Migration marker exists in legacy
    assert (legacy_dir / "MIGRATED_TO_RAVAAN.txt").is_file()

    # Second run does not re-migrate existing files
    assert migrate_legacy_appdata(tmp_path) is False


def test_default_hotkeys_and_pause_vk():
    from ravan.core.config import Config
    from ravan.platform import winapi as w
    from ravan.platform.keys import key_name_to_vk

    cfg = Config()
    assert cfg.convert_hotkey.key == "Pause"
    assert cfg.convert_hotkey.modifiers == []
    assert cfg.quick_stats_hotkey.key == "S"
    assert cfg.quick_stats_hotkey.modifiers == ["Ctrl", "Alt"]

    # Pause and break map to VK_PAUSE
    assert key_name_to_vk("pause") == w.VK_PAUSE
    assert key_name_to_vk("break") == w.VK_PAUSE
    assert key_name_to_vk("PAUSE") == w.VK_PAUSE

    # Roundtrip with text
    spec = text_to_hotkey("Pause")
    assert spec is not None
    assert spec.key == "Pause"
    assert hotkey_to_text(spec) == "Pause"


def test_settings_save_duplicate_hotkey_prevention():
    from unittest.mock import patch

    from ravan.core.config import Config
    from ravan.ui.settings_save import save_settings_window

    class FakeVar:
        def __init__(self, val=""):
            self._val = val

        def get(self):
            return self._val

    class DummyWin:
        def __init__(self):
            self.cfg = Config()
            self._root = None
            self.on_saved = None
            # Set duplicate hotkeys: convert and clipboard both Pause
            self._convert_var = FakeVar("Pause")
            self._lang_var = FakeVar("Alt+L")
            self._clip_var = FakeVar("Pause")  # duplicate!
            self._norm_var = FakeVar("Ctrl+F12")
            self._case_var = FakeVar("Shift+F12")
            self._undo_var = FakeVar("Ctrl+Shift+Z")
            self._stats_var = FakeVar("Ctrl+Alt+S")

    win = DummyWin()
    with patch("tkinter.messagebox.showwarning") as mock_warn:
        save_settings_window(win)
        mock_warn.assert_called_once()
        assert "Duplicate hotkeys" in mock_warn.call_args[0][1]




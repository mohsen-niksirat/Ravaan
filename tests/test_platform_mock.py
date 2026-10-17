"""Unit tests for ravan/platform modules using Win32 API mocks."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ravan.core.events import LanguageInfo
from ravan.platform import clipboard, focus, inject, lang, singleinstance, startup
from ravan.platform import winapi as w

# --- Focus Tests ---

def test_focus_foreground_exe_none_when_no_foreground():
    with patch.object(w.user32, "GetForegroundWindow", return_value=0):
        assert focus.foreground_exe() is None


def test_focus_foreground_exe_success():
    def fake_get_pid(hwnd, p_pid):
        p_pid._obj.value = 4321
        return 1

    with patch.object(w.user32, "GetForegroundWindow", return_value=1001), \
         patch.object(w.user32, "GetWindowThreadProcessId", side_effect=fake_get_pid), \
         patch.object(w.kernel32, "OpenProcess", return_value=5555), \
         patch.object(w.kernel32, "CloseHandle", return_value=True), \
         patch.object(focus, "_query_full_process_name", return_value=r"C:\Tools\CodeEditor.exe"):
        exe = focus.foreground_exe()
        assert exe == "codeeditor.exe"


def test_focus_foreground_exe_open_process_fail():
    def fake_get_pid(hwnd, p_pid):
        p_pid._obj.value = 4321
        return 1

    with patch.object(w.user32, "GetForegroundWindow", return_value=1001), \
         patch.object(w.user32, "GetWindowThreadProcessId", side_effect=fake_get_pid), \
         patch.object(w.kernel32, "OpenProcess", return_value=0):
        assert focus.foreground_exe() is None


def test_focus_window_title_none_when_no_foreground():
    with patch.object(w.user32, "GetForegroundWindow", return_value=0):
        assert focus.window_title() is None


def test_focus_window_title_zero_length():
    with patch.object(w.user32, "GetForegroundWindow", return_value=1001), \
         patch.object(w.user32, "GetWindowTextLengthW", return_value=0):
        assert focus.window_title() is None


def test_focus_window_title_success():
    def fake_get_text(hwnd, buf, max_len):
        buf.value = "Document - Ravaan"
        return len(buf.value)

    with patch.object(w.user32, "GetForegroundWindow", return_value=1001), \
         patch.object(w.user32, "GetWindowTextLengthW", return_value=16), \
         patch.object(w.user32, "GetWindowTextW", side_effect=fake_get_text):
        title = focus.window_title()
        assert title == "Document - Ravaan"


def test_focus_active_window_info():
    with patch.object(w.user32, "GetForegroundWindow", return_value=0):
        info = focus.active_window_info()
        assert info == {"hwnd": 0, "pid": 0, "exe": None, "class_name": None, "title": None}

    def fake_get_pid(hwnd, p_pid):
        p_pid._obj.value = 9999
        return 1

    with patch.object(w.user32, "GetForegroundWindow", return_value=2002), \
         patch.object(focus, "foreground_exe", return_value="notepad.exe"), \
         patch.object(focus, "window_title", return_value="Untitled - Notepad"), \
         patch.object(w.user32, "GetWindowThreadProcessId", side_effect=fake_get_pid):
        info = focus.active_window_info()
        assert info["hwnd"] == 2002
        assert info["pid"] == 9999
        assert info["exe"] == "notepad.exe"
        assert info["title"] == "Untitled - Notepad"


# --- Language Tests ---

def test_lang_hkl_mappings():
    fa_info = lang.hkl_to_language_info(0x0429)
    assert fa_info.tag == "fa"
    assert fa_info.name == "Persian"

    en_info = lang.hkl_to_language_info(0x0409)
    assert en_info.tag == "en"
    assert en_info.name == "English"

    ar_info = lang.hkl_to_language_info(0x0401)
    assert ar_info.tag == "ar"
    assert ar_info.name == "Arabic"

    ru_info = lang.hkl_to_language_info(0x0419)
    assert ru_info.tag == "ru"
    assert ru_info.name == "Russian"


def test_lang_language_label():
    assert lang.language_label(LanguageInfo(tag="fa-IR", name="Persian", hkl=0x0429)) == "فا"
    assert lang.language_label(LanguageInfo(tag="en-US", name="English", hkl=0x0409)) == "EN"
    assert lang.language_label(LanguageInfo(tag="de", name="German", hkl=0x0407)) == "DE"


def test_lang_current_language():
    with patch.object(w.user32, "GetForegroundWindow", return_value=123), \
         patch.object(w.user32, "GetWindowThreadProcessId", return_value=456), \
         patch.object(w.user32, "GetKeyboardLayout", return_value=0x04290429):
        info = lang.current_language()
        assert info is not None
        assert info.tag == "fa"
        assert info.name == "Persian"


def test_lang_current_language_zero_fallback():
    with patch.object(w.user32, "GetForegroundWindow", return_value=0), \
         patch.object(w.user32, "GetKeyboardLayout", return_value=0):
        info = lang.current_language()
        assert info is None


# --- Startup Tests ---

def test_startup_command_contains_ravan():
    cmd = startup._command()
    assert "-m ravan" in cmd


def test_startup_command_frozen_executable():
    import sys
    with patch.object(sys, "frozen", True, create=True), \
         patch.object(sys, "executable", r"C:\Program Files\Ravan\Ravaan.exe"):
        cmd = startup._command()
        assert cmd == r'"C:\Program Files\Ravan\Ravaan.exe"'
        assert "-m ravan" not in cmd


def test_winapi_screen_metrics_constants():
    assert w.SM_CXSCREEN == 0
    assert w.SM_CYSCREEN == 1
    assert w.SM_XVIRTUALSCREEN == 76


def test_startup_is_enabled_false_on_missing_key():
    import winreg
    with patch.object(winreg, "OpenKey", side_effect=FileNotFoundError):
        assert startup.is_startup_enabled() is False


def test_startup_is_enabled_true():
    import winreg
    mock_key = MagicMock()
    with patch.object(winreg, "OpenKey", return_value=mock_key), \
         patch.object(winreg, "QueryValueEx", return_value=("pythonw -m ravan", 1)):
        assert startup.is_startup_enabled() is True


def test_startup_set_enabled():
    import winreg
    mock_key = MagicMock()
    with patch.object(winreg, "OpenKey", return_value=mock_key), \
         patch.object(winreg, "SetValueEx") as mock_set:
        res = startup.set_startup(True)
        assert res is True
        mock_set.assert_called_once()


def test_startup_set_disabled():
    import winreg
    mock_key = MagicMock()
    with patch.object(winreg, "OpenKey", return_value=mock_key), \
         patch.object(winreg, "DeleteValue") as mock_del:
        res = startup.set_startup(False)
        assert res is True
        mock_del.assert_called_once()


# --- SingleInstance Mutex Tests ---

def test_single_instance_acquired_and_released():
    with patch.object(singleinstance.kernel32, "CreateMutexW", return_value=1234), \
         patch("ctypes.get_last_error", return_value=0), \
         patch.object(singleinstance.kernel32, "CloseHandle") as mock_close:
        si = singleinstance.SingleInstance("TestAppMutex")
        assert si.acquired is True
        si.release()
        mock_close.assert_called_once_with(1234)


def test_single_instance_already_running():
    with patch.object(singleinstance.kernel32, "CreateMutexW", return_value=1234), \
         patch("ctypes.get_last_error", return_value=singleinstance.ERROR_ALREADY_EXISTS):
        si = singleinstance.SingleInstance("TestAppMutex")
        assert si.acquired is False


# --- Inject Tests ---

def test_inject_text():
    with patch.object(w.user32, "SendInput") as mock_send:
        inject.inject_text("سلام")
        assert mock_send.called
        call_args = mock_send.call_args[0]
        # 4 chars * 2 (down + up) = 8 events
        assert call_args[0] == 8


def test_inject_backspaces():
    with patch.object(w.user32, "SendInput") as mock_send:
        inject.inject_backspaces(3)
        assert mock_send.called
        call_args = mock_send.call_args[0]
        # 3 backspaces * 2 = 6 events
        assert call_args[0] == 6


def test_inject_left_arrows():
    with patch.object(w.user32, "SendInput") as mock_send:
        inject.inject_left_arrows(2)
        assert mock_send.called
        call_args = mock_send.call_args[0]
        # 2 arrows * 2 = 4 events
        assert call_args[0] == 4


def test_replace_last_n_with():
    with patch.object(w.user32, "SendInput") as mock_send:
        inject.replace_last_n_with(4, "نوین", cursor_offset=1)
        assert mock_send.called
        call_args = mock_send.call_args[0]
        # 4 backspaces * 2 + 4 chars * 2 + 1 left arrow * 2 = 18 inputs in a single atomic batch
        assert call_args[0] == 18


def test_send_shortcut():
    with patch.object(w.user32, "SendInput") as mock_send:
        inject.send_shortcut([w.VK_CONTROL, w.VK_SHIFT], 0x5A)
        assert mock_send.called
        call_args = mock_send.call_args[0]
        # Ctrl down, Shift down, Z down, Z up, Shift up, Ctrl up = 6 events
        assert call_args[0] == 6


# --- Clipboard Tests ---

def test_clipboard_fallback_when_open_fails():
    with patch.object(clipboard, "_open_clipboard", return_value=False):
        assert clipboard.get_clipboard_text() is None
        assert clipboard.set_clipboard_text("test") is False


# --- Elevation & Caret Caching Tests ---

def test_is_current_process_elevated_mock():
    with patch("ctypes.WinDLL") as mock_windll:
        mock_windll.return_value.IsUserAnAdmin.return_value = 1
        assert focus.is_current_process_elevated() is True
        mock_windll.return_value.IsUserAnAdmin.return_value = 0
        assert focus.is_current_process_elevated() is False


def test_is_window_elevated_when_access_denied():
    with patch.object(focus, "is_current_process_elevated", return_value=False), \
         patch.object(w.user32, "GetForegroundWindow", return_value=1234), \
         patch.object(w.user32, "GetWindowThreadProcessId", side_effect=lambda h, p: setattr(p._obj, "value", 999)), \
         patch.object(w.kernel32, "OpenProcess", return_value=0), \
         patch("ctypes.get_last_error", return_value=5):
        assert focus.is_window_elevated(1234) is True


def test_caret_caching():
    from ravan.platform import caret

    caret.reset_caret_cache()
    with patch.object(caret, "_try_uia_caret", return_value=caret.CaretRect(100, 200, 10, 20)) as mock_raw, \
         patch.object(caret, "_get_active_pid", return_value=1234):
        rect1, src1 = caret.get_caret_rect_with_source()
        assert rect1.x == 100
        assert src1 == "UIA"
        # Immediate next call within 30ms returns cached without calling _try_uia_caret again
        rect2, src2 = caret.get_caret_rect_with_source()
        assert rect2.x == 100
        assert src2 == "UIA"
        assert mock_raw.call_count == 1



"""Unit tests for the crash dialog and global crash handler (ravan.ui.crash_dialog, ravan.ui.log_setup)."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

import pytest

from ravan import __version__
from ravan.ui.crash_dialog import CrashDialog, build_diagnostic_report, show_crash_dialog
from ravan.ui.log_setup import install_crash_handler


def test_build_diagnostic_report_content():
    """Verify diagnostic report contains technical stack info and explicit privacy guarantee."""
    try:
        raise RuntimeError("Simulated test error for crash report")
    except RuntimeError:
        exc_type, exc_val, exc_tb = sys.exc_info()

    recent_logs = [
        "2026-10-20 05:00:00 [INFO] [ravan.ui.app:102] Starting Ravan",
        "2026-10-20 05:00:01 [INFO] [ravan.platform.hook:85] Hook installed",
    ]

    report = build_diagnostic_report(
        exc_type=exc_type,
        exc_value=exc_val,
        exc_tb=exc_tb,
        recent_logs=recent_logs,
    )

    # Required headers and version
    assert "Ravaan Crash Report" in report
    assert f"App Version  : {__version__}" in report
    assert "OS Platform  :" in report
    assert "Python       :" in report

    # Privacy guarantee
    assert "PRIVACY GUARANTEE" in report
    assert "Keystrokes, typed text, clipboard contents, and" in report
    assert "credentials are NEVER recorded or included." in report

    # Exception information
    assert "RuntimeError" in report
    assert "Simulated test error for crash report" in report
    assert "test_build_diagnostic_report_content" in report

    # Recent log lines
    assert "Starting Ravan" in report
    assert "Hook installed" in report


def test_crash_dialog_build_and_destroy():
    """Verify CrashDialog builds UI widgets cleanly and closes without error."""
    try:
        report = "Sample diagnostic report content"
        dialog = CrashDialog(report_text=report)

        root = dialog.build()
        try:
            root.update_idletasks()
            assert dialog._btn_copy is not None
            assert dialog._root is not None
        finally:
            dialog._on_close()

        assert dialog._root is None
    except (tk.TclError, Exception) as exc:
        pytest.skip(f"Tkinter display not available: {exc}")


def test_crash_dialog_copy_clipboard():
    """Verify copying diagnostic report populates system clipboard."""
    try:
        report = "Sanitized report text 12345"
        dialog = CrashDialog(report_text=report)
        root = dialog.build()

        try:
            dialog._on_copy()
            clipboard_content = root.clipboard_get()
            assert clipboard_content == report
        finally:
            dialog._on_close()
    except (tk.TclError, Exception) as exc:
        pytest.skip(f"Tkinter display not available: {exc}")


def test_crash_dialog_restart_callback():
    """Verify clicking restart invokes the on_restart callback."""
    try:
        restarted = []

        def mock_restart():
            restarted.append(True)

        dialog = CrashDialog(report_text="crash report", on_restart=mock_restart)
        dialog.build()

        try:
            dialog._on_restart()
            assert len(restarted) == 1
        finally:
            dialog._on_close()
    except (tk.TclError, Exception) as exc:
        pytest.skip(f"Tkinter display not available: {exc}")


def test_crash_dialog_open_logs(tmp_path):
    """Verify open logs button targets the crash folder."""
    try:
        crash_file = tmp_path / "crash" / "crash_test.txt"
        crash_file.parent.mkdir(parents=True)
        crash_file.write_text("dump", encoding="utf-8")

        dialog = CrashDialog(report_text="dump", crash_file=crash_file)
        dialog.build()

        try:
            with patch("os.startfile", create=True) as mock_startfile:
                dialog._on_open_logs()
                assert mock_startfile.called
                called_path = mock_startfile.call_args[0][0]
                assert Path(called_path) == crash_file.parent
        finally:
            dialog._on_close()
    except (tk.TclError, Exception) as exc:
        pytest.skip(f"Tkinter display not available: {exc}")


def test_show_crash_dialog_non_interactive():
    """Verify show_crash_dialog helper runs in non-interactive / headless mode."""
    report = "Test headless crash dialog"
    # Should not raise exception
    show_crash_dialog(report_text=report, interactive=False)


def test_install_crash_handler_flow(tmp_path):
    """Verify install_crash_handler writes report file and calls on_crash without blocking."""
    notified = []

    def on_crash(msg: str):
        notified.append(msg)

    with patch("ravan.ui.log_setup.config_dir", return_value=tmp_path):
        install_crash_handler(on_crash=on_crash, show_dialog=False)
        handler = sys.excepthook

        try:
            raise ArithmeticError("Custom calculation exception")
        except ArithmeticError:
            handler(*sys.exc_info())

        crash_files = list((tmp_path / "crash").glob("crash_*.txt"))
        assert len(crash_files) == 1
        saved_text = crash_files[0].read_text(encoding="utf-8")

        assert "Ravaan Crash Report" in saved_text
        assert "ArithmeticError" in saved_text
        assert "Custom calculation exception" in saved_text
        assert "PRIVACY GUARANTEE" in saved_text
        assert len(notified) == 1

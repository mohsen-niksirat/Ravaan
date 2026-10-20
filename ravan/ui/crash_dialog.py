"""Friendly bilingual crash dialog (Tkinter) for unexpected exceptions in Ravaan."""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Any

from ravan import __version__
from ravan.core.config import config_dir
from ravan.core.i18n import is_rtl, t
from ravan.ui.theme import get_active_palette

log = logging.getLogger(__name__)


def build_diagnostic_report(
    exc_type: type[BaseException] | None = None,
    exc_value: BaseException | None = None,
    exc_tb: Any = None,
    recent_logs: list[str] | None = None,
) -> str:
    """Build a sanitized diagnostic report containing system info and technical stack trace.

    Guarantees:
    - Strictly zero typed keystrokes, clipboard content, or credentials.
    - Captures OS version, Python version, architecture, and exception traceback.
    """
    import traceback
    from datetime import datetime

    now_iso = datetime.now().isoformat()
    os_info = f"{platform.platform()} ({platform.architecture()[0]})"
    py_info = f"{sys.version.split()[0]} ({platform.python_implementation()})"
    exe_info = sys.executable

    if exc_type is not None and exc_value is not None:
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        tb_text = "".join(tb_lines)
        exc_type_name = getattr(exc_type, "__name__", str(exc_type))
        exc_msg = str(exc_value)
    else:
        tb_text = "No active exception traceback.\n"
        exc_type_name = "N/A"
        exc_msg = "N/A"

    logs_section = ""
    if recent_logs:
        logs_section = (
            f"\n------------------------------------------------------------\n"
            f"RECENT LOG ENTRIES (Last {len(recent_logs)} lines)\n"
            f"------------------------------------------------------------\n"
            + "\n".join(recent_logs)
            + "\n"
        )

    return (
        f"============================================================\n"
        f"Ravaan Crash Report — {now_iso}\n"
        f"============================================================\n"
        f"Generated at : {now_iso}\n"
        f"App Version  : {__version__}\n"
        f"OS Platform  : {os_info}\n"
        f"Python       : {py_info}\n"
        f"Executable   : {exe_info}\n"
        f"\n"
        f"------------------------------------------------------------\n"
        f"PRIVACY GUARANTEE\n"
        f"------------------------------------------------------------\n"
        f"This report contains ONLY system metadata and technical stack\n"
        f"traces. Keystrokes, typed text, clipboard contents, and\n"
        f"credentials are NEVER recorded or included.\n"
        f"\n"
        f"------------------------------------------------------------\n"
        f"EXCEPTION DETAILS\n"
        f"------------------------------------------------------------\n"
        f"Type    : {exc_type_name}\n"
        f"Message : {exc_msg}\n"
        f"\n"
        f"Traceback:\n"
        f"{tb_text}"
        f"{logs_section}"
        f"============================================================\n"
    )


class CrashDialog:
    """Friendly bilingual error dialog displaying crash diagnostic details."""

    def __init__(
        self,
        report_text: str,
        crash_file: Path | None = None,
        on_restart: Any = None,
    ) -> None:
        self.report_text = report_text
        self.crash_file = crash_file
        self.on_restart = on_restart
        self._root: tk.Tk | tk.Toplevel | None = None
        self._btn_copy: ttk.Button | None = None

    def build(self, parent: tk.Tk | tk.Toplevel | None = None) -> tk.Tk | tk.Toplevel:
        """Construct the crash dialog window."""
        if parent is None:
            # Check if there is an existing default root window
            default_root = getattr(tk, "_default_root", None)
            if default_root is not None:
                root = tk.Toplevel(default_root)
            else:
                root = tk.Tk()
        else:
            root = tk.Toplevel(parent)

        self._root = root
        palette = get_active_palette("auto")

        rtl = is_rtl()
        title = t("crash.title", "Ravaan — Unexpected Error")
        root.title(title)
        root.geometry("680x560")
        root.minsize(580, 440)
        root.configure(bg=palette.bg)

        # Main frame
        main_frm = ttk.Frame(root, padding=16)
        main_frm.pack(fill="both", expand=True)

        # Header Title
        header_text = t("crash.header", "⚠️ Ravaan encountered an unexpected error")
        lbl_header = ttk.Label(
            main_frm,
            text=header_text,
            font=("Segoe UI" if not rtl else "Vazirmatn", 13, "bold"),
            foreground=palette.fg,
        )
        lbl_header.pack(anchor="w" if not rtl else "e", pady=(0, 6))

        # Description / Privacy notice
        desc_text = t(
            "crash.desc",
            "We apologize for the inconvenience. The application needs to close.\n\n"
            "🔒 Your privacy is strictly protected: your typed text, keystrokes, and "
            "sensitive personal information are NEVER included in crash reports.",
        )
        lbl_desc = ttk.Label(
            main_frm,
            text=desc_text,
            font=("Segoe UI" if not rtl else "Vazirmatn", 9),
            foreground=palette.subtext,
            justify="right" if rtl else "left",
            wraplength=640,
        )
        lbl_desc.pack(anchor="w" if not rtl else "e", pady=(0, 10))

        # Text area label
        lbl_report = ttk.Label(
            main_frm,
            text=t("crash.diagnostic_report_label", "Diagnostic Report (no private text):"),
            font=("Segoe UI" if not rtl else "Vazirmatn", 9, "bold"),
            foreground=palette.fg,
        )
        lbl_report.pack(anchor="w" if not rtl else "e", pady=(0, 4))

        # Report text box
        txt_frm = ttk.Frame(main_frm)
        txt_frm.pack(fill="both", expand=True, pady=(0, 12))

        txt_report = tk.Text(
            txt_frm,
            wrap="none",
            font=("Consolas", 9),
            bg=palette.card_bg,
            fg=palette.fg,
            insertbackground=palette.fg,
            relief="flat",
            padx=8,
            pady=8,
        )
        scroll_y = ttk.Scrollbar(txt_frm, orient="vertical", command=txt_report.yview)
        scroll_x = ttk.Scrollbar(txt_frm, orient="horizontal", command=txt_report.xview)
        txt_report.configure(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)

        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        txt_report.pack(side="left", fill="both", expand=True)

        txt_report.insert("1.0", self.report_text)
        txt_report.configure(state="disabled")

        # Action Buttons frame
        btn_frm = ttk.Frame(main_frm)
        btn_frm.pack(fill="x", pady=(4, 0))

        self._btn_copy = ttk.Button(
            btn_frm,
            text=t("crash.btn_copy", "📋 Copy Diagnostic Report"),
            command=self._on_copy,
        )
        self._btn_copy.pack(side="left" if not rtl else "right", padx=(0, 6))

        btn_logs = ttk.Button(
            btn_frm,
            text=t("crash.btn_logs", "📁 Open Logs Folder"),
            command=self._on_open_logs,
        )
        btn_logs.pack(side="left" if not rtl else "right", padx=6)

        btn_restart = ttk.Button(
            btn_frm,
            text=t("crash.btn_restart", "🔄 Restart Ravaan"),
            command=self._on_restart,
        )
        btn_restart.pack(side="right" if not rtl else "left", padx=6)

        btn_close = ttk.Button(
            btn_frm,
            text=t("crash.btn_close", "✕ Close"),
            command=self._on_close,
        )
        btn_close.pack(side="right" if not rtl else "left", padx=(6, 0))

        return root

    def _on_copy(self) -> None:
        """Copy diagnostic report text to system clipboard."""
        if self._root is None:
            return
        try:
            self._root.clipboard_clear()
            self._root.clipboard_append(self.report_text)
            if self._btn_copy:
                copied_lbl = t("crash.btn_copied", "✓ Copied to Clipboard!")
                self._btn_copy.configure(text=copied_lbl)
                self._root.after(
                    2000,
                    lambda: self._btn_copy.configure(
                        text=t("crash.btn_copy", "📋 Copy Diagnostic Report")
                    )
                    if self._btn_copy
                    else None,
                )
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to copy report to clipboard: %s", exc)

    def _on_open_logs(self) -> None:
        """Open logs / crash folder in Explorer."""
        target_dir = self.crash_file.parent if self.crash_file else (config_dir() / "logs")
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(target_dir)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to open logs folder: %s", exc)

    def _on_restart(self) -> None:
        """Restart Ravaan application process."""
        try:
            if callable(self.on_restart):
                self.on_restart()
            else:
                subprocess.Popen([sys.executable, *sys.argv])
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to restart Ravaan: %s", exc)
        finally:
            self._on_close()

    def _on_close(self) -> None:
        """Close dialog and terminate."""
        if self._root is not None:
            try:
                self._root.destroy()
            except Exception:  # noqa: BLE001
                pass
            self._root = None


def show_crash_dialog(
    report_text: str,
    crash_file: Path | None = None,
    interactive: bool = True,
) -> None:
    """Instantiate and show the crash dialog modal. Safe in headless environments."""
    try:
        dialog = CrashDialog(report_text=report_text, crash_file=crash_file)
        root = dialog.build()
        if interactive:
            root.mainloop()
        else:
            root.update_idletasks()
            root.destroy()
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not launch graphical crash dialog: %s", exc)

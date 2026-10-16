"""Diagnostics window (Tkinter) — live hook state, caret source, active app, and last 50 events."""

from __future__ import annotations

import platform
import sys
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Any

from ravan import __version__


class DiagnosticsWindow:
    """Live diagnostics window displaying hook status, caret detection source, and recent events."""

    def __init__(
        self,
        snapshot_fn: Callable[[], dict[str, Any]],
        on_close: Callable[[], None] | None = None,
    ) -> None:
        self.snapshot_fn = snapshot_fn
        self.on_close = on_close
        self._open = False
        self._built = False
        self._root: tk.Toplevel | None = None
        self._refresh_after: str | None = None

    @property
    def open(self) -> bool:
        return self._open

    def show(self) -> None:
        self._open = True

    def tick(self) -> None:
        if not self._open:
            return
        if not self._built:
            self._build()
            self._built = True
        if self._root is None:
            return
        try:
            self._root.update_idletasks()
            self._root.update()
        except (tk.TclError, RuntimeError):
            pass

    def _build(self) -> None:
        self._root = tk.Toplevel()
        self._root.title("Ravan — Diagnostics")
        self._root.geometry("700x520")
        self._root.minsize(620, 420)
        self._root.protocol("WM_DELETE_WINDOW", self._close)

        main_frm = ttk.Frame(self._root, padding=10)
        main_frm.pack(fill="both", expand=True)

        # ── System / Status Summary Frame ──
        summary_group = ttk.LabelFrame(main_frm, text="System & State Summary", padding=8)
        summary_group.pack(fill="x", pady=(0, 8))

        self._lbl_version = ttk.Label(summary_group, text="Version: ...")
        self._lbl_version.grid(row=0, column=0, sticky="w", padx=6, pady=2)

        self._lbl_hook = ttk.Label(summary_group, text="Hook: ...")
        self._lbl_hook.grid(row=0, column=1, sticky="w", padx=6, pady=2)

        self._lbl_app = ttk.Label(summary_group, text="Active App: ...")
        self._lbl_app.grid(row=1, column=0, sticky="w", padx=6, pady=2)

        self._lbl_excl = ttk.Label(summary_group, text="Excluded: ...")
        self._lbl_excl.grid(row=1, column=1, sticky="w", padx=6, pady=2)

        self._lbl_layout = ttk.Label(summary_group, text="Keyboard Layout: ...")
        self._lbl_layout.grid(row=2, column=0, sticky="w", padx=6, pady=2)

        self._lbl_caret = ttk.Label(summary_group, text="Caret Source & Pos: ...")
        self._lbl_caret.grid(row=2, column=1, sticky="w", padx=6, pady=2)

        # ── Recent Events Table ──
        events_group = ttk.LabelFrame(main_frm, text="Recent Events (Last 50)", padding=6)
        events_group.pack(fill="both", expand=True, pady=(0, 8))

        columns = ("time", "vk", "char", "layout", "action")
        self._tree = ttk.Treeview(
            events_group, columns=columns, show="headings", height=12
        )
        self._tree.heading("time", text="Time")
        self._tree.heading("vk", text="VK")
        self._tree.heading("char", text="Char")
        self._tree.heading("layout", text="Layout")
        self._tree.heading("action", text="Action / Event")

        self._tree.column("time", width=95, anchor="center")
        self._tree.column("vk", width=55, anchor="center")
        self._tree.column("char", width=55, anchor="center")
        self._tree.column("layout", width=65, anchor="center")
        self._tree.column("action", width=380, anchor="w")

        scrollbar = ttk.Scrollbar(
            events_group, orient="vertical", command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ── Buttons ──
        btns_frm = ttk.Frame(main_frm)
        btns_frm.pack(fill="x", pady=(4, 0))

        ttk.Button(
            btns_frm, text="📋 Copy Diagnostics Report", command=self._copy_report
        ).pack(side="left", padx=4)
        ttk.Button(
            btns_frm, text="🔄 Refresh Now", command=self._refresh
        ).pack(side="left", padx=4)

        self._auto_refresh_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            btns_frm, text="Auto-refresh (500ms)", variable=self._auto_refresh_var
        ).pack(side="left", padx=12)

        ttk.Button(btns_frm, text="Close", command=self._close).pack(
            side="right", padx=4
        )

        self._refresh()
        self._schedule_auto_refresh()

    def _schedule_auto_refresh(self) -> None:
        if self._root is None or not self._open:
            return
        if self._auto_refresh_var.get():
            self._refresh()
        self._refresh_after = self._root.after(500, self._schedule_auto_refresh)

    def _refresh(self) -> None:
        if self._root is None:
            return
        try:
            data = self.snapshot_fn()
        except Exception:
            return

        # Update summary labels
        version_str = f"Ravan {data.get('version', __version__)} (Python {sys.version.split()[0]})"
        self._lbl_version.config(text=f"Version: {version_str}")

        hook_status = "Active (running)" if data.get("hook_active") else "Inactive / Stopped"
        self._lbl_hook.config(text=f"Hook: {hook_status}")

        exe = data.get("foreground_exe") or "Unknown"
        pid = data.get("foreground_pid") or 0
        self._lbl_app.config(text=f"Active App: {exe} (PID {pid})")

        excl = "YES (Typing assistance paused)" if data.get("is_excluded") else "No (Active)"
        self._lbl_excl.config(text=f"Excluded: {excl}")

        layout = data.get("layout") or "Unknown"
        self._lbl_layout.config(text=f"Layout: {layout}")

        caret_src = data.get("caret_source") or "Unknown"
        caret_pos = data.get("caret_pos") or "(0, 0)"
        self._lbl_caret.config(text=f"Caret: {caret_src} {caret_pos}")

        # Update Treeview rows
        events = data.get("recent_events", [])
        self._tree.delete(*self._tree.get_children())
        for ev in reversed(events):
            self._tree.insert(
                "",
                "end",
                values=(
                    ev.get("time", ""),
                    ev.get("vk", ""),
                    ev.get("char", ""),
                    ev.get("layout", ""),
                    ev.get("action", ""),
                ),
            )

    def _copy_report(self) -> None:
        try:
            data = self.snapshot_fn()
            lines = [
                "# Ravan Diagnostics Report",
                f"- **Generated At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"- **Ravan Version:** {data.get('version', __version__)}",
                f"- **OS:** {platform.system()} {platform.release()} ({platform.architecture()[0]})",
                f"- **Python:** {sys.version.split()[0]}",
                f"- **Hook State:** {'Active' if data.get('hook_active') else 'Inactive'}",
                f"- **Active Foreground App:** {data.get('foreground_exe')} (PID: {data.get('foreground_pid')})",
                f"- **Window Title:** {data.get('window_title') or 'None'}",
                f"- **Is Excluded:** {data.get('is_excluded')}",
                f"- **Current Layout:** {data.get('layout')}",
                f"- **Caret Source:** {data.get('caret_source')}",
                f"- **Caret Coordinates:** {data.get('caret_pos')}",
                "",
                "## Recent Events (Most Recent First)",
                "| Time | VK | Char | Layout | Action |",
                "| --- | --- | --- | --- | --- |",
            ]
            for ev in reversed(data.get("recent_events", [])):
                t = ev.get("time", "")
                vk = ev.get("vk", "")
                c = ev.get("char", "").replace("|", "\\|")
                lay = ev.get("layout", "")
                act = ev.get("action", "").replace("|", "\\|")
                lines.append(f"| {t} | {vk} | {c} | {lay} | {act} |")

            report_text = "\n".join(lines)
            from ravan.platform.clipboard import set_clipboard_text

            set_clipboard_text(report_text)
            messagebox.showinfo(
                "Ravan Diagnostics",
                "Diagnostics report copied to clipboard!\nYou can now paste it into a GitHub issue.",
                parent=self._root,
            )
        except Exception as e:
            messagebox.showerror(
                "Ravan Diagnostics",
                f"Failed to copy report: {e}",
                parent=self._root,
            )

    def _close(self) -> None:
        self._open = False
        self._built = False
        if self._refresh_after is not None and self._root is not None:
            try:
                self._root.after_cancel(self._refresh_after)
            except Exception:
                pass
            self._refresh_after = None
        if self._root is not None:
            try:
                self._root.destroy()
            except tk.TclError:
                pass
            self._root = None
        if self.on_close:
            self.on_close()

"""Window picker dialog for selecting apps or window classes to exclude."""

from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Any

from ravan.ui.theme import (
    apply_theme_to_ttk,
    apply_window_decorations,
    get_active_palette,
)

log = logging.getLogger(__name__)



class WindowPickerWindow:
    def __init__(
        self,
        parent: tk.Tk | tk.Toplevel,
        on_pick: Callable[[str], None],
    ) -> None:
        self._parent = parent
        self._on_pick = on_pick
        self._root: tk.Toplevel | None = None
        self._tree: ttk.Treeview | None = None
        self._items: list[dict[str, Any]] = []
        self._countdown_job: str | None = None
        self._countdown_sec = 0

    def show(self) -> None:
        if self._root is not None:
            try:
                self._root.lift()
                self._root.focus_force()
                return
            except tk.TclError:
                self._root = None

        from ravan.core.i18n import is_rtl, t

        win = tk.Toplevel(self._parent)
        self._root = win
        win.title(t("picker.title", "Pick Window to Exclude — Ravaan"))
        win.geometry("560x420")
        win.minsize(450, 320)
        win.transient(self._parent)
        palette = get_active_palette()
        apply_window_decorations(win, palette)
        apply_theme_to_ttk(win, palette)
        win.protocol("WM_DELETE_WINDOW", self._close)

        pad = {"padx": 10, "pady": 6}

        hdr = ttk.Frame(win)
        hdr.pack(fill="x", **pad)
        ttk.Label(
            hdr,
            text=t("picker.instructions", "Select an open window from the list or capture with a delay:"),
            font=("Segoe UI", 9),
        ).pack(side="right" if is_rtl() else "left")

        tree_frame = ttk.Frame(win)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=4)

        cols = ("exe", "class", "title")
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        self._tree.heading("exe", text=t("picker.col_exe", "Executable (EXE)"))
        self._tree.heading("class", text=t("picker.col_class", "Window Class"))
        self._tree.heading("title", text=t("picker.col_title", "Window Title"))

        self._tree.column("exe", width=110, stretch=False)
        self._tree.column("class", width=140, stretch=False)
        self._tree.column("title", width=260, stretch=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._tree.bind("<Double-1>", lambda _: self._pick_selected_exe())

        btn_bar = ttk.Frame(win)
        btn_bar.pack(fill="x", padx=10, pady=(6, 10))

        side_l = "right" if is_rtl() else "left"
        side_r = "left" if is_rtl() else "right"

        ttk.Button(btn_bar, text=t("picker.refresh", "🔄 Refresh"), command=self._refresh_list).pack(side=side_l, padx=2)
        self._countdown_btn = ttk.Button(
            btn_bar, text=t("picker.capture_in_3s", "⏱ Capture in 3s…"), command=self._start_countdown
        )
        self._countdown_btn.pack(side=side_l, padx=6)

        ttk.Button(btn_bar, text=t("picker.cancel", "Cancel"), command=self._close).pack(side=side_r, padx=2)
        ttk.Button(
            btn_bar, text=t("picker.exclude_class", "Exclude Class"), command=self._pick_selected_class
        ).pack(side=side_r, padx=4)
        ttk.Button(
            btn_bar, text=t("picker.exclude_exe", "Exclude EXE"), command=self._pick_selected_exe
        ).pack(side=side_r, padx=4)

        self._refresh_list()

    def _refresh_list(self) -> None:
        if not self._tree:
            return
        self._tree.delete(*self._tree.get_children())
        from ravan.platform.focus import enumerate_visible_windows

        try:
            raw_wins = enumerate_visible_windows()
        except Exception:
            raw_wins = []

        self._items = []
        for w in raw_wins:
            exe = w.get("exe") or "unknown"
            cls = w.get("class_name") or "unknown"
            title = w.get("title") or ""
            if exe in ("python.exe", "pythonw.exe", "ravan.exe") and "Pick Window" in title:
                continue
            item_id = self._tree.insert("", "end", values=(exe, cls, title))
            self._items.append({"id": item_id, "exe": exe, "class": cls, "title": title})

    def _get_selected(self) -> dict[str, str] | None:
        if not self._tree:
            return None
        sel = self._tree.selection()
        if not sel:
            return None
        values = self._tree.item(sel[0], "values")
        if not values or len(values) < 2:
            return None
        return {"exe": values[0], "class": values[1], "title": values[2] if len(values) > 2 else ""}

    def _pick_selected_exe(self) -> None:
        item = self._get_selected()
        if not item or not item["exe"] or item["exe"] == "unknown":
            return
        self._on_pick(item["exe"].lower())
        self._close()

    def _pick_selected_class(self) -> None:
        item = self._get_selected()
        if not item or not item["class"] or item["class"] == "unknown":
            return
        self._on_pick(f"class:{item['class'].lower()}")
        self._close()

    def _start_countdown(self) -> None:
        if not self._root:
            return
        self._countdown_sec = 3
        self._countdown_btn.config(state="disabled")
        self._tick_countdown()

    def _tick_countdown(self) -> None:
        if not self._root:
            return
        from ravan.core.i18n import t

        if self._countdown_sec > 0:
            self._countdown_btn.config(
                text=t("picker.focus_target", "Focus target! ({sec}s)", sec=self._countdown_sec)
            )
            self._countdown_sec -= 1
            self._countdown_job = self._root.after(1000, self._tick_countdown)
        else:
            self._countdown_job = None
            self._countdown_btn.config(text=t("picker.capture_in_3s", "⏱ Capture in 3s…"), state="normal")
            from ravan.platform.focus import active_window_info

            info = active_window_info()
            exe = info.get("exe")
            cls = info.get("class_name")
            if exe and exe not in ("python.exe", "pythonw.exe", "ravan.exe"):
                self._on_pick(exe.lower())
                self._close()
            elif cls:
                self._on_pick(f"class:{cls.lower()}")
                self._close()

    def _close(self) -> None:
        if self._root:
            if self._countdown_job:
                try:
                    self._root.after_cancel(self._countdown_job)
                except Exception:
                    pass
                self._countdown_job = None
            try:
                self._root.destroy()
            except tk.TclError:
                pass
            self._root = None

"""Settings window (Tkinter) — hotkeys, toggles, snippets, exclusions."""

from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Any

from ravan.core.config import (
    Config,
    Snippet,
)

log = logging.getLogger(__name__)


class SettingsWindow:
    """Settings window driven by the app's main loop (no own mainloop).

    Tk is not thread-safe, so the window is created and pumped from the
    same thread that owns the overlay's Tk root. `show()` only requests
    opening; `tick()` builds and pumps the window.
    """

    def __init__(
        self,
        cfg: Config,
        on_saved: Callable[[Config], None] | None = None,
    ) -> None:
        self.cfg = cfg
        self.on_saved = on_saved
        self._open = False
        self._built = False
        self._root: tk.Toplevel | None = None
        self._snippet_editor = None
        self._managed_snippets = list(self.cfg.snippets)
        self._last_snip_text = ""

    @property
    def open(self) -> bool:
        return self._open

    def show(self) -> None:
        """Request opening (thread-safe; actual build happens in tick())."""
        self._open = True

    def tick(self) -> None:
        if not self._open:
            return
        if not self._built:
            self._built = True
            try:
                self._build()
            except Exception as exc:  # noqa: BLE001
                self._open = False
                if self._root is not None:
                    try:
                        self._root.destroy()
                    except Exception:  # noqa: BLE001
                        pass
                    self._root = None
                log.exception("SettingsWindow build failed: %s", exc)
                return
        if self._snippet_editor is not None and self._snippet_editor.open:
            self._snippet_editor.tick()
        if self._root is None:
            return
        try:
            self._root.update_idletasks()
            self._root.update()
        except (tk.TclError, RuntimeError):
            pass

    # ── UI construction ──────────────────────────────────────────────

    def _build(self) -> None:
        self._root = tk.Toplevel()
        self._root.withdraw()
        self._root.attributes("-topmost", True)
        self._root.resizable(False, False)
        self._root.protocol("WM_DELETE_WINDOW", self._close)
        self._render_ui()
        self._root.update_idletasks()
        self._center()
        self._root.deiconify()
        self._root.focus_set()

    def _render_ui(self) -> None:
        if self._root is None:
            return
        from ravan.core.i18n import is_rtl, t

        rtl = is_rtl()
        self._root.title(t("settings.title", "Ravaan — Settings"))

        for ch in self._root.winfo_children():
            ch.destroy()

        pad = {"padx": 10, "pady": 4}
        frm = ttk.Frame(self._root, padding=10)
        frm.pack(fill="both", expand=True)

        # Search Bar
        search_frm = ttk.Frame(frm)
        search_frm.pack(fill="x", pady=(0, 6))
        pack_side = "right" if rtl else "left"
        ttk.Label(search_frm, text=t("settings.search_label", "🔍 Search:")).pack(
            side=pack_side, padx=(0, 6) if not rtl else (6, 0)
        )
        self._search_var = tk.StringVar(value="")
        search_entry = ttk.Entry(search_frm, textvariable=self._search_var)
        search_entry.pack(side=pack_side, fill="x", expand=True)
        ttk.Button(
            search_frm,
            text="✕",
            width=3,
            command=lambda: self._search_var.set(""),
        ).pack(side=pack_side, padx=(4, 0))

        nb = ttk.Notebook(frm)
        nb.pack(fill="both", expand=True, pady=(0, 10))

        tab_general = ttk.Frame(nb, padding=10)
        tab_prediction = ttk.Frame(nb, padding=10)
        tab_hotkeys = ttk.Frame(nb, padding=10)
        tab_autofix = ttk.Frame(nb, padding=10)
        tab_exclusions = ttk.Frame(nb, padding=10)
        tab_snippets = ttk.Frame(nb, padding=10)
        tab_sync = ttk.Frame(nb, padding=10)
        tab_about = ttk.Frame(nb, padding=10)

        nb.add(tab_general, text=t("settings.tab_general", "General"))
        nb.add(tab_autofix, text=t("settings.tab_autofix", "Auto-Fix"))
        nb.add(tab_prediction, text=t("settings.tab_prediction", "Prediction"))
        nb.add(tab_hotkeys, text=t("settings.tab_hotkeys", "Hotkeys"))
        nb.add(tab_exclusions, text=t("settings.tab_exclusions", "Excluded Apps"))
        nb.add(tab_snippets, text=t("settings.tab_snippets", "Snippets"))
        nb.add(tab_sync, text=t("settings.tab_sync", "Cloud Sync"))
        nb.add(tab_about, text=t("settings.tab_about", "About"))

        from ravan.ui.settings_autofix import build_autofix_section
        from ravan.ui.settings_builder import (
            build_about_section,
            build_exclusions_section,
            build_general_section,
            build_hotkeys_section,
            build_prediction_section,
            build_snippets_section,
            build_sync_section,
        )

        build_general_section(self, tab_general, 0, pad)
        build_autofix_section(self, tab_autofix, 0, pad)
        build_prediction_section(self, tab_prediction, 0, pad)
        build_hotkeys_section(self, tab_hotkeys, 0, pad)
        build_exclusions_section(self, tab_exclusions, 0, pad)
        build_snippets_section(self, tab_snippets, 0, pad)
        build_sync_section(self, tab_sync, 0, pad)
        build_about_section(tab_about)

        tabs_spec = [
            (tab_general, t("settings.tab_general", "General"), ["lang", "startup", "sound", "calc", "theme", "زبان", "شروع", "صدا"]),
            (tab_autofix, t("settings.tab_autofix", "Auto-Fix"), ["autofix", "layout", "undo", "switch", "اصلاح", "چیدمان"]),
            (tab_prediction, t("settings.tab_prediction", "Prediction"), ["predict", "autocorrect", "zwnj", "words", "پیش‌بینی", "نیم‌فاصله"]),
            (tab_hotkeys, t("settings.tab_hotkeys", "Hotkeys"), ["f12", "hotkey", "convert", "clip", "case", "کلید"]),
            (tab_exclusions, t("settings.tab_exclusions", "Excluded Apps"), ["exclude", "blacklist", "app", "مستثنی"]),
            (tab_snippets, t("settings.tab_snippets", "Snippets"), ["snippet", "trigger", "متن"]),
            (tab_sync, t("settings.tab_sync", "Cloud Sync"), ["sync", "gist", "webdav", "همگام"]),
            (tab_about, t("settings.tab_about", "About"), ["about", "version", "درباره"]),
        ]

        def _filter_tabs(*_args: Any) -> None:
            q = self._search_var.get().strip().lower()
            first = None
            for tab_widget, title, kws in tabs_spec:
                if not q or q in title.lower() or any(q in kw for kw in kws):
                    nb.tab(tab_widget, state="normal")
                    if first is None:
                        first = tab_widget
                else:
                    nb.tab(tab_widget, state="hidden")
            if first is not None and q:
                nb.select(first)

        self._search_var.trace_add("write", _filter_tabs)

        # ── Buttons ──
        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(4, 0))
        btn_side = "left" if rtl else "right"
        ttk.Button(btns, text=t("settings.btn_cancel", "Cancel"), command=self._close).pack(side=btn_side, padx=4)
        ttk.Button(btns, text=t("settings.btn_save", "Save Settings"), command=self._save).pack(side=btn_side, padx=4)

        def _next_tab(_e: Any = None) -> str:
            tabs = nb.tabs()
            if tabs:
                cur = nb.index("current")
                nb.select(tabs[(cur + 1) % len(tabs)])
            return "break"

        def _prev_tab(_e: Any = None) -> str:
            tabs = nb.tabs()
            if tabs:
                cur = nb.index("current")
                nb.select(tabs[(cur - 1 + len(tabs)) % len(tabs)])
            return "break"

        self._root.bind("<Control-Tab>", _next_tab)
        self._root.bind("<Control-Shift-Tab>", _prev_tab)
        try:
            self._root.bind("<Control-ISO_Left_Tab>", _prev_tab)
        except tk.TclError:
            pass
        self._root.bind("<Escape>", lambda _: self._close())
        self._root.bind("<Control-Return>", lambda _: self._save())

    def _on_language_changed(self, _event: object = None) -> None:
        if not hasattr(self, "_ui_language_var"):
            return
        from ravan.core.i18n import set_locale

        val = self._ui_language_var.get()
        new_lang = "fa" if "فارسی" in val else ("en" if "English" in val else "auto")
        self.cfg.ui_language = new_lang
        set_locale(new_lang)
        if self._root:
            self._render_ui()

    def _center(self) -> None:
        if self._root is None:
            return
        self._root.update_idletasks()
        w = self._root.winfo_reqwidth()
        h = self._root.winfo_reqheight()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        x = max(20, (sw - w) // 2)
        y = max(20, (sh - h) // 3)
        self._root.geometry(f"+{x}+{y}")

    # ── Actions ──────────────────────────────────────────────────────

    def _get_current_exclusions_from_text(self) -> list[str]:
        raw = self._excl_text.get("1.0", "end").strip()
        return [line.strip().lower() for line in raw.splitlines() if line.strip()]

    def _detect_active_app(self) -> None:
        from ravan.core.config import is_app_excluded
        from ravan.platform.focus import active_window_info

        info = active_window_info()
        exe = info.get("exe")
        if not exe:
            self._detected_app_var.set("Active app: could not detect")
            self._add_detected_btn.config(state="disabled")
            return

        current_excls = self._get_current_exclusions_from_text()
        status = "EXCLUDED" if is_app_excluded(exe, current_excls) else "ACTIVE"
        self._last_detected_exe = exe
        self._detected_app_var.set(f"{exe}  [{status}]")
        self._add_detected_btn.config(state="normal")

    def _add_exclusion_item(self, item: str) -> None:
        item = item.strip().lower()
        if not item:
            return
        current = self._get_current_exclusions_from_text()
        if item not in current:
            text = self._excl_text.get("1.0", "end").rstrip()
            if text:
                text += "\n" + item + "\n"
            else:
                text = item + "\n"
            self._excl_text.delete("1.0", "end")
            self._excl_text.insert("1.0", text)
        self._detect_active_app()

    def _add_detected_to_exclusions(self) -> None:
        exe = getattr(self, "_last_detected_exe", None)
        if exe:
            self._add_exclusion_item(exe)

    def _open_window_picker(self) -> None:
        from ravan.ui.window_picker import WindowPickerWindow

        picker = WindowPickerWindow(self._root, on_pick=self._add_exclusion_item)
        picker.show()

    def _update_snip_display(self) -> None:
        if self._snip_text is None:
            return
        lines = []
        for s in self._managed_snippets:
            preview = s.replacement.replace("\n", "\\n")
            lines.append(f"{s.trigger} => {preview}")
        text = "\n".join(lines)
        self._snip_text.delete("1.0", "end")
        self._snip_text.insert("1.0", text)
        self._last_snip_text = text

    def _open_snippet_editor(self) -> None:
        from ravan.ui.snippet_editor import SnippetEditorWindow

        def on_editor_saved(snippets: list[Snippet]) -> None:
            self._managed_snippets = snippets
            self._update_snip_display()

        self._snippet_editor = SnippetEditorWindow(
            self._managed_snippets, on_saved=on_editor_saved
        )
        self._snippet_editor.show()

    def _close(self) -> None:
        self._open = False
        self._built = False
        if self._root is not None:
            try:
                self._root.destroy()
            except tk.TclError:
                pass
            self._root = None

    def _reset_tab_defaults(self, tab_name: str) -> None:
        from ravan.ui.settings_reset import reset_tab_defaults

        reset_tab_defaults(self, tab_name)

    def _save(self) -> None:
        from ravan.ui.settings_save import save_settings_window

        save_settings_window(self)

    def _sync_push(self) -> None:
        from ravan.ui.settings_sync import do_sync_push

        do_sync_push(self)

    def _sync_pull(self) -> None:
        from ravan.ui.settings_sync import do_sync_pull

        do_sync_pull(self)


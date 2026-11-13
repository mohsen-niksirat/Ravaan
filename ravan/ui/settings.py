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
from ravan.core.i18n import is_rtl, t
from ravan.ui.theme import (
    Palette,
    apply_theme_to_ttk,
    apply_window_decorations,
    get_active_palette,
    get_ui_font,
)

log = logging.getLogger(__name__)


class _ScrollableTab:
    """Scrollable container for Notebook tabs with responsive layout and mousewheel handling."""

    def __init__(self, notebook: ttk.Notebook, palette: Palette, rtl: bool = False, padding: int = 8) -> None:
        self.outer = ttk.Frame(notebook)
        self.canvas = tk.Canvas(
            self.outer,
            bg=palette.bg,
            highlightthickness=0,
            borderwidth=0,
        )
        self.scrollbar = ttk.Scrollbar(
            self.outer,
            orient="vertical",
            command=self.canvas.yview,
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        sb_side = "left" if rtl else "right"
        cv_side = "right" if rtl else "left"
        self.scrollbar.pack(side=sb_side, fill="y")
        self.canvas.pack(side=cv_side, fill="both", expand=True)

        self.inner = ttk.Frame(self.canvas, padding=padding)
        anchor = "ne" if rtl else "nw"
        self.win_id = self.canvas.create_window((0, 0), window=self.inner, anchor=anchor)

        def _on_canvas_configure(e: tk.Event) -> None:
            self.canvas.itemconfig(self.win_id, width=max(100, e.width))

        def _on_inner_configure(_e: tk.Event) -> None:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        self.canvas.bind("<Configure>", _on_canvas_configure)
        self.inner.bind("<Configure>", _on_inner_configure)

        def _on_wheel(e: tk.Event) -> None:
            if not self.canvas.winfo_exists():
                return
            if getattr(e, "num", None) == 4:
                self.canvas.yview_scroll(-2, "units")
            elif getattr(e, "num", None) == 5:
                self.canvas.yview_scroll(2, "units")
            elif getattr(e, "delta", 0):
                self.canvas.yview_scroll(int(-1 * (e.delta / 120) * 2), "units")

        self._on_wheel = _on_wheel
        self.canvas.bind("<MouseWheel>", _on_wheel)
        self.inner.bind("<MouseWheel>", _on_wheel)
        self.canvas.bind("<Button-4>", _on_wheel)
        self.canvas.bind("<Button-5>", _on_wheel)
        self.inner.bind("<Button-4>", _on_wheel)
        self.inner.bind("<Button-5>", _on_wheel)

    def bind_recursive_scroll(self, widget: tk.Widget) -> None:
        try:
            widget.bind("<MouseWheel>", self._on_wheel, add="+")
            widget.bind("<Button-4>", self._on_wheel, add="+")
            widget.bind("<Button-5>", self._on_wheel, add="+")
        except Exception:
            pass
        for child in widget.winfo_children():
            self.bind_recursive_scroll(child)


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
        learning_engine: Any = None,
    ) -> None:
        self.cfg = cfg
        self.on_saved = on_saved
        self.learning_engine = learning_engine
        self._open = False
        self._built = False
        self._root: tk.Toplevel | None = None
        self._snippet_editor: Any = None
        self._managed_snippets = list(self.cfg.snippets)
        self._last_snip_text = ""
        self._excl_text: tk.Text | None = None
        self._snip_text: tk.Text | None = None
        self._detected_app_var: tk.StringVar | None = None
        self._add_detected_btn: ttk.Button | None = None

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
        self._root.resizable(True, True)
        self._root.minsize(760, 520)
        # Close-with-change: closing the window applies (saves) pending edits.
        # Cancel / Escape remain explicit discard paths.
        self._root.protocol("WM_DELETE_WINDOW", self._save_then_close)
        palette = get_active_palette(getattr(self.cfg, "theme_mode", "auto"))
        apply_window_decorations(self._root, palette)
        apply_theme_to_ttk(self._root, palette)
        self._render_ui()
        self._root.update_idletasks()
        self._center()
        self._root.deiconify()
        self._root.focus_set()

    def _render_ui(self) -> None:
        if self._root is None:
            return

        rtl = is_rtl()
        self._root.title(t("settings.title", "Ravaan — Settings"))

        for ch in self._root.winfo_children():
            ch.destroy()

        palette = get_active_palette(getattr(self.cfg, "theme_mode", "auto"))
        pad = {"padx": 10, "pady": 4}
        frm = ttk.Frame(self._root, padding=0)
        frm.pack(fill="both", expand=True)

        # ── Bottom Action Bar: Pinned at bottom with elevated surface ──
        footer_bar = tk.Frame(
            frm,
            bg=palette.card_bg,
            highlightthickness=1,
            highlightbackground=palette.border,
            padx=18,
            pady=10,
        )
        footer_bar.pack(side="bottom", fill="x")
        btn_side = "left" if rtl else "right"
        hint_side = "right" if rtl else "left"

        shortcut_hint = (
            "Ctrl+Enter: ذخیره  ·  Esc: بستن  ·  Ctrl+Tab: جابه‌جایی تب"
            if rtl
            else "Ctrl+Enter: Save  ·  Esc: Close  ·  Ctrl+Tab: Switch Section"
        )
        tk.Label(
            footer_bar,
            text=shortcut_hint,
            bg=palette.card_bg,
            fg=palette.subtext,
            font=get_ui_font(size=8, rtl=rtl),
        ).pack(side=hint_side, padx=4)

        self._saved_label = tk.Label(
            footer_bar,
            text="",
            bg=palette.card_bg,
            fg=palette.success,
            font=get_ui_font(size=9, bold=True, rtl=rtl),
        )
        self._saved_label.pack(side=btn_side, padx=10)
        ttk.Button(footer_bar, text=t("settings.btn_close", "Close"), command=self._close).pack(
            side=btn_side, padx=4
        )
        ttk.Button(
            footer_bar,
            text=t("settings.btn_save", "Save Settings"),
            style="Accent.TButton",
            command=self._save,
        ).pack(side=btn_side, padx=4)

        # ── Top Hero Header Banner ──
        header_card = tk.Frame(
            frm,
            bg=palette.card_bg,
            highlightthickness=1,
            highlightbackground=palette.border,
            padx=20,
            pady=12,
        )
        header_card.pack(side="top", fill="x")
        h_pack = "right" if rtl else "left"
        h_badge_pack = "left" if rtl else "right"

        brand_col = tk.Frame(header_card, bg=palette.card_bg)
        brand_col.pack(side=h_pack)

        title_row = tk.Frame(brand_col, bg=palette.card_bg)
        title_row.pack(anchor="e" if rtl else "w")

        tk.Label(
            title_row,
            text="🪶 روان — Ravaan",
            bg=palette.card_bg,
            fg=palette.accent,
            font=get_ui_font(size=13, bold=True, rtl=rtl),
        ).pack(side=h_pack)

        from ravan import __version__

        tk.Label(
            title_row,
            text=f"v{__version__}",
            bg=palette.badge_bg,
            fg=palette.badge_fg,
            font=get_ui_font(size=8, bold=True),
            padx=8,
            pady=2,
        ).pack(side=h_pack, padx=8)

        sub_desc = (
            "مرکز کنترل هوشمند تایپ دو‌زبانه، اصلاح خودکار چیدمان و پیش‌بینی کلمات"
            if rtl
            else "Smart Bilingual Typing Assistant, Auto-Layout Fixer & Word Prediction Studio"
        )
        tk.Label(
            brand_col,
            text=sub_desc,
            bg=palette.card_bg,
            fg=palette.subtext,
            font=get_ui_font(size=8, rtl=rtl),
        ).pack(anchor="e" if rtl else "w", pady=(2, 0))

        # Integrated Search Pill on the opposite side of Header
        search_pill = tk.Frame(
            header_card,
            bg=palette.input_bg,
            highlightthickness=1,
            highlightbackground=palette.border,
            padx=8,
            pady=4,
        )
        search_pill.pack(side=h_badge_pack, pady=2)

        pack_side = "right" if rtl else "left"
        tk.Label(
            search_pill,
            text=t("settings.search_label", "🔍"),
            bg=palette.input_bg,
            fg=palette.subtext,
            font=get_ui_font(size=9, bold=True, rtl=rtl),
        ).pack(side=pack_side, padx=(0, 4) if not rtl else (4, 0))

        self._search_var = tk.StringVar(value="")
        search_entry = ttk.Entry(search_pill, textvariable=self._search_var, width=26)
        search_entry.pack(side=pack_side, fill="x", expand=True)
        ttk.Button(
            search_pill,
            text="✕",
            width=2,
            command=lambda: self._search_var.set(""),
        ).pack(side=pack_side, padx=(4, 0))

        # ── Main Workspace: Sidebar Navigation + Content Area ──
        body_frm = ttk.Frame(frm)
        body_frm.pack(side="top", fill="both", expand=True)

        sidebar_side = "right" if rtl else "left"
        content_side = "left" if rtl else "right"

        sidebar = tk.Frame(
            body_frm,
            bg=palette.card_bg,
            width=205,
            highlightthickness=1,
            highlightbackground=palette.border,
            padx=8,
            pady=10,
        )
        sidebar.pack(side=sidebar_side, fill="y")
        sidebar.pack_propagate(False)

        nav_hdr_txt = "بخش‌های تنظیمات" if rtl else "SETTINGS SECTIONS"
        tk.Label(
            sidebar,
            text=nav_hdr_txt,
            bg=palette.card_bg,
            fg=palette.subtext,
            font=get_ui_font(size=8, bold=True, rtl=rtl),
            anchor="e" if rtl else "w",
        ).pack(fill="x", padx=8, pady=(0, 6))

        content_host = ttk.Frame(body_frm, padding=(12, 8))
        content_host.pack(side=content_side, fill="both", expand=True)

        try:
            nb = ttk.Notebook(content_host, style="Hidden.TNotebook")
        except tk.TclError:
            nb = ttk.Notebook(content_host)
        nb.pack(fill="both", expand=True)
        self._nb = nb

        tab_general = _ScrollableTab(nb, palette, rtl=rtl, padding=10)
        tab_autofix = _ScrollableTab(nb, palette, rtl=rtl, padding=10)
        tab_prediction = _ScrollableTab(nb, palette, rtl=rtl, padding=10)
        tab_hotkeys = _ScrollableTab(nb, palette, rtl=rtl, padding=10)
        tab_exclusions = _ScrollableTab(nb, palette, rtl=rtl, padding=10)
        tab_profiles = _ScrollableTab(nb, palette, rtl=rtl, padding=10)
        tab_snippets = _ScrollableTab(nb, palette, rtl=rtl, padding=10)
        tab_sync = _ScrollableTab(nb, palette, rtl=rtl, padding=10)
        tab_about = _ScrollableTab(nb, palette, rtl=rtl, padding=10)

        nav_items = [
            (tab_general.outer, "⚙️", t("settings.tab_general", "General"), ["lang", "startup", "sound", "calc", "theme", "orthography", "toolbar", "undo", "زبان", "شروع", "صدا", "ویراستار", "نوار"]),
            (tab_autofix.outer, "⚡", t("settings.tab_autofix", "Auto-Fix"), ["autofix", "layout", "undo", "switch", "اصلاح", "چیدمان"]),
            (tab_prediction.outer, "🔮", t("settings.tab_prediction", "Prediction"), ["predict", "autocorrect", "zwnj", "words", "style", "learn", "corpus", "blacklist", "پیش‌بینی", "نیم‌فاصله", "استایل", "یادگیری"]),
            (tab_hotkeys.outer, "⌨️", t("settings.tab_hotkeys", "Hotkeys"), ["f12", "hotkey", "convert", "clip", "case", "کلید", "میانبر"]),
            (tab_exclusions.outer, "🚫", t("settings.tab_exclusions", "Exclusions"), ["exclude", "blacklist", "app", "مستثنی"]),
            (tab_profiles.outer, "🎯", t("settings.tab_profiles", "App Profiles"), ["profile", "code", "chat", "formal", "app", "layout", "پروفایل", "برنامه"]),
            (tab_snippets.outer, "📝", t("settings.tab_snippets", "Snippets"), ["snippet", "trigger", "متن", "قطعه"]),
            (tab_sync.outer, "☁️", t("settings.tab_sync", "Cloud Sync"), ["sync", "gist", "webdav", "همگام", "ابری"]),
            (tab_about.outer, "ℹ️", t("settings.tab_about", "About"), ["about", "version", "درباره"]),
        ]

        self._nav_buttons: list[tk.Button] = []

        def _select_nav(idx: int) -> None:
            tabs = nb.tabs()
            if 0 <= idx < len(tabs):
                try:
                    nb.select(tabs[idx])
                except tk.TclError:
                    pass
            _update_nav_highlight(idx)

        def _update_nav_highlight(active_idx: int) -> None:
            for i, btn in enumerate(self._nav_buttons):
                if i == active_idx:
                    btn.config(
                        bg=palette.highlight,
                        fg=palette.highlight_fg,
                        activebackground=palette.accent_hover,
                        activeforeground=palette.highlight_fg,
                        font=get_ui_font(size=9, bold=True, rtl=rtl),
                    )
                else:
                    btn.config(
                        bg=palette.card_bg,
                        fg=palette.fg,
                        activebackground=palette.button_hover,
                        activeforeground=palette.fg,
                        font=get_ui_font(size=9, bold=False, rtl=rtl),
                    )

        for idx, (tab_outer, icon, title, _kws) in enumerate(nav_items):
            nb.add(tab_outer, text=f"{icon} {title}")
            btn_text = f"{title}  {icon}" if rtl else f"{icon}   {title}"
            nav_btn = tk.Button(
                sidebar,
                text=btn_text,
                bd=0,
                relief="flat",
                padx=12,
                pady=8,
                anchor="e" if rtl else "w",
                justify="right" if rtl else "left",
                cursor="hand2",
                command=lambda i=idx: _select_nav(i),
            )
            nav_btn.pack(fill="x", pady=2)
            self._nav_buttons.append(nav_btn)

        def _on_nb_changed(_e: Any = None) -> None:
            try:
                cur_idx = nb.index("current")
                _update_nav_highlight(cur_idx)
            except Exception:
                pass

        nb.bind("<<NotebookTabChanged>>", _on_nb_changed)
        _update_nav_highlight(0)

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
        from ravan.ui.settings_profiles import build_profiles_section

        build_general_section(self, tab_general.inner, 0, pad)
        build_autofix_section(self, tab_autofix.inner, 0, pad)
        build_prediction_section(self, tab_prediction.inner, 0, pad)
        build_hotkeys_section(self, tab_hotkeys.inner, 0, pad)
        build_exclusions_section(self, tab_exclusions.inner, 0, pad)
        build_profiles_section(self, tab_profiles.inner, 0, pad)
        build_snippets_section(self, tab_snippets.inner, 0, pad)
        build_sync_section(self, tab_sync.inner, 0, pad)
        build_about_section(tab_about.inner)

        for tab in (
            tab_general,
            tab_autofix,
            tab_prediction,
            tab_hotkeys,
            tab_exclusions,
            tab_profiles,
            tab_snippets,
            tab_sync,
            tab_about,
        ):
            tab.bind_recursive_scroll(tab.inner)

        def _filter_tabs(*_args: Any) -> None:
            q = self._search_var.get().strip().lower()
            first_idx = None
            for idx, (tab_widget, _icon, title, kws) in enumerate(nav_items):
                matched = not q or q in title.lower() or any(q in kw for kw in kws)
                if matched:
                    nb.tab(tab_widget, state="normal")
                    self._nav_buttons[idx].config(state="normal")
                    if first_idx is None:
                        first_idx = idx
                else:
                    nb.tab(tab_widget, state="hidden")
                    self._nav_buttons[idx].config(
                        state="disabled",
                        bg=palette.card_bg,
                        fg=palette.subtext,
                    )
            if first_idx is not None and q:
                _select_nav(first_idx)
            elif not q:
                try:
                    _update_nav_highlight(nb.index("current"))
                except Exception:
                    pass

        self._search_var.trace_add("write", _filter_tabs)

        def _next_tab(_e: Any = None) -> str:
            tabs = nb.tabs()
            if tabs:
                cur = nb.index("current")
                nxt = (cur + 1) % len(tabs)
                _select_nav(nxt)
            return "break"

        def _prev_tab(_e: Any = None) -> str:
            tabs = nb.tabs()
            if tabs:
                cur = nb.index("current")
                prv = (cur - 1 + len(tabs)) % len(tabs)
                _select_nav(prv)
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
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        target_w = min(920, max(780, int(sw * 0.85)))
        target_h = min(700, max(520, int(sh * 0.84)))
        x = max(20, (sw - target_w) // 2)
        y = max(20, (sh - target_h) // 3)
        self._root.geometry(f"{target_w}x{target_h}+{x}+{y}")

    # ── Actions ──────────────────────────────────────────────────────

    def _get_current_exclusions_from_text(self) -> list[str]:
        if self._excl_text is None:
            return list(self.cfg.excluded_apps)
        raw = self._excl_text.get("1.0", "end").strip()
        return [line.strip().lower() for line in raw.splitlines() if line.strip()]

    def _detect_active_app(self) -> None:
        from ravan.core.config import is_app_excluded
        from ravan.platform.focus import active_window_info

        info = active_window_info()
        exe = info.get("exe")
        if not exe:
            if self._detected_app_var is not None:
                self._detected_app_var.set("Active app: could not detect")
            if self._add_detected_btn is not None:
                self._add_detected_btn.config(state="disabled")
            return

        current_excls = self._get_current_exclusions_from_text()
        status = "EXCLUDED" if is_app_excluded(exe, current_excls) else "ACTIVE"
        self._last_detected_exe = exe
        if self._detected_app_var is not None:
            self._detected_app_var.set(f"{exe}  [{status}]")
        if self._add_detected_btn is not None:
            self._add_detected_btn.config(state="normal")

    def _add_exclusion_item(self, item: str) -> None:
        item = item.strip().lower()
        if not item or self._excl_text is None:
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

        if self._root is None:
            return
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
            self._managed_snippets,
            on_saved=on_editor_saved,
            groups=getattr(self.cfg, "snippet_groups", None),
        )
        if self._snippet_editor is not None:
            self._snippet_editor.show()

    def _save_then_close(self) -> None:
        """Close-with-change: persist + apply pending edits, then close."""
        try:
            self._save()
        except Exception:  # noqa: BLE001
            log.exception("Save-on-close failed; closing without saving")
        self._close()

    def flash_saved(self) -> None:
        """Show a transient 'saved & applied' confirmation; window stays open."""
        from ravan.core.i18n import t

        if self._root is None or not self._root.winfo_exists():
            return
        try:
            self._saved_label.config(text="✓ " + t("settings.saved_flash", "ذخیره و اعمال شد — پنجره باز ماند"))
            if getattr(self, "_saved_flash_job", None):
                self._root.after_cancel(self._saved_flash_job)
            self._saved_flash_job = self._root.after(2500, lambda: self._saved_label.config(text=""))
        except Exception:  # noqa: BLE001
            pass

    def on_prediction_style_changed(self) -> None:
        """Apply-on-change: live-update the suggestion box design (no disk write)."""
        if hasattr(self, "_prediction_ui_style_var"):
            self.cfg.prediction_ui_style = self._prediction_ui_style_var.get()
        if hasattr(self, "_prediction_use_custom_colors_var"):
            self._prediction_use_custom_colors_var.set(False)
            self.cfg.prediction_use_custom_colors = False
        if hasattr(self, "_refresh_style_gallery"):
            try:
                self._refresh_style_gallery()
            except Exception:  # noqa: BLE001
                pass
        self._render_style_preview()
        if self.on_saved:
            self.on_saved(self.cfg)

    def on_prediction_layout_changed(self) -> None:
        """Apply-on-change: live-update suggestion box layout (vertical vs horizontal)."""
        if hasattr(self, "_prediction_layout_var"):
            self.cfg.prediction_layout = self._prediction_layout_var.get()
        self._render_style_preview()
        if self.on_saved:
            self.on_saved(self.cfg)

    def on_prediction_colors_changed(self) -> None:
        """Apply-on-change: live-update custom prediction colors."""
        if hasattr(self, "_prediction_use_custom_colors_var"):
            self.cfg.prediction_use_custom_colors = self._prediction_use_custom_colors_var.get()
        if hasattr(self, "_prediction_custom_bg_var"):
            self.cfg.prediction_custom_bg = self._prediction_custom_bg_var.get()
        if hasattr(self, "_prediction_custom_fg_var"):
            self.cfg.prediction_custom_fg = self._prediction_custom_fg_var.get()
        if hasattr(self, "_prediction_custom_accent_var"):
            self.cfg.prediction_custom_accent = self._prediction_custom_accent_var.get()
        if hasattr(self, "_prediction_custom_border_var"):
            self.cfg.prediction_custom_border = self._prediction_custom_border_var.get()
        if hasattr(self, "_prediction_custom_highlight_var"):
            self.cfg.prediction_custom_highlight = self._prediction_custom_highlight_var.get()
        self._render_style_preview()
        if self.on_saved:
            self.on_saved(self.cfg)

    def pick_prediction_color(self, field_name: str) -> None:
        """Open native color picker and update color swatch and preview."""
        import tkinter.colorchooser as cc

        var = getattr(self, f"_{field_name}_var", None)
        btn = getattr(self, f"_{field_name}_btn", None)
        if not var:
            return
        curr = var.get()
        picker_title = "انتخاب رنگ" if is_rtl() else "Choose Color"
        chosen = cc.askcolor(color=curr, parent=self._root, title=picker_title)
        if chosen and chosen[1]:
            hex_col = chosen[1].upper()
            var.set(hex_col)
            if btn:
                btn.config(bg=hex_col, activebackground=hex_col)
            if hasattr(self, "_prediction_use_custom_colors_var"):
                self._prediction_use_custom_colors_var.set(True)
            self.on_prediction_colors_changed()

    def reset_prediction_colors_to_style(self) -> None:
        """Reset custom color variables to match the currently selected style's palette."""
        from ravan.ui.theme import get_prediction_style

        style = (
            self._prediction_ui_style_var.get()
            if hasattr(self, "_prediction_ui_style_var")
            else "macos"
        )
        mode = getattr(self.cfg, "theme_mode", "auto")
        tokens = get_prediction_style(style, mode)
        pal = tokens.palette

        color_map = {
            "prediction_custom_bg": pal.bg,
            "prediction_custom_fg": pal.fg,
            "prediction_custom_accent": pal.accent,
            "prediction_custom_border": tokens.border_color or pal.border,
            "prediction_custom_highlight": pal.highlight,
        }
        for field, col in color_map.items():
            var = getattr(self, f"_{field}_var", None)
            btn = getattr(self, f"_{field}_btn", None)
            if var:
                var.set(col)
            if btn:
                btn.config(bg=col, activebackground=col)

        self.on_prediction_colors_changed()

    def apply_color_preset(
        self, bg: str, fg: str, accent: str, border: str, highlight: str
    ) -> None:
        """Apply a curated color preset and update preview immediately."""
        color_map = {
            "prediction_custom_bg": bg,
            "prediction_custom_fg": fg,
            "prediction_custom_accent": accent,
            "prediction_custom_border": border,
            "prediction_custom_highlight": highlight,
        }
        for field, col in color_map.items():
            var = getattr(self, f"_{field}_var", None)
            btn = getattr(self, f"_{field}_btn", None)
            if var:
                var.set(col)
            if btn:
                btn.config(bg=col, activebackground=col)

        if hasattr(self, "_prediction_use_custom_colors_var"):
            self._prediction_use_custom_colors_var.set(True)
        self.on_prediction_colors_changed()

    def on_lang_placement_changed(self) -> None:
        """Apply-on-change: live-update the language chip placement."""
        mapping = getattr(self, "_lang_placement_map", {})
        if hasattr(self, "_lang_placement_var"):
            self.cfg.lang_indicator_placement = mapping.get(
                self._lang_placement_var.get(), "bottom_right"
            )
        if self.on_saved:
            self.on_saved(self.cfg)

    _STYLE_TRAITS = {
        "macos": ("مک‌اواس با چراغ‌های راهنما 🔴🟡🟢، شیشه آکریلیک و انتخاب آبی اپل", 0.85),
        "modern": ("مدرن بنفش کیهانی با هایلایت بنفش درخشان و انحنای نرم", 0.96),
        "compact": ("فشرده و بهینه با پدینگ حداقلی و بیشترین بهره‌وری از فضا", 0.96),
        "glass": ("شیشه‌ای ارو با لبه بازتاب نور، شفافیت بالا و سطح نیمه‌مات", 0.68),
        "classic": ("کلاسیک سنتی با کادر پنجره — □ ✕ و هایلایت سرمه‌ای ویندوز", 1.0),
        "fluent": ("ویندوز ۱۱ فلوئنت میکا با لوگوی ویندوز و نوار تأکید آبی", 0.96),
        "material": ("گوگل متریال یو با نشان‌های دایره‌ای توپر و کپسول‌های نرم ۲۰px", 0.96),
        "ios": ("آیفون و آی‌اواس با آیکون اپل  و کپسول آبی الکتریک", 0.94),
        "minimal": ("مینیمال زن Linear با کلیدهای میانبر کیبورد و تمرکز خالص", 0.98),
        "neon": ("سایبرپانک HUD با کادر نئون سرخابی و متن‌های سبز درخشان", 0.98),
    }
    _STYLE_TRAITS_EN = {
        "macos": ("macOS with traffic lights 🔴🟡🟢, acrylic blur and Apple blue selection", 0.85),
        "modern": ("Cosmic deep violet with vibrant purple pill highlight", 0.96),
        "compact": ("Ultra-compact list with minimal padding and maximum efficiency", 0.96),
        "glass": ("Frosted Aero glass with specular light refraction rim", 0.68),
        "classic": ("Traditional retro frame with — □ ✕ title bar and classic navy selection", 1.0),
        "fluent": ("Windows 11 Fluent Mica with Windows logo and accent bar", 0.96),
        "material": ("Google Material You with filled circular badges and 20px pill", 0.96),
        "ios": ("Apple iOS with  icon and electric blue pill selection", 0.94),
        "minimal": ("Linear Minimal Zen with keyboard keycaps and zero chrome", 0.98),
        "neon": ("Cyberpunk HUD with glowing magenta border and electric green text", 0.98),
    }
    _STYLE_ICONS = {
        "macos": "🍎",
        "modern": "🔮",
        "compact": "📐",
        "glass": "💎",
        "classic": "🗔",
        "fluent": "🪟",
        "material": "🎨",
        "ios": "📱",
        "minimal": "⬛",
        "neon": "⚡",
    }
    _PREVIEW_BACKDROP = "#3c5068"  # representative desktop color for translucency

    @staticmethod
    def _blend_hex(fg_hex: str, bg_hex: str, t: float) -> str:
        """Blend two '#rrggbb' colors; t = share of bg_hex (0..1)."""
        try:
            a = int(fg_hex.lstrip("#"), 16)
            b = int(bg_hex.lstrip("#"), 16)
        except (ValueError, AttributeError):
            return fg_hex
        t = max(0.0, min(1.0, t))
        ch = [round(((a >> s) & 255) * (1 - t) + ((b >> s) & 255) * t) for s in (16, 8, 0)]
        return "#{:02x}{:02x}{:02x}".format(*ch)

    def _render_style_preview(self) -> None:
        """Render a live mini suggestion-box over a simulated desktop so each
        design style (and its geometry, tokens, translucency) is visibly distinct."""
        from ravan.ui.theme import get_prediction_style, get_ui_font

        preview = getattr(self, "_style_preview", None)
        if preview is None:
            return
        for ch in preview.winfo_children():
            ch.destroy()

        style = self._prediction_ui_style_var.get()
        mode = getattr(self.cfg, "theme_mode", "auto")
        layout = (
            self._prediction_layout_var.get()
            if hasattr(self, "_prediction_layout_var")
            else getattr(self.cfg, "prediction_layout", "vertical")
        )
        use_custom = (
            self._prediction_use_custom_colors_var.get()
            if hasattr(self, "_prediction_use_custom_colors_var")
            else getattr(self.cfg, "prediction_use_custom_colors", False)
        )
        custom_colors = None
        if use_custom:
            custom_colors = {
                "bg": (
                    self._prediction_custom_bg_var.get()
                    if hasattr(self, "_prediction_custom_bg_var")
                    else getattr(self.cfg, "prediction_custom_bg", "#202024")
                ),
                "fg": (
                    self._prediction_custom_fg_var.get()
                    if hasattr(self, "_prediction_custom_fg_var")
                    else getattr(self.cfg, "prediction_custom_fg", "#F5F5F7")
                ),
                "accent": (
                    self._prediction_custom_accent_var.get()
                    if hasattr(self, "_prediction_custom_accent_var")
                    else getattr(self.cfg, "prediction_custom_accent", "#0A84FF")
                ),
                "border": (
                    self._prediction_custom_border_var.get()
                    if hasattr(self, "_prediction_custom_border_var")
                    else getattr(self.cfg, "prediction_custom_border", "#3A3A42")
                ),
                "highlight": (
                    self._prediction_custom_highlight_var.get()
                    if hasattr(self, "_prediction_custom_highlight_var")
                    else getattr(self.cfg, "prediction_custom_highlight", "#0A84FF")
                ),
            }
        tokens = get_prediction_style(
            style, mode, custom_colors=custom_colors, layout=layout
        )
        palette = tokens.palette
        rtl_ui = is_rtl()
        traits_dict = self._STYLE_TRAITS if rtl_ui else self._STYLE_TRAITS_EN
        trait_text, _alpha_eff = traits_dict.get(style, traits_dict["modern"])
        style_icon = self._STYLE_ICONS.get(style, "✨")

        container = tk.Frame(preview)
        container.pack(fill="x")

        # Simulated modern desktop/editor canvas behind the mock popup
        canvas_h = 244
        is_dark_preview = mode == "dark" or (mode == "auto" and palette.name in ("dark", "high_contrast")) or style == "neon"
        canvas_bg = "#15161D" if is_dark_preview else "#F2F3F7"
        canvas_border = "#2A2B36" if is_dark_preview else "#D6D7DF"
        sim_text_fg = "#6E7681" if is_dark_preview else "#71767B"

        backdrop_canvas = tk.Canvas(
            container,
            height=canvas_h,
            highlightthickness=1,
            highlightbackground=canvas_border,
            bd=0,
            bg=canvas_bg,
        )
        backdrop_canvas.pack(fill="both", expand=True)

        from PIL import ImageTk

        from ravan.ui.preview_graphics import render_style_chassis

        is_horiz_preview = layout == "horizontal"
        card_w = 276 if is_horiz_preview else 260
        card_h = 64 if is_horiz_preview else 216
        chassis_img = render_style_chassis(
            style=style,
            width=card_w,
            height=card_h,
            is_dark=is_dark_preview,
            custom_colors=custom_colors,
            layout=layout,
        )
        self._preview_chassis_img = chassis_img
        self._preview_chassis_photo = ImageTk.PhotoImage(chassis_img)

        def _draw_content(cw_in: int) -> None:
            cw = max(cw_in, 300)
            backdrop_canvas.delete("all")

            # Subtle simulated typing line context
            typing_prompt = "متن در حال تایپ: سلام" if rtl_ui else "Typing: hello"
            caret_char = " |"
            f_sim = get_ui_font(size=8, rtl=rtl_ui)
            sim_lead_x = cw - 18 if rtl_ui else 18
            sim_anchor = "ne" if rtl_ui else "nw"
            backdrop_canvas.create_text(
                sim_lead_x,
                7,
                text=typing_prompt + caret_char,
                anchor=sim_anchor,
                fill=sim_text_fg,
                font=f_sim,
            )

            cx = cw // 2
            cy = (canvas_h // 2) if is_horiz_preview else (20 + card_h // 2)
            backdrop_canvas.create_image(cx, cy, image=self._preview_chassis_photo)

            x_left = cx - card_w // 2
            x_right = cx + card_w // 2
            y_top = cy - card_h // 2

            if is_horiz_preview:
                horiz_cands = [
                    ("۱ سلام علیکم", True),
                    ("۲ سلام", False),
                    ("۳ سلسفیلا", False),
                ]
                chip_w = (card_w - 36) // 3
                c1_right = x_right - 18
                for idx, (cand_label, is_sel) in enumerate(horiz_cands):
                    chip_cx = c1_right - idx * chip_w - chip_w // 2
                    if custom_colors:
                        fg_c = (
                            custom_colors.get("highlight_fg", "#FFFFFF")
                            if is_sel
                            else custom_colors.get("fg", "#F5F5F7")
                        )
                    elif is_sel:
                        fg_c = "#00FF66" if style == "neon" else "#FFFFFF"
                    elif style == "classic":
                        fg_c = "#000000"
                    elif style == "neon":
                        fg_c = "#00FF66"
                    else:
                        fg_c = "#E5E5EA"
                    backdrop_canvas.create_text(
                        chip_cx,
                        cy,
                        text=cand_label,
                        anchor="center",
                        fill=fg_c,
                        font=get_ui_font(size=9, bold=is_sel, rtl=True),
                    )
                return

            # ── Header titles on the chassis ──
            if style == "classic":
                backdrop_canvas.create_text(
                    x_left + 14,
                    y_top + 10,
                    text="روان - Ravaan",
                    anchor="w",
                    fill="#FFFFFF",
                    font=get_ui_font(size=8, bold=True, rtl=True),
                )
            elif style == "modern":
                backdrop_canvas.create_text(
                    cx,
                    y_top + 11,
                    text="✦  روان  ✦",
                    anchor="center",
                    fill="#E9D5FF",
                    font=get_ui_font(size=8, bold=True, rtl=True),
                )
            elif style == "fluent":
                backdrop_canvas.create_text(
                    x_left + 26,
                    y_top + 10,
                    text="روان",
                    anchor="w",
                    fill="#60CDFF",
                    font=get_ui_font(size=8, bold=True, rtl=True),
                )
            elif style == "ios":
                backdrop_canvas.create_text(
                    x_left + 16,
                    y_top + 11,
                    text=" روان",
                    anchor="w",
                    fill="#D2D2D7",
                    font=get_ui_font(size=8, bold=True, rtl=True),
                )
            elif style == "glass":
                backdrop_canvas.create_text(
                    cx,
                    y_top + 11,
                    text="💎  روان",
                    anchor="center",
                    fill="#A0D0FF",
                    font=get_ui_font(size=8, bold=True, rtl=True),
                )
            elif style == "neon":
                backdrop_canvas.create_text(
                    cx,
                    y_top + 11,
                    text="// RAVAAN HUD //",
                    anchor="center",
                    fill="#FF007F",
                    font=get_ui_font(size=8, bold=True),
                )
            elif style == "material":
                backdrop_canvas.create_text(
                    cx,
                    y_top + 11,
                    text="🎨 روان",
                    anchor="center",
                    fill="#D0BCFF",
                    font=get_ui_font(size=8, bold=True, rtl=True),
                )
            elif style == "compact":
                backdrop_canvas.create_text(
                    x_left + 14,
                    y_top + 8,
                    text="روان",
                    anchor="w",
                    fill="#8E8E96",
                    font=get_ui_font(size=8, bold=True, rtl=True),
                )
            elif style == "minimal":
                backdrop_canvas.create_text(
                    cx,
                    y_top + 10,
                    text="⋯ روان ⋯",
                    anchor="center",
                    fill="#808088",
                    font=get_ui_font(size=8, bold=True, rtl=True),
                )
            elif style == "macos":
                backdrop_canvas.create_text(
                    cx,
                    y_top + 11,
                    text="روان",
                    anchor="center",
                    fill="#94949E",
                    font=get_ui_font(size=8, bold=True, rtl=True),
                )

            # ── 5 Candidate Rows (matching user's reference mockup) ──
            candidates = [
                ("سلام علیکم", "1", True, "[ادامه]"),
                ("سلام", "2", False, ""),
                ("سلسفیلا", "3", False, ""),
                ("سلیس", "4", False, ""),
                ("سلاح", "5", False, ""),
            ]

            r1_y = y_top + 38
            if style == "compact":
                r1_y = y_top + 30
            elif style == "classic":
                r1_y = y_top + 34

            for idx, (cand_text, badge_num, is_sel, tag) in enumerate(candidates):
                row_y = r1_y + idx * 26
                if style == "compact":
                    row_y = r1_y + idx * 25

                # Colors per style
                if custom_colors:
                    if is_sel:
                        fg_c = custom_colors.get("highlight_fg", "#FFFFFF")
                        b_fg = custom_colors.get("highlight_fg", "#FFFFFF")
                    else:
                        fg_c = custom_colors.get("fg", "#F5F5F7")
                        b_fg = custom_colors.get("accent", "#0A84FF")
                elif is_sel:
                    fg_c = "#00FF66" if style == "neon" else "#FFFFFF"
                    b_fg = "#FF007F" if style == "neon" else ("#60CDFF" if style == "fluent" else "#FFFFFF")
                else:
                    if style == "neon":
                        fg_c, b_fg = "#00FF66", "#FF007F"
                    elif style == "classic":
                        fg_c, b_fg = "#000000", "#000000"
                    elif style == "fluent":
                        fg_c, b_fg = "#E0E0E0", "#60CDFF"
                    elif style == "modern":
                        fg_c, b_fg = "#F3E8FF", "#C77DFF"
                    elif style == "glass":
                        fg_c, b_fg = "#FFFFFF", "#8FA6BC"
                    elif style == "material":
                        fg_c, b_fg = "#E6E1E5", "#CAC4D0"
                    else:
                        fg_c, b_fg = "#C4C4CF", "#8C8C96"

                # Text
                f_row = get_ui_font(size=10 if is_sel else 9, bold=is_sel, rtl=True)
                backdrop_canvas.create_text(
                    x_right - 20,
                    row_y,
                    text=cand_text,
                    anchor="e",
                    fill=fg_c,
                    font=f_row,
                )

                # Badge
                b_x = x_left + 18
                backdrop_canvas.create_text(
                    b_x,
                    row_y,
                    text=badge_num,
                    anchor="center" if style in ("material", "minimal") else "w",
                    fill=b_fg,
                    font=get_ui_font(size=8, bold=is_sel),
                )

                # Tag or meter for row 1
                if is_sel:
                    m_col = "#00FF66" if style == "neon" else ("#60CDFF" if style == "fluent" else "#FFFFFF")
                    backdrop_canvas.create_text(
                        x_right - 78,
                        row_y,
                        text="████" if style == "neon" else "█",
                        anchor="e",
                        fill=m_col,
                        font=get_ui_font(size=8),
                    )
                    if tag:
                        tag_col = "#546E7A" if style == "neon" else ("#D4D0C8" if style == "classic" else "#A0C0E0")
                        backdrop_canvas.create_text(
                            x_right - 92,
                            row_y,
                            text=tag,
                            anchor="e",
                            fill=tag_col,
                            font=get_ui_font(size=7, rtl=True),
                        )

            # ── Hint Bar / Status ──
            if tokens.show_hint_bar and style != "compact":
                if style == "neon":
                    hint_mock = "[ESC: CLOSE  |  ENTER: ACCEPT  |  1-5: QUICK PICK]"
                    hint_fg = "#FF007F"
                elif style == "classic":
                    hint_mock = "بستن: Esc  ·  تأیید: Enter  ·  انتخاب: ۱-۵ سریع" if rtl_ui else "Esc: Close  ·  Enter: Accept  ·  1-5: Pick"
                    hint_fg = "#505050"
                elif style == "fluent":
                    hint_mock = "بستن: Esc  ·  تأیید: Enter  ·  انتخاب: ۱-۵ سریع" if rtl_ui else "Esc: Close  ·  Enter: Accept  ·  1-5: Pick"
                    hint_fg = "#60CDFF"
                elif style == "modern":
                    hint_mock = "بستن: Esc  ·  تأیید: Enter  ·  انتخاب: ۱-۵ سریع" if rtl_ui else "Esc: Close  ·  Enter: Accept  ·  1-5: Pick"
                    hint_fg = "#A894C4"
                elif style == "glass":
                    hint_mock = "بستن: Esc  ·  تأیید: Enter  ·  انتخاب: ۱-۵ سریع" if rtl_ui else "Esc: Close  ·  Enter: Accept  ·  1-5: Pick"
                    hint_fg = "#8AB4D8"
                else:
                    hint_mock = "بستن: Esc  ·  تأیید: Enter  ·  انتخاب: ۱-۵ سریع" if rtl_ui else "Esc: Close  ·  Enter: Accept  ·  1-5: Pick"
                    hint_fg = "#787884"

                backdrop_canvas.create_text(
                    cx,
                    y_top + card_h - 10,
                    text=hint_mock,
                    anchor="center",
                    fill=hint_fg,
                    font=get_ui_font(size=7, rtl=rtl_ui),
                )

        backdrop_canvas.update_idletasks()
        init_w = backdrop_canvas.winfo_width()
        _draw_content(init_w if init_w > 50 else 320)
        backdrop_canvas.bind("<Configure>", lambda e: _draw_content(e.width))

        # Bottom info pill banner
        info_bar = tk.Frame(preview, bg=palette.card_bg, padx=8, pady=3)
        info_bar.pack(fill="x", pady=(2, 0))

        is_horizontal = tokens.layout == "horizontal"
        if rtl_ui:
            layout_txt = "افقی (رو‌به‌روی هم)" if is_horizontal else "عمودی (زیر هم)"
            custom_txt = " · رنگ‌های سفارشی" if use_custom else ""
        else:
            layout_txt = "Horizontal Ribbon" if is_horizontal else "Vertical Stack"
            custom_txt = " · Custom Colors" if use_custom else ""

        ttk.Label(
            info_bar,
            text=f"{style_icon}  {style.upper()} ({layout_txt}{custom_txt})",
            font=get_ui_font(size=9, bold=True),
            foreground=palette.accent,
        ).pack(side="left", padx=(4, 8))

        ttk.Label(
            info_bar,
            text=trait_text,
            style="Sub.TLabel",
        ).pack(side="left", fill="x", expand=True)

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


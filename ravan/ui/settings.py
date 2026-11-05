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
from ravan.ui.theme import (
    Palette,
    apply_theme_to_ttk,
    apply_window_decorations,
    get_active_palette,
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
    ) -> None:
        self.cfg = cfg
        self.on_saved = on_saved
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
        self._root.minsize(620, 440)
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
        from ravan.core.i18n import is_rtl, t

        rtl = is_rtl()
        self._root.title(t("settings.title", "Ravaan — Settings"))

        for ch in self._root.winfo_children():
            ch.destroy()

        palette = get_active_palette(getattr(self.cfg, "theme_mode", "auto"))
        pad = {"padx": 8, "pady": 3}
        frm = ttk.Frame(self._root, padding=8)
        frm.pack(fill="both", expand=True)

        # ── Buttons: Pinned at bottom so they are NEVER cut off ──
        btns = ttk.Frame(frm)
        btns.pack(side="bottom", fill="x", pady=(6, 0))
        btn_side = "left" if rtl else "right"
        self._saved_label = ttk.Label(btns, text="", foreground=palette.success)
        self._saved_label.pack(side=btn_side, padx=8)
        ttk.Button(btns, text=t("settings.btn_cancel", "Cancel"), command=self._close).pack(side=btn_side, padx=4)
        ttk.Button(btns, text=t("settings.btn_save", "Save Settings"), style="Accent.TButton", command=self._save).pack(side=btn_side, padx=4)

        # ── Search Bar: Top ──
        search_frm = ttk.Frame(frm)
        search_frm.pack(side="top", fill="x", pady=(0, 6))
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

        # ── Notebook in middle: Expands and fills remaining space ──
        nb = ttk.Notebook(frm)
        nb.pack(side="top", fill="both", expand=True)
        self._nb = nb

        tab_general = _ScrollableTab(nb, palette, rtl=rtl, padding=8)
        tab_autofix = _ScrollableTab(nb, palette, rtl=rtl, padding=8)
        tab_prediction = _ScrollableTab(nb, palette, rtl=rtl, padding=8)
        tab_hotkeys = _ScrollableTab(nb, palette, rtl=rtl, padding=8)
        tab_exclusions = _ScrollableTab(nb, palette, rtl=rtl, padding=8)
        tab_snippets = _ScrollableTab(nb, palette, rtl=rtl, padding=8)
        tab_sync = _ScrollableTab(nb, palette, rtl=rtl, padding=8)
        tab_about = _ScrollableTab(nb, palette, rtl=rtl, padding=8)

        nb.add(tab_general.outer, text=f"⚙️ {t('settings.tab_general', 'General')}")
        nb.add(tab_autofix.outer, text=f"⚡ {t('settings.tab_autofix', 'Auto-Fix')}")
        nb.add(tab_prediction.outer, text=f"🔮 {t('settings.tab_prediction', 'Prediction')}")
        nb.add(tab_hotkeys.outer, text=f"⌨️ {t('settings.tab_hotkeys', 'Hotkeys')}")
        nb.add(tab_exclusions.outer, text=f"🚫 {t('settings.tab_exclusions', 'Exclusions')}")
        nb.add(tab_snippets.outer, text=f"📝 {t('settings.tab_snippets', 'Snippets')}")
        nb.add(tab_sync.outer, text=f"☁️ {t('settings.tab_sync', 'Cloud Sync')}")
        nb.add(tab_about.outer, text=f"ℹ️ {t('settings.tab_about', 'About')}")

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

        build_general_section(self, tab_general.inner, 0, pad)
        build_autofix_section(self, tab_autofix.inner, 0, pad)
        build_prediction_section(self, tab_prediction.inner, 0, pad)
        build_hotkeys_section(self, tab_hotkeys.inner, 0, pad)
        build_exclusions_section(self, tab_exclusions.inner, 0, pad)
        build_snippets_section(self, tab_snippets.inner, 0, pad)
        build_sync_section(self, tab_sync.inner, 0, pad)
        build_about_section(tab_about.inner)

        for tab in (
            tab_general,
            tab_autofix,
            tab_prediction,
            tab_hotkeys,
            tab_exclusions,
            tab_snippets,
            tab_sync,
            tab_about,
        ):
            tab.bind_recursive_scroll(tab.inner)

        tabs_spec = [
            (tab_general.outer, t("settings.tab_general", "General"), ["lang", "startup", "sound", "calc", "theme", "زبان", "شروع", "صدا"]),
            (tab_autofix.outer, t("settings.tab_autofix", "Auto-Fix"), ["autofix", "layout", "undo", "switch", "اصلاح", "چیدمان"]),
            (tab_prediction.outer, t("settings.tab_prediction", "Prediction"), ["predict", "autocorrect", "zwnj", "words", "پیش‌بینی", "نیم‌فاصله"]),
            (tab_hotkeys.outer, t("settings.tab_hotkeys", "Hotkeys"), ["f12", "hotkey", "convert", "clip", "case", "کلید"]),
            (tab_exclusions.outer, t("settings.tab_exclusions", "Excluded Apps"), ["exclude", "blacklist", "app", "مستثنی"]),
            (tab_snippets.outer, t("settings.tab_snippets", "Snippets"), ["snippet", "trigger", "متن"]),
            (tab_sync.outer, t("settings.tab_sync", "Cloud Sync"), ["sync", "gist", "webdav", "همگام"]),
            (tab_about.outer, t("settings.tab_about", "About"), ["about", "version", "درباره"]),
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
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        target_w = min(800, max(680, int(sw * 0.85)))
        target_h = min(660, max(460, int(sh * 0.82)))
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
        self._render_style_preview()
        if self.on_saved:
            self.on_saved(self.cfg)

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
        "macos": ("متریال آکریلیک شیشه‌ای + حاشیه مویی — پیش‌فرض", 0.82),
        "modern": ("فلوئنت ۲ ویندوز ۱۱", 0.96),
        "compact": ("فشرده با فاصله کم", 0.96),
        "glass": ("شیشه‌ای با شفافیت بالا", 0.55),
        "classic": ("کلاسیک مات با قاب ضخیم", 1.0),
    }
    _PREVIEW_BACKDROP = "#4a6a8a"  # representative desktop color for translucency

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
        design style (and its translucency) is visibly distinct."""
        from ravan.ui.theme import get_macos_palette, get_ui_font

        preview = getattr(self, "_style_preview", None)
        if preview is None:
            return
        for ch in preview.winfo_children():
            ch.destroy()

        style = self._prediction_ui_style_var.get()
        mode = getattr(self.cfg, "theme_mode", "auto")
        palette = get_macos_palette(mode) if style == "macos" else get_active_palette(mode)
        trait_text, alpha_eff = self._STYLE_TRAITS.get(style, self._STYLE_TRAITS["modern"])
        f_sz = int(getattr(self.cfg, "prediction_font_size", 12))
        pad_y = 2 if style == "compact" else (5 if style == "macos" else 4)
        pad_x = 8 if style == "compact" else (14 if style == "macos" else 10)
        backdrop = self._PREVIEW_BACKDROP
        see_through = 1.0 - alpha_eff  # share of the desktop showing through

        container = tk.Frame(preview)
        container.pack(fill="x")

        # Simulated desktop (colored bands + window blocks) behind the mock.
        backdrop_canvas = tk.Canvas(
            container, height=126, highlightthickness=0, bd=0, bg="#31518a"
        )
        backdrop_canvas.pack(fill="both", expand=True)
        backdrop_canvas.update_idletasks()
        cw = max(backdrop_canvas.winfo_width(), 280)
        band_colors = ["#2f6f4f", "#31518a", "#8a5131", "#5a3a6e", "#2b6d6d"]
        band_h = 126 // len(band_colors) + 1
        for i, color in enumerate(band_colors):
            backdrop_canvas.create_rectangle(
                0, i * band_h, cw, (i + 1) * band_h, fill=color, width=0
            )
        backdrop_canvas.create_rectangle(
            cw - 90, 14, cw - 14, 58, fill="#c9cdd4", width=0
        )
        backdrop_canvas.create_rectangle(
            18, 84, 120, 112, fill="#d8b24a", width=0
        )

        # The mock popup: blended colors make the style's translucency visible.
        eff_bg = self._blend_hex(palette.bg, backdrop, see_through)
        eff_row = self._blend_hex(
            palette.card_bg if style == "macos" else palette.bg, backdrop, see_through
        )
        eff_border = self._blend_hex(palette.border, backdrop, see_through * 0.6)
        eff_selected = self._blend_hex(palette.highlight, backdrop, see_through * 0.25)

        mock = tk.Frame(
            container,
            bg=eff_bg,
            highlightthickness=2 if style == "classic" else 1,
            highlightbackground=eff_border,
        )
        mock.place(relx=0.5, rely=0.5, anchor="center")

        rows = [
            ("1   سلام", True),
            ("2   سلام علیکم   [ادامه]", False),
            ("3   سلامتی", False),
        ]
        for text, selected in rows:
            if selected:
                bg, fg, bold = eff_selected, palette.highlight_fg, True
            else:
                bg = eff_row
                fg = palette.subtext if "[ادامه]" in text else palette.fg
                bold = False
            tk.Label(
                mock,
                text=text,
                bg=bg,
                fg=fg,
                font=get_ui_font(size=f_sz, bold=bold, rtl=True),
                anchor="w",
                padx=pad_x,
                pady=pad_y,
            ).pack(fill="x")
        tk.Label(
            mock,
            text="↑↓ انتخاب  ·  Enter تأیید  ·  Esc بستن",
            bg=eff_row,
            fg=palette.subtext,
            font=get_ui_font(size=max(8, f_sz - 3), rtl=True),
            padx=pad_x,
            pady=3,
        ).pack(fill="x")

        ttk.Label(
            preview,
            text=f"{style} — {trait_text}",
            foreground=palette.subtext if hasattr(palette, "subtext") else "gray",
        ).pack(anchor="w", padx=8, pady=(2, 0))

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


"""Settings window (Tkinter) — Fluent 2 workspace with vector sidebar, search, and live preview."""

from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Any

from ravan.core.config import Config, Snippet
from ravan.core.i18n import is_rtl, t
from ravan.ui.settings_builder import _ScrollableTab
from ravan.ui.settings_preview import SettingsPreviewMixin
from ravan.ui.theme import (
    apply_theme_to_ttk,
    apply_window_decorations,
    create_managed_toplevel,
    destroy_managed_toplevel,
    get_active_palette,
    get_dpi_scale,
    get_ui_font,
)
from ravan.ui.widgets import FluentBadge, FluentEntry, FluentPillButton, get_icon

log = logging.getLogger(__name__)


class SettingsWindow(SettingsPreviewMixin):
    """Settings window driven by the app's main loop (no own mainloop)."""

    def __init__(
        self, cfg: Config, on_saved: Callable[[Config], None] | None = None,
        learning_engine: Any = None, parent: tk.Misc | None = None,
    ) -> None:
        self.cfg, self.on_saved, self.learning_engine, self._parent = cfg, on_saved, learning_engine, parent
        self._open = self._built = False
        self._root: tk.Toplevel | None = None
        self._owned_tk_root: tk.Tk | None = None
        self._saved_flash_job: str | None = None
        self._snippet_editor: Any = None
        self._managed_snippets = list(self.cfg.snippets)
        self._last_snip_text = ""
        self._excl_text: tk.Text | None = None
        self._snip_text: tk.Text | None = None
        self._detected_app_var: tk.StringVar | None = None
        self._add_detected_btn: Any = None
        self._nav_icon_photos: list[Any] = []

    @property
    def open(self) -> bool:
        return self._open

    def show(self) -> None:
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
                destroy_managed_toplevel(self._root, self._owned_tk_root)
                self._root = self._owned_tk_root = None
                log.exception("SettingsWindow build failed: %s", exc)
                return
        if self._snippet_editor is not None and self._snippet_editor.open:
            self._snippet_editor.tick()
        if self._root is not None:
            try:
                self._root.update_idletasks()
                self._root.update()
            except (tk.TclError, RuntimeError):
                pass

    def _build(self) -> None:
        self._root, self._owned_tk_root = create_managed_toplevel(self._parent)
        self._root.withdraw()
        self._root.attributes("-topmost", True)
        self._root.resizable(True, True)
        self._root.minsize(780, 540)
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
        dpi = get_dpi_scale(self._root)
        pad = {"padx": 10, "pady": 4}
        frm = ttk.Frame(self._root, padding=0)
        frm.pack(fill="both", expand=True)

        # ── Bottom Action Bar ──
        footer_bar = tk.Frame(frm, bg=palette.bg_surface, highlightthickness=1, highlightbackground=palette.border_subtle, padx=18, pady=10)
        footer_bar.pack(side="bottom", fill="x")
        btn_side, hint_side = ("left", "right") if rtl else ("right", "left")
        shortcut_hint = "Ctrl+Enter: ذخیره  ·  Esc: بستن  ·  Ctrl+Tab: جابه‌جایی تب" if rtl else "Ctrl+Enter: Save  ·  Esc: Close  ·  Ctrl+Tab: Switch Section"
        tk.Label(footer_bar, text=shortcut_hint, bg=palette.bg_surface, fg=palette.subtext, font=get_ui_font(size=8, rtl=rtl)).pack(side=hint_side, padx=4)

        self._saved_label = tk.Label(footer_bar, text="", bg=palette.bg_surface, fg=palette.success, font=get_ui_font(size=9, bold=True, rtl=rtl))
        self._saved_label.pack(side=btn_side, padx=10)
        FluentPillButton(footer_bar, text=t("settings.btn_close", "Close"), variant="secondary", palette=palette, rtl=rtl, command=self._close).pack(side=btn_side, padx=4)
        FluentPillButton(footer_bar, text=t("settings.btn_save", "Save Settings"), icon="check", variant="primary", palette=palette, rtl=rtl, command=self._save).pack(side=btn_side, padx=4)

        # ── Top Hero Header Banner ──
        header_card = tk.Frame(frm, bg=palette.bg_surface, highlightthickness=1, highlightbackground=palette.border_subtle, padx=20, pady=12)
        header_card.pack(side="top", fill="x")
        h_pack, h_badge_pack = ("right", "left") if rtl else ("left", "right")

        brand_col = tk.Frame(header_card, bg=palette.bg_surface)
        brand_col.pack(side=h_pack)
        title_row = tk.Frame(brand_col, bg=palette.bg_surface)
        title_row.pack(anchor="e" if rtl else "w")

        self._brand_icon = get_icon("feather", size=18, color=palette.accent, dpi=dpi, master=self._root)
        if self._brand_icon is not None:
            tk.Label(title_row, image=self._brand_icon, bg=palette.bg_surface, bd=0).pack(side=h_pack, padx=(6, 0) if rtl else (0, 6))
        tk.Label(title_row, text="روان — Ravaan", bg=palette.bg_surface, fg=palette.accent, font=get_ui_font(size=13, bold=True, rtl=rtl)).pack(side=h_pack)

        from ravan import __version__

        FluentBadge(title_row, text=f"v{__version__}", palette=palette, parent_bg=palette.bg_surface).pack(side=h_pack, padx=8)
        sub_desc = "مرکز کنترل هوشمند تایپ دو‌زبانه، اصلاح خودکار چیدمان و پیش‌بینی کلمات" if rtl else "Smart Bilingual Typing Assistant, Auto-Layout Fixer & Word Prediction Studio"
        tk.Label(brand_col, text=sub_desc, bg=palette.bg_surface, fg=palette.subtext, font=get_ui_font(size=8, rtl=rtl)).pack(anchor="e" if rtl else "w", pady=(2, 0))

        self._search_var = tk.StringVar(value="")
        self._search_entry = FluentEntry(
            header_card, textvariable=self._search_var,
            placeholder="جستجو در تنظیمات..." if rtl else "Search settings...",
            width=26, palette=palette, rtl=rtl, leading_icon="search", clearable=True,
        )
        self._search_entry.pack(side=h_badge_pack, pady=2)

        # ── Main Workspace: Sidebar Navigation + Content Area ──
        body_frm = ttk.Frame(frm)
        body_frm.pack(side="top", fill="both", expand=True)

        sidebar = tk.Frame(body_frm, bg=palette.bg_surface, width=210, highlightthickness=1, highlightbackground=palette.border_subtle, padx=8, pady=10)
        sidebar.pack(side="right" if rtl else "left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="بخش‌های تنظیمات" if rtl else "SETTINGS SECTIONS", bg=palette.bg_surface, fg=palette.subtext, font=get_ui_font(size=8, bold=True, rtl=rtl), anchor="e" if rtl else "w").pack(fill="x", padx=8, pady=(0, 6))

        content_host = ttk.Frame(body_frm, padding=(12, 8))
        content_host.pack(side="left" if rtl else "right", fill="both", expand=True)
        try:
            nb = ttk.Notebook(content_host, style="Hidden.TNotebook")
        except tk.TclError:
            nb = ttk.Notebook(content_host)
        nb.pack(fill="both", expand=True)
        self._nb = nb

        tabs_list = [_ScrollableTab(nb, palette, rtl=rtl, padding=10) for _ in range(10)]
        t_gen, t_af, t_pred, t_hk, t_excl, t_prof, t_snip, t_sync, t_ai, t_about = tabs_list

        nav_items = [
            (t_gen.outer, "settings", t("settings.tab_general", "General"), ["lang", "startup", "sound", "calc", "theme", "orthography", "toolbar", "undo", "زبان", "شروع", "صدا", "ویراستار", "نوار"]),
            (t_af.outer, "bolt", t("settings.tab_autofix", "Auto-Fix"), ["autofix", "layout", "undo", "switch", "اصلاح", "چیدمان"]),
            (t_pred.outer, "sparkle", t("settings.tab_prediction", "Prediction"), ["predict", "autocorrect", "zwnj", "words", "style", "learn", "corpus", "blacklist", "پیش‌بینی", "نیم‌فاصله", "استایل", "یادگیری"]),
            (t_hk.outer, "keyboard", t("settings.tab_hotkeys", "Hotkeys"), ["f12", "hotkey", "convert", "clip", "case", "کلید", "میانبر"]),
            (t_excl.outer, "shield", t("settings.tab_exclusions", "Exclusions"), ["exclude", "blacklist", "app", "مستثنی"]),
            (t_prof.outer, "sliders", t("settings.tab_profiles", "App Profiles"), ["profile", "code", "chat", "formal", "app", "layout", "پروفایل", "برنامه"]),
            (t_snip.outer, "code", t("settings.tab_snippets_hub", "اسنیپت و مخزن Hub" if rtl else "Snippets & Hub"), ["snippet", "trigger", "hub", "pack", "ravaanpack", "متن", "قطعه", "بسته", "مخزن"]),
            (t_sync.outer, "cloud", t("settings.tab_sync", "Cloud Sync"), ["sync", "gist", "webdav", "همگام", "ابری"]),
            (t_ai.outer, "mic", t("settings.tab_ai_voice", "هوش مصنوعی و صدا" if rtl else "AI & Voice"), ["ai", "ollama", "openai", "gemini", "groq", "voice", "whisper", "mic", "dictation", "هوش", "صوت", "میکروفن", "مدل"]),
            (t_about.outer, "info", t("settings.tab_about", "About"), ["about", "version", "درباره"]),
        ]

        self._nav_buttons: list[tk.Button] = []
        self._nav_icon_photos = []

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
                is_act = i == active_idx
                ic = get_icon(nav_items[i][1], size=15, color=palette.highlight_fg if is_act else palette.subtext, dpi=dpi, master=self._root)
                btn.config(
                    image=ic if ic else "", bg=palette.highlight if is_act else palette.bg_surface,
                    fg=palette.highlight_fg if is_act else palette.fg,
                    activebackground=palette.accent_hover if is_act else palette.button_hover,
                    activeforeground=palette.highlight_fg if is_act else palette.fg,
                    font=get_ui_font(size=9, bold=is_act, rtl=rtl),
                )

        for idx, (tab_outer, icon_name, title, _kws) in enumerate(nav_items):
            nb.add(tab_outer, text=title)
            ic_init = get_icon(icon_name, size=15, color=palette.subtext, dpi=dpi, master=self._root)
            self._nav_icon_photos.append(ic_init)
            nav_btn = tk.Button(
                sidebar, text=f"  {title}  ", image=ic_init if ic_init else None,
                compound="right" if rtl else "left", bd=0, relief="flat", padx=12, pady=5,
                anchor="e" if rtl else "w", justify="right" if rtl else "left", cursor="hand2",
                command=lambda i=idx: _select_nav(i),
            )
            nav_btn.pack(fill="x", pady=2)
            self._nav_buttons.append(nav_btn)

        nb.bind("<<NotebookTabChanged>>", lambda _e=None: _update_nav_highlight(nb.index("current")))
        _update_nav_highlight(0)

        import ravan.ui.settings_builder as _sb
        from ravan.ui.settings_autofix import build_autofix_section
        from ravan.ui.settings_profiles import build_profiles_section

        for builder, tab_obj in (
            (_sb.build_general_section, t_gen), (_sb.build_autofix_section if hasattr(_sb, "build_autofix_section") else build_autofix_section, t_af),
            (_sb.build_prediction_section, t_pred), (_sb.build_hotkeys_section, t_hk),
            (_sb.build_exclusions_section, t_excl), (build_profiles_section, t_prof),
            (_sb.build_snippets_section, t_snip), (_sb.build_sync_section, t_sync),
            (_sb.build_ai_voice_section, t_ai),
        ):
            builder(self, tab_obj.inner, 0, pad)
        _sb.build_about_section(t_about.inner)

        for tab in tabs_list:
            tab.bind_recursive_scroll(tab.inner)

        def _filter_tabs(*_args: Any) -> None:
            q = self._search_entry.get().strip().lower() if hasattr(self, "_search_entry") else self._search_var.get().strip().lower()
            first_idx = None
            for idx, (tab_widget, _icon, title, kws) in enumerate(nav_items):
                if not q or q in title.lower() or any(q in kw for kw in kws):
                    nb.tab(tab_widget, state="normal")
                    self._nav_buttons[idx].config(state="normal")
                    if first_idx is None:
                        first_idx = idx
                else:
                    nb.tab(tab_widget, state="hidden")
                    self._nav_buttons[idx].config(state="disabled", bg=palette.bg_surface, fg=palette.subtext)
            if first_idx is not None and q:
                _select_nav(first_idx)
            elif not q:
                try:
                    _update_nav_highlight(nb.index("current"))
                except Exception:
                    pass

        self._search_var.trace_add("write", _filter_tabs)
        self._root.bind("<Control-Tab>", lambda _e: (_select_nav((nb.index("current") + 1) % len(nb.tabs())) if nb.tabs() else None) or "break")
        self._root.bind("<Control-Shift-Tab>", lambda _e: (_select_nav((nb.index("current") - 1) % len(nb.tabs())) if nb.tabs() else None) or "break")
        self._root.bind("<Escape>", lambda _: self._close())
        self._root.bind("<Control-Return>", lambda _: self._save())

    def _on_language_changed(self, _event: object = None) -> None:
        if not hasattr(self, "_ui_language_var"):
            return
        from ravan.core.i18n import set_locale
        from ravan.ui.settings_voice_panel import stop_voice_preview

        stop_voice_preview(self)
        val = self._ui_language_var.get()
        self.cfg.ui_language = "fa" if "فارسی" in val else ("en" if "English" in val else "auto")
        set_locale(self.cfg.ui_language)
        if self._root:
            self._render_ui()

    def _center(self) -> None:
        if self._root is None:
            return
        self._root.update_idletasks()
        sw, sh = self._root.winfo_screenwidth(), self._root.winfo_screenheight()
        target_w, target_h = min(940, max(780, int(sw * 0.85))), min(710, max(540, int(sh * 0.84)))
        self._root.geometry(f"{target_w}x{target_h}+{max(20, (sw - target_w) // 2)}+{max(20, (sh - target_h) // 3)}")

    def _get_current_exclusions_from_text(self) -> list[str]:
        if self._excl_text is None:
            return list(self.cfg.excluded_apps)
        return [line.strip().lower() for line in self._excl_text.get("1.0", "end").strip().splitlines() if line.strip()]

    def _detect_active_app(self) -> None:
        from ravan.core.config import is_app_excluded
        from ravan.platform.focus import active_window_info

        exe = active_window_info().get("exe")
        if not exe:
            if self._detected_app_var is not None:
                self._detected_app_var.set("Active app: could not detect")
            if self._add_detected_btn is not None:
                self._add_detected_btn.config(state="disabled")
            return
        status = "EXCLUDED" if is_app_excluded(exe, self._get_current_exclusions_from_text()) else "ACTIVE"
        self._last_detected_exe = exe
        if self._detected_app_var is not None:
            self._detected_app_var.set(f"{exe}  [{status}]")
        if self._add_detected_btn is not None:
            self._add_detected_btn.config(state="normal")

    def _add_exclusion_item(self, item: str) -> None:
        item = item.strip().lower()
        if not item or self._excl_text is None:
            return
        if item not in self._get_current_exclusions_from_text():
            text = self._excl_text.get("1.0", "end").rstrip()
            self._excl_text.delete("1.0", "end")
            self._excl_text.insert("1.0", (f"{text}\n{item}\n" if text else f"{item}\n"))
        self._detect_active_app()

    def _add_detected_to_exclusions(self) -> None:
        exe = getattr(self, "_last_detected_exe", None)
        if exe:
            self._add_exclusion_item(exe)

    def _open_window_picker(self) -> None:
        from ravan.ui.window_picker import WindowPickerWindow

        if self._root is not None:
            WindowPickerWindow(self._root, on_pick=self._add_exclusion_item).show()

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
            self._managed_snippets, on_saved=on_editor_saved, groups=getattr(self.cfg, "snippet_groups", None), parent=self._root
        )
        self._snippet_editor.show()

    def _save_then_close(self) -> None:
        try:
            self._save()
        except Exception:  # noqa: BLE001
            log.exception("Save-on-close failed; closing without saving")
        self._close()

    def flash_saved(self) -> None:
        if self._root is None or not self._root.winfo_exists():
            return
        try:
            self._saved_label.config(text="✓ " + t("settings.saved_flash", "ذخیره و اعمال شد — پنجره باز ماند"))
            if getattr(self, "_saved_flash_job", None):
                self._root.after_cancel(self._saved_flash_job)
            self._saved_flash_job = self._root.after(2500, lambda: self._saved_label.config(text=""))
        except Exception:  # noqa: BLE001
            pass

    def _close(self) -> None:
        self._open = self._built = False
        from ravan.ui.settings_voice_panel import stop_voice_preview

        stop_voice_preview(self)
        if self._saved_flash_job is not None and self._root is not None:
            try:
                self._root.after_cancel(self._saved_flash_job)
            except Exception:  # noqa: BLE001
                pass
            self._saved_flash_job = None
        if self._snippet_editor is not None:
            try:
                self._snippet_editor._close()
            except Exception:  # noqa: BLE001
                pass
            self._snippet_editor = None
        destroy_managed_toplevel(self._root, self._owned_tk_root)
        self._root = self._owned_tk_root = None

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

"""UI section builder functions for SettingsWindow (Modern Card-Based Fluent Design)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from ravan.core.config import hotkey_to_text
from ravan.core.i18n import is_rtl, t
from ravan.ui.theme import Palette, get_active_palette, get_ui_font


def _get_win_palette(win: Any) -> Palette:
    mode = getattr(getattr(win, "cfg", None), "theme_mode", "auto")
    return get_active_palette(mode)


def _make_section_banner(
    parent: ttk.Frame,
    icon: str,
    title: str,
    subtitle: str,
    palette: Palette,
    rtl: bool,
) -> tk.Frame:
    """Create a prominent section title banner at the top of a tab page."""
    banner = tk.Frame(
        parent,
        bg=palette.card_bg,
        highlightthickness=1,
        highlightbackground=palette.border,
        padx=14,
        pady=10,
    )
    anchor = "e" if rtl else "w"
    justify = "right" if rtl else "left"
    hdr_txt = f"{title}  {icon}" if rtl else f"{icon}  {title}"
    tk.Label(
        banner,
        text=hdr_txt,
        bg=palette.card_bg,
        fg=palette.fg,
        font=get_ui_font(size=12, bold=True, rtl=rtl),
        anchor=anchor,
        justify=justify,
    ).pack(fill="x", anchor=anchor)
    if subtitle:
        tk.Label(
            banner,
            text=subtitle,
            bg=palette.card_bg,
            fg=palette.subtext,
            font=get_ui_font(size=8, rtl=rtl),
            anchor=anchor,
            justify=justify,
        ).pack(fill="x", anchor=anchor, pady=(2, 0))
    return banner


def _make_card(
    parent: ttk.Frame,
    title: str,
    padding: int = 12,
) -> ttk.LabelFrame:
    """Create a grouped settings card."""
    return ttk.LabelFrame(parent, text=f"  {title}  ", padding=padding)


def _style_text_widget(text_widget: tk.Text, palette: Palette, rtl: bool = False) -> None:
    """Apply dark/light palette styling to a raw tk.Text editor."""
    text_widget.configure(
        bg=palette.input_bg,
        fg=palette.fg,
        insertbackground=palette.fg,
        selectbackground=palette.highlight,
        selectforeground=palette.highlight_fg,
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=palette.border,
        highlightcolor=palette.accent,
        padx=10,
        pady=8,
        font=get_ui_font(size=9, rtl=rtl),
    )


def _bind_live_capture(entry: ttk.Entry, var: tk.StringVar) -> None:
    def on_key(event: Any) -> str:
        if event.keysym in ("BackSpace", "Delete"):
            var.set("")
            return "break"
        if event.keysym in (
            "Control_L",
            "Control_R",
            "Alt_L",
            "Alt_R",
            "Shift_L",
            "Shift_R",
            "Win_L",
            "Win_R",
        ):
            return "break"
        mods = []
        if event.state & 0x0004:
            mods.append("Ctrl")
        if event.state & 0x20000 or event.state & 0x0008 or event.state & 0x0080:
            mods.append("Alt")
        if event.state & 0x0001:
            mods.append("Shift")
        sym = event.keysym.upper()
        key = sym
        var.set("+".join([*mods, key]))
        return "break"

    entry.bind("<KeyPress>", on_key)


def build_hotkeys_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    rtl = is_rtl()
    palette = _get_win_palette(win)
    row = start_row
    align = "e" if rtl else "w"
    frm.columnconfigure(0, weight=1)

    sub = (
        "روی هر کادر کلیک کنید و کلید ترکیبی دلخواه خود را فشار دهید (BackSpace برای پاک کردن)"
        if rtl
        else "Click any shortcut box and press your desired key combination (BackSpace to clear)"
    )
    banner = _make_section_banner(
        frm, "⌨️", t("settings.tab_hotkeys", "Hotkeys"), sub, palette, rtl
    )
    banner.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    row += 1

    card_title = "🎯 میانبرهای سراسری کیبورد" if rtl else "🎯 Global Keyboard Shortcuts"
    hk_card = _make_card(frm, card_title, padding=12)
    hk_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    hk_card.columnconfigure(0, weight=1)
    row += 1

    entries_spec = [
        (t("settings.hotkey_convert", "Convert last word:"), "_convert_var", win.cfg.convert_hotkey, "e.g. Pause"),
        (t("settings.hotkey_lang", "Show language chip:"), "_lang_var", win.cfg.lang_indicator_hotkey, "e.g. Alt+L"),
        (t("settings.hotkey_clip", "Clipboard history:"), "_clip_var", win.cfg.clipboard_history_hotkey, "e.g. Alt+V"),
        (t("settings.hotkey_norm", "Normalize text:"), "_norm_var", win.cfg.normalize_hotkey, "e.g. Ctrl+F12"),
        (t("settings.hotkey_case", "Cycle text case:"), "_case_var", win.cfg.case_hotkey, "e.g. Shift+F12"),
        (t("settings.hotkey_undo", "Undo last autocorrect:"), "_undo_var", win.cfg.undo_autocorrect_hotkey, "e.g. Ctrl+Shift+Z"),
        (t("settings.hotkey_stats", "Quick text stats:"), "_stats_var", getattr(win.cfg, "quick_stats_hotkey", None) or win.cfg.quick_stats_hotkey, "e.g. Ctrl+Alt+S"),
        (t("settings.hotkey_pause", "Pause / Resume Ravaan:"), "_pause_var", getattr(win.cfg, "pause_hotkey", None) or win.cfg.pause_hotkey, "e.g. Ctrl+Alt+Pause"),
        (t("settings.hotkey_translit", "Phonetic Finglish (Experimental):"), "_translit_hotkey_var", getattr(win.cfg, "translit_hotkey", None) or win.cfg.translit_hotkey, "e.g. Ctrl+Alt+T"),
    ]

    c_row = 0
    for label_text, var_attr, hotkey_spec, hint in entries_spec:
        ttk.Label(hk_card, text=label_text).grid(row=c_row, column=0, sticky=align, **pad)
        var = tk.StringVar(value=hotkey_to_text(hotkey_spec))
        setattr(win, var_attr, var)
        entry = ttk.Entry(hk_card, textvariable=var, width=20, justify="center")
        entry.grid(row=c_row, column=1, sticky="w", **pad)
        _bind_live_capture(entry, var)
        ttk.Label(hk_card, text=hint, style="Sub.TLabel").grid(row=c_row, column=2, sticky="w", **pad)
        c_row += 1

        if var_attr == "_convert_var":
            ttk.Label(
                hk_card,
                text=t("settings.convert_scope_label", "  ↳ Scope without selection:"),
                style="Sub.TLabel",
            ).grid(row=c_row, column=0, sticky=align, **pad)
            scope_cur = getattr(win.cfg, "convert_scope", "sentence")
            scope_var = tk.StringVar(value=scope_cur)
            win._convert_scope_var = scope_var
            scope_map = {
                t("settings.convert_scope_sentence", "Last sentence / phrase (Default)"): "sentence",
                t("settings.convert_scope_word", "Last word only"): "word",
            }
            inv_scope = {v: k for k, v in scope_map.items()}
            display_var = tk.StringVar(value=inv_scope.get(scope_cur, inv_scope["sentence"]))
            win._convert_scope_display_var = display_var

            def _on_scope_change(*_, sv=scope_var, dv=display_var, sm=scope_map):
                sv.set(sm.get(dv.get(), "sentence"))

            display_var.trace_add("write", _on_scope_change)
            scope_combo = ttk.Combobox(
                hk_card,
                textvariable=display_var,
                values=list(scope_map.keys()),
                state="readonly",
                width=26,
            )
            scope_combo.grid(row=c_row, column=1, columnspan=2, sticky="w", **pad)
            c_row += 1

    ttk.Button(
        frm,
        text=t("settings.reset_tab_btn", "↺ Reset tab defaults"),
        command=lambda: win._reset_tab_defaults("hotkeys"),
    ).grid(row=row, column=0, sticky=align, pady=(4, 4))
    row += 1
    return row


def build_general_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    from ravan.platform.protocol import is_protocol_registered
    from ravan.platform.startup import is_startup_enabled
    from ravan.ui.tooltip import ToolTip

    rtl = is_rtl()
    palette = _get_win_palette(win)
    row = start_row
    align = "e" if rtl else "w"
    frm.columnconfigure(0, weight=1)

    sub = (
        "مدیریت زبان رابط کاربری، تم ظاهری، اجرای خودکار و ابزارهای هوشمند نگارش فارسی"
        if rtl
        else "Configure interface language, visual theme, startup behavior, and smart Persian typing tools"
    )
    banner = _make_section_banner(
        frm, "⚙️", t("settings.tab_general", "General Options"), sub, palette, rtl
    )
    banner.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    row += 1

    # ── Card 1: Language, Appearance & Language Indicator ──
    card1_title = "🎨 زبان، ظاهر و نشانگر زبان کیبورد" if rtl else "🎨 Appearance, Language & Indicator"
    card1 = _make_card(frm, card1_title, padding=12)
    card1.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    card1.columnconfigure(0, weight=1)
    row += 1

    c1_r = 0
    ttk.Label(card1, text=t("settings.ui_language", "UI Language:")).grid(
        row=c1_r, column=0, sticky=align, **pad
    )
    cur_lang = getattr(win.cfg, "ui_language", "auto")
    display_lang = (
        t("settings.lang_fa", "فارسی")
        if cur_lang == "fa"
        else (t("settings.lang_en", "English") if cur_lang == "en" else t("settings.lang_auto", "Auto (follow Windows)"))
    )
    win._ui_language_var = tk.StringVar(value=display_lang)
    lang_box = ttk.Combobox(
        card1,
        textvariable=win._ui_language_var,
        values=[
            t("settings.lang_auto", "Auto (follow Windows)"),
            t("settings.lang_en", "English"),
            t("settings.lang_fa", "فارسی"),
        ],
        state="readonly",
        width=24,
    )
    lang_box.grid(row=c1_r, column=1, sticky="w", **pad)
    lang_box.bind("<<ComboboxSelected>>", win._on_language_changed)
    c1_r += 1

    ttk.Label(card1, text=t("settings.theme_mode", "Theme Mode:")).grid(
        row=c1_r, column=0, sticky=align, **pad
    )
    win._theme_mode_var = tk.StringVar(value=getattr(win.cfg, "theme_mode", "auto"))
    theme_box = ttk.Combobox(
        card1,
        textvariable=win._theme_mode_var,
        values=["auto", "dark", "light", "high_contrast"],
        state="readonly",
        width=18,
    )
    theme_box.grid(row=c1_r, column=1, sticky="w", **pad)
    c1_r += 1

    win._lang_placement_map = {
        t("settings.placement.bottom_right", "پایین راست — بالای آیکون‌های تری"): "bottom_right",
        t("settings.placement.bottom_left", "پایین چپ"): "bottom_left",
        t("settings.placement.top_right", "بالا راست"): "top_right",
        t("settings.placement.top_left", "بالا چپ"): "top_left",
        t("settings.placement.click", "در محل کلیک (کنار نشانگر)"): "click",
    }
    code_to_label = {v: k for k, v in win._lang_placement_map.items()}
    win._lang_placement_var = tk.StringVar(
        value=code_to_label.get(
            getattr(win.cfg, "lang_indicator_placement", "bottom_right"),
            next(iter(win._lang_placement_map)),
        )
    )
    ttk.Label(
        card1,
        text=t("settings.lang_indicator_placement", "جای نمایش نشانگر زبان:"),
    ).grid(row=c1_r, column=0, sticky=align, **pad)
    placement_box = ttk.Combobox(
        card1,
        textvariable=win._lang_placement_var,
        values=list(win._lang_placement_map.keys()),
        state="readonly",
        width=30,
    )
    placement_box.grid(row=c1_r, column=1, columnspan=2, sticky="w", **pad)
    placement_box.bind("<<ComboboxSelected>>", lambda _e: win.on_lang_placement_changed())
    c1_r += 1

    win._show_lang_on_click_var = tk.BooleanVar(
        value=getattr(win.cfg, "show_lang_on_click", True)
    )
    cb_lang_click = ttk.Checkbutton(
        card1,
        text=t("settings.show_lang_on_click", "Show keyboard language indicator on mouse click"),
        variable=win._show_lang_on_click_var,
    )
    cb_lang_click.grid(row=c1_r, column=0, columnspan=3, sticky=align, **pad)
    lang_click_ex = t(
        "settings.show_lang_on_click_example",
        "Example: Clicking in any text box automatically shows whether typing in FA or EN",
    )
    ToolTip(cb_lang_click, lang_click_ex)
    c1_r += 1

    # ── Card 2: System Integration & Startup ──
    card2_title = "🚀 سیستم و اجرای خودکار" if rtl else "🚀 System & Startup Integration"
    card2 = _make_card(frm, card2_title, padding=12)
    card2.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    card2.columnconfigure(0, weight=1)
    row += 1

    c2_r = 0
    win._startup_var = tk.BooleanVar(value=is_startup_enabled())
    ttk.Checkbutton(
        card2,
        text=t("settings.launch_at_startup", "Launch at Windows startup"),
        variable=win._startup_var,
    ).grid(row=c2_r, column=0, columnspan=3, sticky=align, **pad)
    c2_r += 1

    win._protocol_var = tk.BooleanVar(value=is_protocol_registered())
    ttk.Checkbutton(
        card2,
        text=t("settings.register_protocol", "Register 'ravan://' URL protocol handler"),
        variable=win._protocol_var,
    ).grid(row=c2_r, column=0, columnspan=3, sticky=align, **pad)
    c2_r += 1

    win._sound_var = tk.BooleanVar(value=win.cfg.sound_feedback_enabled)
    ttk.Checkbutton(
        card2,
        text=t("settings.sound_feedback", "Audio feedback on keyboard layout switch"),
        variable=win._sound_var,
    ).grid(row=c2_r, column=0, columnspan=3, sticky=align, **pad)
    c2_r += 1

    # ── Card 3: Smart Persian Writing & Productivity Tools ──
    card3_title = "✍️ ابزارهای هوشمند نگارش و بهره‌وری" if rtl else "✍️ Smart Persian Typing & Productivity Tools"
    card3 = _make_card(frm, card3_title, padding=12)
    card3.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    card3.columnconfigure(0, weight=1)
    row += 1

    c3_r = 0
    smart_toggles = [
        (
            "_zwnj_var",
            win.cfg.auto_zwnj_enabled,
            t("settings.auto_zwnj", "Smart Persian half-space (auto ZWNJ)"),
            t("settings.auto_zwnj_example", "Example: Automatically converts 'می روم' to 'می‌روم'"),
        ),
        (
            "_shift_space_var",
            win.cfg.shift_space_zwnj,
            t("settings.shift_space_zwnj", "Shift+Space inserts half-space (ZWNJ)"),
            t("settings.shift_space_zwnj_example", "Example: Press Shift+Space anywhere to insert half-space (‌)"),
        ),
        (
            "_punct_spacing_var",
            win.cfg.fix_punctuation_spacing,
            t("settings.fix_punctuation", "Fix spaces before punctuation"),
            t("settings.fix_punctuation_example", "Example: Fixes extra spaces before punctuation (e.g. 'سلام .' → 'سلام.')"),
        ),
        (
            "_cliphist_var",
            win.cfg.clipboard_history_enabled,
            t("settings.enable_cliphist", "Enable clipboard history (Alt+V)"),
            t("settings.enable_cliphist_example", "Example: Press Alt+V to search and paste recent clipboard items"),
        ),
        (
            "_calc_var",
            win.cfg.inline_calc_enabled,
            t("settings.enable_calc", "Inline calculator on '=' (1200*1.09=)"),
            t("settings.enable_calc_example", "Example: Type '2500*4=' to automatically replace with '10000'"),
        ),
        (
            "_hints_var",
            getattr(win.cfg, "enable_feature_hints", True),
            t("settings.enable_hints", "Show helpful feature tips (max once per feature)"),
            t("settings.enable_hints_example", "Example: Shows friendly tips max once per feature, dismissible forever"),
        ),
        (
            "_translit_var",
            getattr(win.cfg, "translit_enabled", False),
            t("settings.enable_translit", "Phonetic Finglish typing (Experimental)"),
            t("settings.enable_translit_example", "Example: Type 'salam' to convert to 'سلام' phonetically with candidates popup"),
        ),
    ]

    for attr_name, init_val, label_txt, ex_txt in smart_toggles:
        bvar = tk.BooleanVar(value=init_val)
        setattr(win, attr_name, bvar)
        cb = ttk.Checkbutton(card3, text=label_txt, variable=bvar)
        cb.grid(row=c3_r, column=0, columnspan=3, sticky=align, padx=10, pady=(4, 0))
        ToolTip(cb, ex_txt)
        c3_r += 1
        ttk.Label(
            card3,
            text=f"↳ {ex_txt}",
            style="Sub.TLabel",
        ).grid(
            row=c3_r,
            column=0,
            columnspan=3,
            sticky=align,
            padx=26,
            pady=(0, 4),
        )
        c3_r += 1

    ttk.Button(
        frm,
        text=t("settings.reset_tab_btn", "↺ Reset tab defaults"),
        command=lambda: win._reset_tab_defaults("general"),
    ).grid(row=row, column=0, sticky=align, pady=(4, 4))
    row += 1
    return row


def build_prediction_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    from ravan.core.user_dict import load_user_words

    rtl = is_rtl()
    palette = _get_win_palette(win)
    row = start_row
    align = "e" if rtl else "w"
    frm.columnconfigure(0, weight=1)

    sub = (
        "طراحی ظاهری باکس پیشنهاد، پیش‌نمایش زنده، موتور یادگیری تطبیقی و دیکشنری شخصی"
        if rtl
        else "Customize suggestion box visual style with live preview, adaptive learning, and personal vocabulary"
    )
    banner = _make_section_banner(
        frm, "🔮", t("settings.prediction_header", "Prediction & Autocorrect"), sub, palette, rtl
    )
    banner.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    row += 1

    # ── Card 1: Suggestion Box Visual Studio & Live Preview ──
    studio_title = "✨ استودیو طراحی باکس پیشنهاد و پیش‌نمایش زنده" if rtl else "✨ Suggestion Box Design Studio & Live Preview"
    studio_card = _make_card(frm, studio_title, padding=12)
    studio_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    studio_card.columnconfigure(1, weight=1)
    row += 1

    s_row = 0
    ttk.Label(
        studio_card,
        text=t("settings.prediction_ui_style", "Suggestion box design style:"),
    ).grid(row=s_row, column=0, sticky=align, **pad)
    win._prediction_ui_style_var = tk.StringVar(
        value=getattr(win.cfg, "prediction_ui_style", "macos")
    )
    style_names = [
        "macos",
        "modern",
        "compact",
        "glass",
        "classic",
        "fluent",
        "material",
        "ios",
        "minimal",
        "neon",
    ]
    ui_box = ttk.Combobox(
        studio_card,
        textvariable=win._prediction_ui_style_var,
        values=style_names,
        state="readonly",
        width=16,
    )
    ui_box.grid(row=s_row, column=1, sticky="w", **pad)
    ui_box.bind("<<ComboboxSelected>>", lambda _e: win.on_prediction_style_changed())
    s_row += 1

    # Interactive Style Gallery Pill Buttons (5x2 grid)
    gallery_frame = tk.Frame(studio_card, bg=palette.bg)
    gallery_frame.grid(row=s_row, column=0, columnspan=3, sticky="ew", padx=8, pady=(4, 8))
    s_row += 1

    style_chips_meta = [
        ("macos", "🍎 macOS"),
        ("fluent", "🪟 Fluent 11"),
        ("material", "🎨 Material"),
        ("modern", "🔮 Modern"),
        ("ios", "📱 iOS"),
        ("glass", "💎 Glass"),
        ("minimal", "⬛ Minimal"),
        ("compact", "📐 Compact"),
        ("classic", "🗔 Classic"),
        ("neon", "⚡ Neon HUD"),
    ]
    style_chip_btns: dict[str, tk.Button] = {}

    def _refresh_style_gallery() -> None:
        cur_s = win._prediction_ui_style_var.get()
        for s_key, b in style_chip_btns.items():
            if not b.winfo_exists():
                continue
            if s_key == cur_s:
                b.config(
                    bg=palette.highlight,
                    fg=palette.highlight_fg,
                    activebackground=palette.accent_hover,
                    activeforeground=palette.highlight_fg,
                    font=get_ui_font(size=8, bold=True),
                    highlightbackground=palette.accent,
                )
            else:
                b.config(
                    bg=palette.card_bg,
                    fg=palette.fg,
                    activebackground=palette.button_hover,
                    activeforeground=palette.fg,
                    font=get_ui_font(size=8, bold=False),
                    highlightbackground=palette.border,
                )

    win._refresh_style_gallery = _refresh_style_gallery

    def _pick_style_chip(s_key: str) -> None:
        win._prediction_ui_style_var.set(s_key)
        win.on_prediction_style_changed()

    for idx_s, (s_key, s_label) in enumerate(style_chips_meta):
        r_idx = idx_s // 5
        c_idx = idx_s % 5
        gallery_frame.columnconfigure(c_idx, weight=1)
        chip_btn = tk.Button(
            gallery_frame,
            text=s_label,
            bd=0,
            relief="flat",
            padx=8,
            pady=5,
            cursor="hand2",
            highlightthickness=1,
            command=lambda k=s_key: _pick_style_chip(k),
        )
        chip_btn.grid(row=r_idx, column=c_idx, sticky="ew", padx=3, pady=3)
        style_chip_btns[s_key] = chip_btn

    _refresh_style_gallery()

    # Suggestion box layout: vertical vs horizontal
    ttk.Label(
        studio_card,
        text=t("settings.prediction_layout", "چیدمان پیشنهادها:"),
    ).grid(row=s_row, column=0, sticky=align, **pad)

    layout_val = getattr(win.cfg, "prediction_layout", "vertical")
    layout_map = {
        t("settings.layout_vertical", "زیر هم (عمودی — پیش‌فرض)"): "vertical",
        t("settings.layout_horizontal", "رو‌به‌روی هم (افقی / نواری)"): "horizontal",
    }
    rev_layout_map = {v: k for k, v in layout_map.items()}

    win._prediction_layout_var = tk.StringVar(value=layout_val)
    win._prediction_layout_display_var = tk.StringVar(
        value=rev_layout_map.get(layout_val, rev_layout_map.get("vertical", "vertical"))
    )

    def _on_layout_selected(_e: object = None) -> None:
        selected_text = win._prediction_layout_display_var.get()
        chosen = layout_map.get(selected_text, "vertical")
        win._prediction_layout_var.set(chosen)
        win.on_prediction_layout_changed()

    layout_cb = ttk.Combobox(
        studio_card,
        textvariable=win._prediction_layout_display_var,
        values=list(layout_map.keys()),
        state="readonly",
        width=26,
    )
    layout_cb.grid(row=s_row, column=1, sticky="w", **pad)
    layout_cb.bind("<<ComboboxSelected>>", _on_layout_selected)
    s_row += 1

    # Live preview container (preserves win._style_preview hierarchy for tests!)
    ttk.Label(
        studio_card,
        text=t("settings.style_preview", "پیش‌نمایش زنده:"),
    ).grid(row=s_row, column=0, sticky="ne", **pad)
    win._style_preview = ttk.Frame(studio_card, relief="groove", borderwidth=1)
    win._style_preview.grid(row=s_row, column=1, columnspan=2, sticky="ew", **pad)
    win._render_style_preview()
    s_row += 1

    # Font size, opacity, and position inside Studio Card
    ttk.Label(
        studio_card,
        text=t("settings.prediction_font_size", "Suggestion font size:"),
    ).grid(row=s_row, column=0, sticky=align, **pad)
    win._prediction_font_size_var = tk.IntVar(
        value=int(getattr(win.cfg, "prediction_font_size", 12))
    )
    ttk.Spinbox(
        studio_card, from_=9, to=18, increment=1, textvariable=win._prediction_font_size_var, width=8
    ).grid(row=s_row, column=1, sticky="w", **pad)
    s_row += 1

    ttk.Label(
        studio_card,
        text=t("settings.prediction_opacity", "Suggestion box opacity (%):"),
    ).grid(row=s_row, column=0, sticky=align, **pad)
    win._prediction_opacity_var = tk.IntVar(
        value=int(float(getattr(win.cfg, "prediction_opacity", 0.95)) * 100)
    )
    ttk.Spinbox(
        studio_card, from_=60, to=100, increment=5, textvariable=win._prediction_opacity_var, width=8
    ).grid(row=s_row, column=1, sticky="w", **pad)
    s_row += 1

    win._overlay_custom_pos_var = tk.BooleanVar(
        value=getattr(win.cfg, "overlay_custom_pos", False)
    )
    ttk.Checkbutton(
        studio_card,
        text=t("settings.overlay_custom_pos", "Remember last dragged position of suggestion box"),
        variable=win._overlay_custom_pos_var,
    ).grid(row=s_row, column=0, columnspan=2, sticky=align, **pad)

    def _do_reset_overlay_pos() -> None:
        from tkinter import messagebox

        win.cfg.overlay_custom_pos = False
        win.cfg.overlay_pos_x = -1
        win.cfg.overlay_pos_y = -1
        win._overlay_custom_pos_var.set(False)
        if hasattr(win, "overlay") and win.overlay:
            win.overlay.reset_position_to_caret()
        messagebox.showinfo(
            "Ravaan",
            t("settings.overlay_reset_done", "Suggestion box position reset to typing cursor!"),
            parent=win._root,
        )

    ttk.Button(
        studio_card,
        text=t("settings.overlay_reset_pos", "↺ Reset position to typing cursor"),
        command=_do_reset_overlay_pos,
    ).grid(row=s_row, column=2, sticky="e" if not rtl else "w", padx=pad.get("padx", 10))
    s_row += 1

    # ── Card 2: Custom Color Palette Section ──
    color_card = _make_card(
        frm,
        t("settings.custom_colors_title", "🎨 سفارشی‌سازی رنگ‌بندی جعبه پیشنهاد"),
        padding=12,
    )
    color_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    row += 1

    win._prediction_use_custom_colors_var = tk.BooleanVar(
        value=getattr(win.cfg, "prediction_use_custom_colors", False)
    )
    ttk.Checkbutton(
        color_card,
        text=t(
            "settings.use_custom_colors",
            "فعال‌سازی رنگ‌بندی دلخواه (جایگزینی پالت استایل انتخابی)",
        ),
        variable=win._prediction_use_custom_colors_var,
        command=win.on_prediction_colors_changed,
    ).pack(anchor=align, padx=10, pady=(4, 6))

    swatches_frame = ttk.Frame(color_card)
    swatches_frame.pack(fill="x", padx=10, pady=(2, 8))

    color_fields = [
        ("prediction_custom_bg", t("settings.color_bg", "پس‌زمینه")),
        ("prediction_custom_fg", t("settings.color_fg", "متن")),
        ("prediction_custom_highlight", t("settings.color_highlight", "انتخاب")),
        ("prediction_custom_border", t("settings.color_border", "حاشیه")),
        ("prediction_custom_accent", t("settings.color_accent", "تأکید")),
    ]

    for field_name, label_text in color_fields:
        item_frame = ttk.Frame(swatches_frame)
        item_frame.pack(side="right" if rtl else "left", padx=10, pady=2)

        ttk.Label(item_frame, text=label_text, style="Sub.TLabel").pack(anchor="center")

        initial_color = getattr(
            win.cfg,
            field_name,
            "#202024" if "bg" in field_name else ("#F5F5F7" if "fg" in field_name else "#0A84FF"),
        )
        var = tk.StringVar(value=initial_color)
        setattr(win, f"_{field_name}_var", var)

        btn = tk.Button(
            item_frame,
            bg=initial_color,
            activebackground=initial_color,
            width=4,
            height=1,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=palette.border,
            cursor="hand2",
            command=lambda fn=field_name: win.pick_prediction_color(fn),
        )
        btn.pack(anchor="center", pady=(3, 0))
        setattr(win, f"_{field_name}_btn", btn)

    actions_frame = ttk.Frame(color_card)
    actions_frame.pack(fill="x", padx=10, pady=(2, 4))

    ttk.Label(
        actions_frame,
        text=t("settings.presets_label", "پالت‌های آماده:"),
        font=get_ui_font(size=8, bold=True, rtl=rtl),
    ).pack(side="right" if rtl else "left", padx=(0, 6))

    presets = [
        (t("settings.preset_ocean", "🌊 اقیانوسی"), ("#0D1B2A", "#E0E1DD", "#00A8E8", "#1B263B", "#00A8E8")),
        (t("settings.preset_emerald", "🌲 زمردی"), ("#132A13", "#ECF39E", "#52B788", "#31572C", "#52B788")),
        (t("settings.preset_sunset", "🌅 غروب"), ("#240046", "#E0AAFF", "#9D4EDD", "#3C096C", "#C77DFF")),
        (t("settings.preset_neon", "⚡ سایبر نئون"), ("#080410", "#00FF66", "#FF007F", "#FF007F", "#2A0820")),
        (t("settings.preset_dark", "🌙 تاریک تمیز"), ("#1E1E2E", "#CDD6F4", "#89B4FA", "#313244", "#89B4FA")),
    ]

    for p_name, p_cols in presets:
        btn_preset = ttk.Button(
            actions_frame,
            text=p_name,
            command=lambda cols=p_cols: win.apply_color_preset(*cols),
        )
        btn_preset.pack(side="right" if rtl else "left", padx=3)

    btn_reset = ttk.Button(
        actions_frame,
        text=t("settings.reset_colors_btn", "↺ بازنشانی به پالت استایل"),
        command=win.reset_prediction_colors_to_style,
    )
    btn_reset.pack(side="left" if rtl else "right", padx=(8, 0))

    # ── Card 3: Prediction & Autocorrect Behavior Engine ──
    eng_title = "🧠 موتور پیش‌بینی، اصلاح خودکار و کلیدهای انتخاب" if rtl else "🧠 Prediction, Autocorrect & Selection Behavior"
    eng_card = _make_card(frm, eng_title, padding=12)
    eng_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    eng_card.columnconfigure(0, weight=1)
    row += 1

    e_row = 0
    win._prediction_var = tk.BooleanVar(value=win.cfg.prediction_enabled)
    ttk.Checkbutton(
        eng_card,
        text=t("settings.prediction_enabled", "Enable word prediction near typing cursor"),
        variable=win._prediction_var,
    ).grid(row=e_row, column=0, columnspan=3, sticky=align, **pad)
    e_row += 1

    win._learning_enabled_var = tk.BooleanVar(value=getattr(win.cfg, "learning_enabled", True))
    ttk.Checkbutton(
        eng_card,
        text=t("settings.learning_enabled", "Enable adaptive typing learning (tracks frequent words locally)"),
        variable=win._learning_enabled_var,
    ).grid(row=e_row, column=0, columnspan=3, sticky=align, **pad)
    e_row += 1

    initial_ac_enabled = bool(win.cfg.autocorrect_enabled)
    initial_ac_mode = str(getattr(win.cfg, "autocorrect_mode", "safe")).lower()
    if not initial_ac_enabled or initial_ac_mode == "off":
        if initial_ac_mode == "off":
            initial_ac_enabled = False

    win._autocorrect_var = tk.BooleanVar(value=initial_ac_enabled)
    ttk.Checkbutton(
        eng_card,
        text=t("settings.autocorrect_enabled", "Enable autocorrect on word boundaries"),
        variable=win._autocorrect_var,
    ).grid(row=e_row, column=0, columnspan=3, sticky=align, **pad)
    e_row += 1

    ttk.Label(eng_card, text=t("settings.autocorrect_mode", "Autocorrect mode:")).grid(
        row=e_row, column=0, sticky=align, **pad
    )
    win._autocorrect_mode_var = tk.StringVar(value="safe" if initial_ac_mode == "off" else initial_ac_mode)
    mode_box = ttk.Combobox(
        eng_card,
        textvariable=win._autocorrect_mode_var,
        values=["safe", "normal", "off"],
        state="readonly" if initial_ac_enabled else "disabled",
        width=14,
    )
    mode_box.grid(row=e_row, column=1, sticky="w", **pad)
    e_row += 1

    _syncing_ac = False

    def _on_ac_var_changed(*_):
        nonlocal _syncing_ac
        if _syncing_ac:
            return
        _syncing_ac = True
        try:
            is_on = win._autocorrect_var.get()
            if is_on:
                mode_box.configure(state="readonly")
                if win._autocorrect_mode_var.get() == "off":
                    win._autocorrect_mode_var.set("safe")
            else:
                mode_box.configure(state="disabled")
        finally:
            _syncing_ac = False

    def _on_ac_mode_changed(*_):
        nonlocal _syncing_ac
        if _syncing_ac:
            return
        _syncing_ac = True
        try:
            m = win._autocorrect_mode_var.get()
            if m == "off":
                win._autocorrect_var.set(False)
                mode_box.configure(state="disabled")
            else:
                win._autocorrect_var.set(True)
                mode_box.configure(state="readonly")
        finally:
            _syncing_ac = False

    win._autocorrect_var.trace_add("write", _on_ac_var_changed)
    win._autocorrect_mode_var.trace_add("write", _on_ac_mode_changed)

    win._digits_var = tk.BooleanVar(value=win.cfg.quickpick_digits)
    ttk.Checkbutton(
        eng_card,
        text=t("settings.quickpick_digits", "Digits 1–5 quick-pick in popup"),
        variable=win._digits_var,
    ).grid(row=e_row, column=0, columnspan=3, sticky=align, **pad)
    e_row += 1

    win._prediction_auto_space_var = tk.BooleanVar(
        value=getattr(win.cfg, "prediction_auto_space", True)
    )
    ttk.Checkbutton(
        eng_card,
        text=t("settings.prediction_auto_space", "Auto-insert space after accepting suggestion"),
        variable=win._prediction_auto_space_var,
    ).grid(row=e_row, column=0, columnspan=3, sticky=align, **pad)
    e_row += 1

    win._suggestion_accept_enter_var = tk.BooleanVar(
        value=getattr(win.cfg, "suggestion_accept_enter", False)
    )
    ttk.Checkbutton(
        eng_card,
        text=t("settings.suggestion_accept_enter", "Accept suggestion on Enter (recommended: Off)"),
        variable=win._suggestion_accept_enter_var,
    ).grid(row=e_row, column=0, columnspan=3, sticky=align, **pad)
    e_row += 1

    ttk.Label(eng_card, text=t("settings.debounce_ms", "Debounce (ms):")).grid(
        row=e_row, column=0, sticky=align, **pad
    )
    win._debounce_var = tk.IntVar(value=win.cfg.prediction_debounce_ms)
    ttk.Spinbox(eng_card, from_=0, to=500, increment=10, textvariable=win._debounce_var, width=8).grid(
        row=e_row, column=1, sticky="w", **pad
    )
    e_row += 1

    ttk.Label(eng_card, text=t("settings.max_candidates", "Max suggestions:")).grid(
        row=e_row, column=0, sticky=align, **pad
    )
    win._maxcand_var = tk.IntVar(value=win.cfg.prediction_max_candidates)
    ttk.Spinbox(eng_card, from_=1, to=9, increment=1, textvariable=win._maxcand_var, width=8).grid(
        row=e_row, column=1, sticky="w", **pad
    )
    e_row += 1

    ttk.Label(eng_card, text=t("settings.min_prefix", "Min prefix length:")).grid(
        row=e_row, column=0, sticky=align, **pad
    )
    win._minlen_var = tk.IntVar(value=win.cfg.min_prefix_len)
    ttk.Spinbox(eng_card, from_=1, to=6, increment=1, textvariable=win._minlen_var, width=8).grid(
        row=e_row, column=1, sticky="w", **pad
    )
    e_row += 1

    # ── Card 4: Dictionaries, Personal Vocabulary & Privacy ──
    dict_title = "📚 واژه‌نامه‌ها، کلمات شخصی و حریم خصوصی" if rtl else "📚 Dictionaries, Personal Vocabulary & Privacy"
    dict_card = _make_card(frm, dict_title, padding=12)
    dict_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    dict_card.columnconfigure(0, weight=1)
    row += 1

    d_row = 0
    win._en_dict_var = tk.BooleanVar(value=win.cfg.english_dict_enabled)
    ttk.Checkbutton(
        dict_card, text=t("settings.en_dict", "English dictionary"), variable=win._en_dict_var
    ).grid(row=d_row, column=0, columnspan=3, sticky=align, **pad)
    d_row += 1

    win._fa_dict_var = tk.BooleanVar(value=win.cfg.persian_dict_enabled)
    ttk.Checkbutton(
        dict_card, text=t("settings.fa_dict", "Persian dictionary"), variable=win._fa_dict_var
    ).grid(row=d_row, column=0, columnspan=3, sticky=align, **pad)
    d_row += 1

    ttk.Label(
        dict_card,
        text=t("settings.custom_words_label", "Custom words / names (one per line):"),
        font=get_ui_font(size=9, bold=True, rtl=rtl),
    ).grid(row=d_row, column=0, columnspan=3, sticky=align, padx=10, pady=(6, 2))
    d_row += 1

    win._user_words_text = tk.Text(dict_card, width=48, height=4)
    _style_text_widget(win._user_words_text, palette, rtl=rtl)
    win._user_words_text.insert("1.0", "\n".join(load_user_words()))
    win._user_words_text.grid(row=d_row, column=0, columnspan=3, sticky="ew", **pad)
    d_row += 1

    data_box = ttk.Frame(dict_card)
    data_box.grid(row=d_row, column=0, columnspan=3, sticky="we", padx=10, pady=(4, 4))
    d_row += 1

    def _do_export_data() -> None:
        from tkinter import filedialog, messagebox

        from ravan.core.learning import UserLearningEngine

        dest = filedialog.asksaveasfilename(
            parent=win._root,
            title=t("settings.export_dialog_title", "Export Learned Data"),
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="ravaan_learned_data.json",
        )
        if dest:
            try:
                engine = UserLearningEngine(auto_load=True)
                engine.export_profile(target_path=dest)
                messagebox.showinfo(
                    "Ravaan",
                    t("settings.export_data_success", "Learned vocabulary and style data exported successfully!"),
                    parent=win._root,
                )
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("Ravaan", str(exc), parent=win._root)

    def _do_clear_data() -> None:
        from tkinter import messagebox

        from ravan.core.learning import UserLearningEngine

        confirmed = messagebox.askyesno(
            t("settings.clear_data_confirm_title", "Clear Learned Data"),
            t("settings.clear_data_confirm_msg", "Are you sure? All learned words and style data will be reset to factory defaults."),
            parent=win._root,
        )
        if confirmed:
            try:
                engine = UserLearningEngine(auto_load=True)
                engine.clear_learned_data()
                messagebox.showinfo(
                    "Ravaan",
                    t("settings.clear_data_success", "All learned data has been cleared successfully."),
                    parent=win._root,
                )
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("Ravaan", str(exc), parent=win._root)

    btn_pack_side = "right" if rtl else "left"
    ttk.Button(
        data_box,
        text=t("settings.btn_export_data", "💾 Export my data (.json)"),
        command=_do_export_data,
    ).pack(side=btn_pack_side, padx=(0, 6) if not rtl else (6, 0))

    ttk.Button(
        data_box,
        text=t("settings.btn_clear_data", "🗑️ Clear learned data"),
        command=_do_clear_data,
    ).pack(side=btn_pack_side, padx=(0, 6) if not rtl else (6, 0))

    ttk.Button(
        frm,
        text=t("settings.reset_tab_btn", "↺ Reset tab defaults"),
        command=lambda: win._reset_tab_defaults("prediction"),
    ).grid(row=row, column=0, sticky=align, pady=(4, 4))
    row += 1
    return row


def build_exclusions_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    rtl = is_rtl()
    palette = _get_win_palette(win)
    row = start_row
    align = "e" if rtl else "w"
    frm.columnconfigure(0, weight=1)

    sub = (
        "برنامه‌هایی که نمی‌خواهید «روان» در آن‌ها فعال باشد (مانند بازی‌ها یا محیط‌های خاص) را اضافه کنید"
        if rtl
        else "Specify applications where Ravaan should stay inactive (e.g. games, remote desktop, terminals)"
    )
    banner = _make_section_banner(
        frm, "🚫", t("settings.tab_exclusions", "Excluded Apps"), sub, palette, rtl
    )
    banner.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    row += 1

    excl_card = _make_card(frm, t("settings.excl_header", "Excluded apps (one per line)"), padding=12)
    excl_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    excl_card.columnconfigure(0, weight=1)
    row += 1

    win._excl_text = tk.Text(excl_card, width=48, height=6)
    _style_text_widget(win._excl_text, palette, rtl=False)
    win._excl_text.insert("1.0", "\n".join(win.cfg.excluded_apps))
    win._excl_text.grid(row=0, column=0, columnspan=3, sticky="ew", **pad)

    excl_tools = ttk.Frame(excl_card)
    excl_tools.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=(6, 4))

    pack_side = "right" if rtl else "left"
    win._detected_app_var = tk.StringVar(value=t("settings.active_app", "Active app: {app}", app="—"))
    ttk.Label(excl_tools, textvariable=win._detected_app_var, style="Sub.TLabel").pack(
        side=pack_side, padx=(8, 0) if rtl else (0, 8)
    )
    ttk.Button(
        excl_tools,
        text=t("settings.detect_active_app", "Detect Active App"),
        command=win._detect_active_app,
    ).pack(side=pack_side, padx=3)
    win._add_detected_btn = ttk.Button(
        excl_tools,
        text=t("settings.add_to_exclusions", "+ Add to Exclusions"),
        command=win._add_detected_to_exclusions,
        state="disabled",
    )
    win._add_detected_btn.pack(side=pack_side, padx=3)
    ttk.Button(
        excl_tools,
        text=t("settings.btn_pick_window", "Pick Window…"),
        command=win._open_window_picker,
    ).pack(side=pack_side, padx=3)

    ttk.Button(
        frm,
        text=t("settings.reset_tab_btn", "↺ Reset tab defaults"),
        command=lambda: win._reset_tab_defaults("exclusions"),
    ).grid(row=row, column=0, sticky=align, pady=(4, 4))
    row += 1
    return row


def build_snippets_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    rtl = is_rtl()
    palette = _get_win_palette(win)
    row = start_row
    align = "e" if rtl else "w"
    pack_side = "right" if rtl else "left"
    frm.columnconfigure(0, weight=1)

    sub = (
        "میانبرهای متنی و ماکروهای پویا (مانند ;date و ;mail) را مدیریت و دسته‌بندی کنید"
        if rtl
        else "Create and organize text expansion triggers, dynamic macros, and application-specific snippet groups"
    )
    banner = _make_section_banner(
        frm, "📝", t("settings.snippets_header", "Snippets"), sub, palette, rtl
    )
    banner.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    row += 1

    snip_card = _make_card(frm, t("settings.snippets_header", "Snippets"), padding=12)
    snip_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    snip_card.columnconfigure(0, weight=1)
    row += 1

    snip_hdr = ttk.Frame(snip_card)
    snip_hdr.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 6))
    ttk.Button(
        snip_hdr,
        text=t("settings.snippets_editor_btn", "Open Snippet Editor…"),
        style="Accent.TButton",
        command=win._open_snippet_editor,
    ).pack(side=pack_side, padx=(6, 0) if rtl else (0, 6))

    def _import_pkg() -> None:
        from ravan.ui.package_dialog import open_package_import_dialog

        def _on_pkg_imported(snips: list[Any], grps: list[Any]) -> None:
            win._managed_snippets = snips
            if grps:
                win.cfg.snippet_groups = grps
            win._update_snip_display()

        open_package_import_dialog(frm, win._managed_snippets, win.cfg.snippet_groups, _on_pkg_imported)

    ttk.Button(
        snip_hdr,
        text=t("packages.import_btn", "📦 Import Package…"),
        command=_import_pkg,
    ).pack(side=pack_side, padx=4)

    win._snip_text = tk.Text(snip_card, width=48, height=6)
    _style_text_widget(win._snip_text, palette, rtl=rtl)
    win._update_snip_display()
    win._snip_text.grid(row=1, column=0, columnspan=3, sticky="ew", **pad)

    from ravan.ui.snippet_groups_ui import build_groups_manager_frame

    def _on_groups_changed(groups: list[Any]) -> None:
        from ravan.core.config import save_config

        win.cfg.snippet_groups = groups
        save_config(win.cfg)

    grp_frm = build_groups_manager_frame(frm, win.cfg, _on_groups_changed)
    grp_frm.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    row += 1

    ttk.Button(
        frm,
        text=t("settings.reset_tab_btn", "↺ Reset tab defaults"),
        command=lambda: win._reset_tab_defaults("snippets"),
    ).grid(row=row, column=0, sticky=align, pady=(4, 4))
    row += 1
    return row


def build_sync_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    """Delegate to ravan.ui.settings_sync."""
    from ravan.ui.settings_sync import build_sync_section as _build_sync

    return _build_sync(win, frm, start_row, pad)


def build_about_section(frm: ttk.Frame) -> None:
    from ravan import __version__

    rtl = is_rtl()
    palette = get_active_palette("auto")
    anchor = "e" if rtl else "w"
    justify = "right" if rtl else "left"

    hero = _make_section_banner(
        frm,
        "🪶",
        t("settings.about_title", "Ravaan (روان)"),
        t("settings.about_subtitle", "Windows typing assistant for bilingual Persian/English typists"),
        palette,
        rtl,
    )
    hero.pack(fill="x", pady=(0, 10))

    info_card = _make_card(frm, "ℹ️ مشخصات و حریم خصوصی" if rtl else "ℹ️ Version & Privacy Guarantee", padding=12)
    info_card.pack(fill="x", pady=(0, 10))

    ttk.Label(
        info_card,
        text=t("settings.about_version", "Version {version} — MIT License", version=__version__),
        font=get_ui_font(size=9, bold=True, rtl=rtl),
    ).pack(anchor=anchor, pady=(0, 4))
    ttk.Label(
        info_card,
        text=t("settings.about_github", "GitHub: https://github.com/mohsen-niksirat/Ravaan"),
        foreground=palette.accent,
    ).pack(anchor=anchor, pady=(0, 4))
    ttk.Label(
        info_card,
        text=t("settings.about_data_privacy", "Data & Privacy: 100% local-first, DPAPI-encrypted (see DATA.md)"),
        foreground=palette.success,
    ).pack(anchor=anchor, pady=(0, 4))

    feat_card = _make_card(frm, "✨ قابلیت‌های کلیدی" if rtl else "✨ Key Capabilities", padding=12)
    feat_card.pack(fill="x", pady=(0, 6))

    features_text = t(
        "settings.about_features",
        "Key Features:\n• Layout Conversion (Pause)\n• Word Prediction & Autocorrect\n• Smart Half-Space (ZWNJ)\n• Clipboard History (Alt+V)\n• Quick Text Stats (Ctrl+Alt+S)\n• Math & Jalali Macros\n• Snippets 2.0 & Cloud Sync\n• Data Manifest & Zero Telemetry",
    )
    ttk.Label(feat_card, text=features_text, justify=justify).pack(anchor=anchor, pady=2)

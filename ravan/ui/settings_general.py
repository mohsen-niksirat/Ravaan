"""General and Hotkeys tab builders for SettingsWindow using Fluent 2 widgets."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from ravan.core.config import hotkey_to_text
from ravan.core.i18n import is_rtl, t
from ravan.ui.theme import Palette, get_active_palette
from ravan.ui.widgets import (
    FluentCard,
    FluentPillButton,
    FluentSectionBanner,
    FluentToggleSwitch,
)


def _get_win_palette(win: Any) -> Palette:
    mode = getattr(getattr(win, "cfg", None), "theme_mode", "auto")
    return get_active_palette(mode)


def _bind_live_capture(entry: tk.Widget, var: tk.StringVar) -> None:
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
        var.set("+".join([*mods, sym]))
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
    banner = FluentSectionBanner(
        frm, "keyboard", t("settings.tab_hotkeys", "Hotkeys"), sub, palette, rtl
    )
    banner.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    row += 1

    card_title = "🎯 میانبرهای سراسری کیبورد" if rtl else "🎯 Global Keyboard Shortcuts"
    hk_card = FluentCard(frm, card_title, padding=12, palette=palette, rtl=rtl, icon="keyboard")
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
        ttk.Label(hk_card, text=label_text, style="Card.TLabel").grid(row=c_row, column=0, sticky=align, **pad)
        var = tk.StringVar(value=hotkey_to_text(hotkey_spec))
        setattr(win, var_attr, var)
        entry = ttk.Entry(hk_card, textvariable=var, width=20, justify="center")
        entry.grid(row=c_row, column=1, sticky="w", **pad)
        _bind_live_capture(entry, var)
        ttk.Label(hk_card, text=hint, style="CardSub.TLabel").grid(row=c_row, column=2, sticky="w", **pad)
        c_row += 1

        if var_attr == "_convert_var":
            ttk.Label(
                hk_card,
                text=t("settings.convert_scope_label", "  ↳ Scope without selection:"),
                style="CardSub.TLabel",
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

    FluentPillButton(
        frm,
        text=t("settings.reset_tab_btn", "Reset tab defaults"),
        icon="reset",
        variant="secondary",
        palette=palette,
        rtl=rtl,
        parent_bg=palette.bg_base,
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
    banner = FluentSectionBanner(
        frm, "settings", t("settings.tab_general", "General Options"), sub, palette, rtl
    )
    banner.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    row += 1

    # ── Card 1: Language, Appearance & Language Indicator ──
    card1_title = "🎨 زبان، ظاهر و نشانگر زبان کیبورد" if rtl else "🎨 Appearance, Language & Indicator"
    card1 = FluentCard(frm, card1_title, padding=12, palette=palette, rtl=rtl, icon="palette")
    card1.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    lbl_col = 1 if rtl else 0
    ctrl_col = 0 if rtl else 1
    ctrl_sticky = "w" if rtl else "e"
    card1.columnconfigure(lbl_col, weight=1)
    card1.columnconfigure(ctrl_col, weight=0)
    row += 1

    c1_r = 0
    ttk.Label(card1, text=t("settings.ui_language", "UI Language:"), style="Card.TLabel").grid(
        row=c1_r, column=lbl_col, sticky=align, **pad
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
        width=34,
    )
    lang_box.grid(row=c1_r, column=ctrl_col, sticky=ctrl_sticky, **pad)
    lang_box.bind("<<ComboboxSelected>>", win._on_language_changed)
    c1_r += 1

    ttk.Label(card1, text=t("settings.theme_mode", "Theme Mode:"), style="Card.TLabel").grid(
        row=c1_r, column=lbl_col, sticky=align, **pad
    )
    win._theme_mode_var = tk.StringVar(value=getattr(win.cfg, "theme_mode", "auto"))
    theme_box = ttk.Combobox(
        card1,
        textvariable=win._theme_mode_var,
        values=["auto", "dark", "light", "high_contrast"],
        state="readonly",
        width=34,
    )
    theme_box.grid(row=c1_r, column=ctrl_col, sticky=ctrl_sticky, **pad)
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
        style="Card.TLabel",
    ).grid(row=c1_r, column=lbl_col, sticky=align, **pad)
    placement_box = ttk.Combobox(
        card1,
        textvariable=win._lang_placement_var,
        values=list(win._lang_placement_map.keys()),
        state="readonly",
        width=34,
    )
    placement_box.grid(row=c1_r, column=ctrl_col, sticky=ctrl_sticky, **pad)
    placement_box.bind("<<ComboboxSelected>>", lambda _e: win.on_lang_placement_changed())
    c1_r += 1

    win._show_lang_on_click_var = tk.BooleanVar(
        value=getattr(win.cfg, "show_lang_on_click", True)
    )
    lang_click_ex = t(
        "settings.show_lang_on_click_example",
        "Example: Clicking in any text box automatically shows whether typing in FA or EN",
    )
    sw_lang_click = FluentToggleSwitch(
        card1,
        text=t("settings.show_lang_on_click", "Show keyboard language indicator on mouse click"),
        variable=win._show_lang_on_click_var,
        palette=palette,
        rtl=rtl,
    )
    sw_lang_click.grid(row=c1_r, column=0, columnspan=3, sticky="ew", padx=10, pady=4)
    ToolTip(sw_lang_click, lang_click_ex)
    c1_r += 1

    # ── Card 2: System Integration & Startup ──
    card2_title = "🚀 سیستم و اجرای خودکار" if rtl else "🚀 System & Startup Integration"
    card2 = FluentCard(frm, card2_title, padding=12, palette=palette, rtl=rtl, icon="settings")
    card2.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    card2.columnconfigure(0, weight=1)
    row += 1

    c2_r = 0
    win._startup_var = tk.BooleanVar(value=is_startup_enabled())
    FluentToggleSwitch(
        card2,
        text=t("settings.launch_at_startup", "Launch at Windows startup"),
        variable=win._startup_var,
        palette=palette,
        rtl=rtl,
    ).grid(row=c2_r, column=0, columnspan=3, sticky="ew", padx=10, pady=4)
    c2_r += 1

    win._protocol_var = tk.BooleanVar(value=is_protocol_registered())
    FluentToggleSwitch(
        card2,
        text=t("settings.register_protocol", "Register 'ravan://' URL protocol handler"),
        variable=win._protocol_var,
        palette=palette,
        rtl=rtl,
    ).grid(row=c2_r, column=0, columnspan=3, sticky="ew", padx=10, pady=4)
    c2_r += 1

    win._sound_var = tk.BooleanVar(value=win.cfg.sound_feedback_enabled)
    FluentToggleSwitch(
        card2,
        text=t("settings.sound_feedback", "Audio feedback on keyboard layout switch"),
        variable=win._sound_var,
        palette=palette,
        rtl=rtl,
    ).grid(row=c2_r, column=0, columnspan=3, sticky="ew", padx=10, pady=4)
    c2_r += 1

    # ── Card 3: Smart Persian Writing & Productivity Tools ──
    card3_title = "✍️ ابزارهای هوشمند نگارش و بهره‌وری" if rtl else "✍️ Smart Persian Typing & Productivity Tools"
    card3 = FluentCard(frm, card3_title, padding=12, palette=palette, rtl=rtl, icon="feather")
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
        (
            "_orthography_guard_var",
            getattr(win.cfg, "orthography_guard_enabled", True),
            t("settings.enable_orthography_guard", "Real-time Persian Orthography Guard"),
            t("settings.enable_orthography_guard_example", "Example: Fixes 'انشاالله' → 'ان‌شاءالله', 'حتما' → 'حتماً', 'گفتگو' → 'گفت‌وگو'"),
        ),
        (
            "_quick_undo_chip_var",
            getattr(win.cfg, "quick_undo_chip_enabled", True),
            t("settings.enable_quick_undo_chip", "Show Quick-Undo chip with auto-exception learn"),
            t("settings.enable_quick_undo_chip_example", "Example: Revert auto-ZWNJ/orthography in 1 click and never re-fix that word"),
        ),
        (
            "_selection_toolbar_var",
            getattr(win.cfg, "selection_toolbar_enabled", True),
            t("settings.enable_selection_toolbar", "Floating mini-toolbar on selected text"),
            t("settings.enable_selection_toolbar_example", "Example: Quick buttons to convert layout, polish Persian, or toggle digits near selection"),
        ),
    ]

    for attr_name, init_val, label_txt, ex_txt in smart_toggles:
        bvar = tk.BooleanVar(value=init_val)
        setattr(win, attr_name, bvar)
        sw = FluentToggleSwitch(
            card3,
            text=label_txt,
            subtitle=f"↳ {ex_txt}",
            variable=bvar,
            palette=palette,
            rtl=rtl,
        )
        sw.grid(row=c3_r, column=0, columnspan=3, sticky="ew", padx=10, pady=3)
        ToolTip(sw, ex_txt)
        c3_r += 1

    ortho_row = tk.Frame(card3, bg=palette.bg_surface)
    ortho_row.grid(row=c3_r, column=0, columnspan=3, sticky=align, padx=10, pady=(6, 2))
    ttk.Label(
        ortho_row,
        text=t("settings.orthography_mode_label", "Orthography Guard strictness:"),
        style="Card.TLabel",
    ).pack(side="right" if rtl else "left", padx=(0, 8) if not rtl else (8, 0))
    win._orthography_mode_var = tk.StringVar(
        value=getattr(win.cfg, "orthography_guard_mode", "safe")
    )
    ttk.Combobox(
        ortho_row,
        textvariable=win._orthography_mode_var,
        values=["safe", "strict", "off"],
        state="readonly",
        width=12,
    ).pack(side="right" if rtl else "left")
    c3_r += 1

    FluentPillButton(
        frm,
        text=t("settings.reset_tab_btn", "Reset tab defaults"),
        icon="reset",
        variant="secondary",
        palette=palette,
        rtl=rtl,
        parent_bg=palette.bg_base,
        command=lambda: win._reset_tab_defaults("general"),
    ).grid(row=row, column=0, sticky=align, pady=(4, 4))
    row += 1
    return row

"""Prediction & Style Studio tab builder for SettingsWindow using Fluent 2 widgets."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from ravan.core.i18n import is_rtl, t
from ravan.ui.settings_general import _get_win_palette
from ravan.ui.theme import Palette, get_ui_font
from ravan.ui.widgets import FluentCard, FluentPillButton, FluentSectionBanner, FluentToggleSwitch


def _style_text_widget(text_widget: tk.Text, palette: Palette, rtl: bool = False) -> None:
    """Apply dark/light palette styling to a raw tk.Text editor."""
    text_widget.configure(
        bg=palette.bg_interactive, fg=palette.fg, insertbackground=palette.fg,
        selectbackground=palette.highlight, selectforeground=palette.highlight_fg,
        relief="flat", bd=0, highlightthickness=1, highlightbackground=palette.border_subtle,
        highlightcolor=palette.border_focus, padx=10, pady=8, font=get_ui_font(size=9, rtl=rtl),
    )


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
    FluentSectionBanner(frm, "sparkle", t("settings.prediction_header", "Prediction & Autocorrect"), sub, palette, rtl).grid(
        row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8)
    )
    row += 1

    # ── Card 1: Suggestion Box Visual Studio & Live Preview ──
    studio_title = "✨ استودیو طراحی باکس پیشنهاد و پیش‌نمایش زنده" if rtl else "✨ Suggestion Box Design Studio & Live Preview"
    studio_card = FluentCard(frm, studio_title, padding=12, palette=palette, rtl=rtl, icon="sparkle")
    studio_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    studio_card.columnconfigure(1, weight=1)
    row += 1

    s_row = 0
    ttk.Label(studio_card, text=t("settings.prediction_ui_style", "Suggestion box design style:"), style="Card.TLabel").grid(
        row=s_row, column=0, sticky=align, **pad
    )
    win._prediction_ui_style_var = tk.StringVar(value=getattr(win.cfg, "prediction_ui_style", "macos"))
    style_names = ["macos", "modern", "compact", "glass", "classic", "fluent", "material", "ios", "minimal", "neon"]
    ui_box = ttk.Combobox(studio_card, textvariable=win._prediction_ui_style_var, values=style_names, state="readonly", width=22)
    ui_box.grid(row=s_row, column=1, sticky="w", **pad)
    ui_box.bind("<<ComboboxSelected>>", lambda _e: win.on_prediction_style_changed())
    s_row += 1

    gallery_frame = tk.Frame(studio_card, bg=palette.bg_surface)
    gallery_frame.grid(row=s_row, column=0, columnspan=3, sticky="ew", padx=8, pady=(4, 8))
    s_row += 1

    style_chips_meta = [
        ("macos", "macOS"), ("fluent", "Fluent 11"), ("material", "Material"), ("modern", "Modern"), ("ios", "iOS"),
        ("glass", "Glass"), ("minimal", "Minimal"), ("compact", "Compact"), ("classic", "Classic"), ("neon", "Neon HUD"),
    ]
    style_chip_btns: dict[str, FluentPillButton] = {}

    def _refresh_style_gallery() -> None:
        cur_s = win._prediction_ui_style_var.get()
        for s_key, b in style_chip_btns.items():
            if b.winfo_exists():
                b.configure(variant="primary" if s_key == cur_s else "secondary")

    win._refresh_style_gallery = _refresh_style_gallery

    def _pick_style_chip(s_key: str) -> None:
        win._prediction_ui_style_var.set(s_key)
        win.on_prediction_style_changed()

    for idx_s, (s_key, s_label) in enumerate(style_chips_meta):
        r_idx, c_idx = idx_s // 5, idx_s % 5
        gallery_frame.columnconfigure(c_idx, weight=1)
        chip_btn = FluentPillButton(
            gallery_frame, text=s_label,
            variant="primary" if s_key == win._prediction_ui_style_var.get() else "secondary",
            palette=palette, parent_bg=palette.bg_surface, height=28,
            command=lambda k=s_key: _pick_style_chip(k),
        )
        chip_btn.grid(row=r_idx, column=c_idx, sticky="ew", padx=3, pady=3)
        style_chip_btns[s_key] = chip_btn

    ttk.Label(studio_card, text=t("settings.prediction_layout", "چیدمان پیشنهادها:"), style="Card.TLabel").grid(
        row=s_row, column=0, sticky=align, **pad
    )
    layout_val = getattr(win.cfg, "prediction_layout", "vertical")
    layout_map = {
        t("settings.layout_vertical", "زیر هم (عمودی — پیش‌فرض)"): "vertical",
        t("settings.layout_horizontal", "رو‌به‌روی هم (افقی / نواری)"): "horizontal",
    }
    rev_layout_map = {v: k for k, v in layout_map.items()}
    win._prediction_layout_var = tk.StringVar(value=layout_val)
    win._prediction_layout_display_var = tk.StringVar(value=rev_layout_map.get(layout_val, rev_layout_map.get("vertical", "vertical")))

    def _on_layout_selected(_e: object = None) -> None:
        win._prediction_layout_var.set(layout_map.get(win._prediction_layout_display_var.get(), "vertical"))
        win.on_prediction_layout_changed()

    layout_cb = ttk.Combobox(studio_card, textvariable=win._prediction_layout_display_var, values=list(layout_map.keys()), state="readonly", width=32)
    layout_cb.grid(row=s_row, column=1, sticky="w", **pad)
    layout_cb.bind("<<ComboboxSelected>>", _on_layout_selected)
    s_row += 1

    ttk.Label(studio_card, text=t("settings.style_preview", "پیش‌نمایش زنده:"), style="Card.TLabel").grid(row=s_row, column=0, sticky="ne", **pad)
    win._style_preview = ttk.Frame(studio_card, relief="flat", borderwidth=0)
    win._style_preview.grid(row=s_row, column=1, columnspan=2, sticky="ew", **pad)
    win._render_style_preview()
    s_row += 1

    ttk.Label(studio_card, text=t("settings.prediction_font_size", "Suggestion font size:"), style="Card.TLabel").grid(row=s_row, column=0, sticky=align, **pad)
    win._prediction_font_size_var = tk.IntVar(value=int(getattr(win.cfg, "prediction_font_size", 12)))
    ttk.Spinbox(studio_card, from_=9, to=18, increment=1, textvariable=win._prediction_font_size_var, width=8).grid(row=s_row, column=1, sticky="w", **pad)
    s_row += 1

    ttk.Label(studio_card, text=t("settings.prediction_opacity", "Suggestion box opacity (%):"), style="Card.TLabel").grid(row=s_row, column=0, sticky=align, **pad)
    win._prediction_opacity_var = tk.IntVar(value=int(float(getattr(win.cfg, "prediction_opacity", 0.95)) * 100))
    ttk.Spinbox(studio_card, from_=60, to=100, increment=5, textvariable=win._prediction_opacity_var, width=8).grid(row=s_row, column=1, sticky="w", **pad)
    s_row += 1

    win._overlay_custom_pos_var = tk.BooleanVar(value=getattr(win.cfg, "overlay_custom_pos", False))
    FluentToggleSwitch(
        studio_card, text=t("settings.overlay_custom_pos", "Remember last dragged position of suggestion box"),
        variable=win._overlay_custom_pos_var, palette=palette, rtl=rtl,
    ).grid(row=s_row, column=0, columnspan=2, sticky="ew", padx=10, pady=4)

    def _do_reset_overlay_pos() -> None:
        from tkinter import messagebox

        win.cfg.overlay_custom_pos = False
        win.cfg.overlay_pos_x = -1
        win.cfg.overlay_pos_y = -1
        win._overlay_custom_pos_var.set(False)
        if hasattr(win, "overlay") and win.overlay:
            win.overlay.reset_position_to_caret()
        messagebox.showinfo("Ravaan", t("settings.overlay_reset_done", "Suggestion box position reset to typing cursor!"), parent=win._root)

    FluentPillButton(
        studio_card, text=t("settings.overlay_reset_pos", "Reset position to typing cursor"),
        icon="reset", variant="secondary", palette=palette, rtl=rtl, command=_do_reset_overlay_pos,
    ).grid(row=s_row, column=2, sticky="e" if not rtl else "w", padx=pad.get("padx", 10))
    s_row += 1

    # ── Card 2: Custom Color Palette Section ──
    color_card = FluentCard(frm, t("settings.custom_colors_title", "🎨 سفارشی‌سازی رنگ‌بندی جعبه پیشنهاد"), padding=12, palette=palette, rtl=rtl, icon="palette")
    color_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    row += 1

    win._prediction_use_custom_colors_var = tk.BooleanVar(value=getattr(win.cfg, "prediction_use_custom_colors", False))
    FluentToggleSwitch(
        color_card, text=t("settings.use_custom_colors", "فعال‌سازی رنگ‌بندی دلخواه (جایگزینی پالت استایل انتخابی)"),
        variable=win._prediction_use_custom_colors_var, command=win.on_prediction_colors_changed, palette=palette, rtl=rtl,
    ).pack(fill="x", padx=10, pady=(4, 6))

    swatches_frame = tk.Frame(color_card, bg=palette.bg_surface)
    swatches_frame.pack(fill="x", padx=10, pady=(2, 8))

    color_fields = [
        ("prediction_custom_bg", t("settings.color_bg", "پس‌زمینه")),
        ("prediction_custom_fg", t("settings.color_fg", "متن")),
        ("prediction_custom_highlight", t("settings.color_highlight", "انتخاب")),
        ("prediction_custom_border", t("settings.color_border", "حاشیه")),
        ("prediction_custom_accent", t("settings.color_accent", "تأکید")),
    ]
    for field_name, label_text in color_fields:
        item_frame = tk.Frame(swatches_frame, bg=palette.bg_surface)
        item_frame.pack(side="right" if rtl else "left", padx=10, pady=2)
        ttk.Label(item_frame, text=label_text, style="CardSub.TLabel").pack(anchor="center")
        initial_color = getattr(win.cfg, field_name, "#202024" if "bg" in field_name else ("#F5F5F7" if "fg" in field_name else "#0A84FF"))
        setattr(win, f"_{field_name}_var", tk.StringVar(value=initial_color))
        btn = tk.Button(
            item_frame, bg=initial_color, activebackground=initial_color, width=4, height=1,
            relief="flat", bd=0, highlightthickness=1, highlightbackground=palette.border_subtle,
            cursor="hand2", command=lambda fn=field_name: win.pick_prediction_color(fn),
        )
        btn.pack(anchor="center", pady=(3, 0))
        setattr(win, f"_{field_name}_btn", btn)

    actions_frame = tk.Frame(color_card, bg=palette.bg_surface)
    actions_frame.pack(fill="x", padx=10, pady=(2, 4))
    ttk.Label(actions_frame, text=t("settings.presets_label", "پالت‌های آماده:"), style="Card.TLabel", font=get_ui_font(size=8, bold=True, rtl=rtl)).pack(side="right" if rtl else "left", padx=(0, 6))

    presets = [
        (t("settings.preset_ocean", "اقیانوسی"), ("#0D1B2A", "#E0E1DD", "#00A8E8", "#1B263B", "#00A8E8")),
        (t("settings.preset_emerald", "زمردی"), ("#132A13", "#ECF39E", "#52B788", "#31572C", "#52B788")),
        (t("settings.preset_sunset", "غروب"), ("#240046", "#E0AAFF", "#9D4EDD", "#3C096C", "#C77DFF")),
        (t("settings.preset_neon", "سایبر نئون"), ("#080410", "#00FF66", "#FF007F", "#FF007F", "#2A0820")),
        (t("settings.preset_dark", "تاریک تمیز"), ("#1E1E2E", "#CDD6F4", "#89B4FA", "#313244", "#89B4FA")),
    ]
    for p_name, p_cols in presets:
        FluentPillButton(actions_frame, text=p_name, variant="secondary", palette=palette, rtl=rtl, height=26, command=lambda cols=p_cols: win.apply_color_preset(*cols)).pack(side="right" if rtl else "left", padx=3)

    FluentPillButton(
        actions_frame, text=t("settings.reset_colors_btn", "بازنشانی به پالت استایل"),
        icon="reset", variant="ghost", palette=palette, rtl=rtl, height=26, command=win.reset_prediction_colors_to_style,
    ).pack(side="left" if rtl else "right", padx=(8, 0))

    # ── Card 3: Prediction & Autocorrect Behavior Engine ──
    eng_title = "🧠 موتور پیش‌بینی، اصلاح خودکار و کلیدهای انتخاب" if rtl else "🧠 Prediction, Autocorrect & Selection Behavior"
    eng_card = FluentCard(frm, eng_title, padding=12, palette=palette, rtl=rtl, icon="sliders")
    eng_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    eng_card.columnconfigure(0, weight=1)
    row += 1

    e_row = 0
    win._prediction_var = tk.BooleanVar(value=win.cfg.prediction_enabled)
    FluentToggleSwitch(eng_card, text=t("settings.prediction_enabled", "Enable word prediction near typing cursor"), variable=win._prediction_var, palette=palette, rtl=rtl).grid(row=e_row, column=0, columnspan=3, sticky="ew", padx=10, pady=3)
    e_row += 1

    win._learning_enabled_var = tk.BooleanVar(value=getattr(win.cfg, "learning_enabled", True))
    FluentToggleSwitch(eng_card, text=t("settings.learning_enabled", "Enable adaptive typing learning (tracks frequent words locally)"), variable=win._learning_enabled_var, palette=palette, rtl=rtl).grid(row=e_row, column=0, columnspan=3, sticky="ew", padx=10, pady=3)
    e_row += 1

    initial_ac_mode = str(getattr(win.cfg, "autocorrect_mode", "safe")).lower()
    initial_ac_enabled = bool(win.cfg.autocorrect_enabled) and initial_ac_mode != "off"
    win._autocorrect_var = tk.BooleanVar(value=initial_ac_enabled)
    FluentToggleSwitch(eng_card, text=t("settings.autocorrect_enabled", "Enable autocorrect on word boundaries"), variable=win._autocorrect_var, palette=palette, rtl=rtl).grid(row=e_row, column=0, columnspan=3, sticky="ew", padx=10, pady=3)
    e_row += 1

    ttk.Label(eng_card, text=t("settings.autocorrect_mode", "Autocorrect mode:"), style="Card.TLabel").grid(row=e_row, column=0, sticky=align, **pad)
    win._autocorrect_mode_var = tk.StringVar(value="safe" if initial_ac_mode == "off" else initial_ac_mode)
    mode_box = ttk.Combobox(eng_card, textvariable=win._autocorrect_mode_var, values=["safe", "normal", "off"], state="readonly" if initial_ac_enabled else "disabled", width=14)
    mode_box.grid(row=e_row, column=1, sticky="w", **pad)
    e_row += 1

    _syncing_ac = False

    def _on_ac_var_changed(*_):
        nonlocal _syncing_ac
        if _syncing_ac:
            return
        _syncing_ac = True
        try:
            if win._autocorrect_var.get():
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
            is_off = win._autocorrect_mode_var.get() == "off"
            win._autocorrect_var.set(not is_off)
            mode_box.configure(state="disabled" if is_off else "readonly")
        finally:
            _syncing_ac = False

    win._autocorrect_var.trace_add("write", _on_ac_var_changed)
    win._autocorrect_mode_var.trace_add("write", _on_ac_mode_changed)

    for attr_name, init_val, label_key, label_def in (
        ("_digits_var", win.cfg.quickpick_digits, "settings.quickpick_digits", "Digits 1–5 quick-pick in popup"),
        ("_prediction_auto_space_var", getattr(win.cfg, "prediction_auto_space", True), "settings.prediction_auto_space", "Auto-insert space after accepting suggestion"),
        ("_suggestion_accept_enter_var", getattr(win.cfg, "suggestion_accept_enter", False), "settings.suggestion_accept_enter", "Accept suggestion on Enter (recommended: Off)"),
    ):
        bv = tk.BooleanVar(value=init_val)
        setattr(win, attr_name, bv)
        FluentToggleSwitch(eng_card, text=t(label_key, label_def), variable=bv, palette=palette, rtl=rtl).grid(row=e_row, column=0, columnspan=3, sticky="ew", padx=10, pady=3)
        e_row += 1

    for attr_name, init_val, label_key, label_def, f_from, f_to, f_inc in (
        ("_debounce_var", win.cfg.prediction_debounce_ms, "settings.debounce_ms", "Debounce (ms):", 0, 500, 10),
        ("_maxcand_var", win.cfg.prediction_max_candidates, "settings.max_candidates", "Max suggestions:", 1, 9, 1),
        ("_minlen_var", win.cfg.min_prefix_len, "settings.min_prefix", "Min prefix length:", 1, 6, 1),
    ):
        ttk.Label(eng_card, text=t(label_key, label_def), style="Card.TLabel").grid(row=e_row, column=0, sticky=align, **pad)
        iv = tk.IntVar(value=init_val)
        setattr(win, attr_name, iv)
        ttk.Spinbox(eng_card, from_=f_from, to=f_to, increment=f_inc, textvariable=iv, width=8).grid(row=e_row, column=1, sticky="w", **pad)
        e_row += 1

    # ── Card 4: Dictionaries, Personal Vocabulary & Privacy ──
    dict_title = "📚 واژه‌نامه‌ها، کلمات شخصی و حریم خصوصی" if rtl else "📚 Dictionaries, Personal Vocabulary & Privacy"
    dict_card = FluentCard(frm, dict_title, padding=12, palette=palette, rtl=rtl, icon="code")
    dict_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    dict_card.columnconfigure(0, weight=1)
    row += 1

    d_row = 0
    win._en_dict_var = tk.BooleanVar(value=win.cfg.english_dict_enabled)
    FluentToggleSwitch(dict_card, text=t("settings.en_dict", "English dictionary"), variable=win._en_dict_var, palette=palette, rtl=rtl).grid(row=d_row, column=0, columnspan=3, sticky="ew", padx=10, pady=3)
    d_row += 1

    win._fa_dict_var = tk.BooleanVar(value=win.cfg.persian_dict_enabled)
    FluentToggleSwitch(dict_card, text=t("settings.fa_dict", "Persian dictionary"), variable=win._fa_dict_var, palette=palette, rtl=rtl).grid(row=d_row, column=0, columnspan=3, sticky="ew", padx=10, pady=3)
    d_row += 1

    ttk.Label(dict_card, text=t("settings.custom_words_label", "Custom words / names (one per line):"), style="Card.TLabel", font=get_ui_font(size=9, bold=True, rtl=rtl)).grid(row=d_row, column=0, columnspan=3, sticky=align, padx=10, pady=(6, 2))
    d_row += 1

    win._user_words_text = tk.Text(dict_card, width=48, height=4)
    _style_text_widget(win._user_words_text, palette, rtl=rtl)
    win._user_words_text.insert("1.0", "\n".join(load_user_words()))
    win._user_words_text.grid(row=d_row, column=0, columnspan=3, sticky="ew", **pad)
    d_row += 1

    data_box = tk.Frame(dict_card, bg=palette.bg_surface)
    data_box.grid(row=d_row, column=0, columnspan=3, sticky="we", padx=10, pady=(4, 4))
    d_row += 1

    def _do_export_data() -> None:
        from tkinter import filedialog, messagebox

        from ravan.ui.settings_learning import _get_engine

        dest = filedialog.asksaveasfilename(
            parent=win._root, title=t("settings.export_dialog_title", "Export Learned Data"),
            defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="ravaan_learned_data.json",
        )
        if dest:
            try:
                _get_engine(win).export_profile(target_path=dest)
                messagebox.showinfo("Ravaan", t("settings.export_data_success", "Learned vocabulary and style data exported successfully!"), parent=win._root)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("Ravaan", str(exc), parent=win._root)

    def _do_clear_data() -> None:
        from tkinter import messagebox

        from ravan.ui.settings_learning import _get_engine

        if messagebox.askyesno(
            t("settings.clear_data_confirm_title", "Clear Learned Data"),
            t("settings.clear_data_confirm_msg", "Are you sure? All learned words and style data will be reset to factory defaults."),
            parent=win._root,
        ):
            try:
                _get_engine(win).clear_learned_data()
                if callable(getattr(win, "_refresh_learning_list", None)):
                    win._refresh_learning_list()
                messagebox.showinfo("Ravaan", t("settings.clear_data_success", "All learned data has been cleared successfully."), parent=win._root)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("Ravaan", str(exc), parent=win._root)

    btn_pack_side = "right" if rtl else "left"
    FluentPillButton(data_box, text=t("settings.btn_export_data", "Export my data (.json)"), icon="copy", variant="secondary", palette=palette, rtl=rtl, command=_do_export_data).pack(side=btn_pack_side, padx=(0, 6) if not rtl else (6, 0))
    FluentPillButton(data_box, text=t("settings.btn_clear_data", "Clear learned data"), icon="close", variant="danger", palette=palette, rtl=rtl, command=_do_clear_data).pack(side=btn_pack_side, padx=(0, 6) if not rtl else (6, 0))

    from ravan.ui.settings_learning import build_learning_and_exceptions_card

    row = build_learning_and_exceptions_card(win, frm, row, pad)
    FluentPillButton(frm, text=t("settings.reset_tab_btn", "Reset tab defaults"), icon="reset", variant="secondary", palette=palette, rtl=rtl, parent_bg=palette.bg_base, command=lambda: win._reset_tab_defaults("prediction")).grid(row=row, column=0, sticky=align, pady=(4, 4))
    return row + 1

"""Live suggestion-box preview and color preset handlers for SettingsWindow."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from ravan.core.i18n import is_rtl


class SettingsPreviewMixin:
    """Mixin providing live suggestion-box style preview and custom color pickers."""

    cfg: Any
    on_saved: Any
    _root: tk.Toplevel | None
    _preview_chassis_img: Any
    _preview_chassis_photo: Any

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
    _PREVIEW_BACKDROP = "#3c5068"

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
        for f in ("bg", "fg", "accent", "border", "highlight"):
            var = getattr(self, f"_prediction_custom_{f}_var", None)
            if var is not None:
                setattr(self.cfg, f"prediction_custom_{f}", var.get())
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

    def _render_style_preview(self) -> None:
        """Render a live mini suggestion-box over a simulated desktop."""
        from PIL import ImageTk

        from ravan.ui.preview_graphics import render_style_chassis
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
        tokens = get_prediction_style(style, mode, custom_colors=custom_colors, layout=layout)
        palette = tokens.palette
        rtl_ui = is_rtl()
        traits_dict = self._STYLE_TRAITS if rtl_ui else self._STYLE_TRAITS_EN
        trait_text, _alpha_eff = traits_dict.get(style, traits_dict["modern"])
        style_icon = self._STYLE_ICONS.get(style, "✨")

        container = tk.Frame(preview)
        container.pack(fill="x")

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

            typing_prompt = "متن در حال تایپ: سلام" if rtl_ui else "Typing: hello"
            f_sim = get_ui_font(size=8, rtl=rtl_ui)
            sim_lead_x = cw - 18 if rtl_ui else 18
            sim_anchor = "ne" if rtl_ui else "nw"
            backdrop_canvas.create_text(
                sim_lead_x, 7, text=typing_prompt + " |", anchor=sim_anchor, fill=sim_text_fg, font=f_sim
            )

            cx = cw // 2
            cy = (canvas_h // 2) if is_horiz_preview else (20 + card_h // 2)
            backdrop_canvas.create_image(cx, cy, image=self._preview_chassis_photo)

            x_left = cx - card_w // 2
            x_right = cx + card_w // 2
            y_top = cy - card_h // 2

            if is_horiz_preview:
                horiz_cands = [("۱ سلام علیکم", True), ("۲ سلام", False), ("۳ سلسفیلا", False)]
                chip_w = (card_w - 36) // 3
                c1_right = x_right - 18
                for idx, (cand_label, is_sel) in enumerate(horiz_cands):
                    chip_cx = c1_right - idx * chip_w - chip_w // 2
                    if custom_colors:
                        fg_c = custom_colors.get("highlight_fg", "#FFFFFF") if is_sel else custom_colors.get("fg", "#F5F5F7")
                    elif is_sel:
                        fg_c = "#00FF66" if style == "neon" else "#FFFFFF"
                    elif style == "classic":
                        fg_c = "#000000"
                    elif style == "neon":
                        fg_c = "#00FF66"
                    else:
                        fg_c = "#E5E5EA"
                    backdrop_canvas.create_text(
                        chip_cx, cy, text=cand_label, anchor="center", fill=fg_c, font=get_ui_font(size=9, bold=is_sel, rtl=True)
                    )
                return

            headers_spec = {
                "classic": (x_left + 14, y_top + 10, "روان - Ravaan", "w", "#FFFFFF", True),
                "modern": (cx, y_top + 11, "✦  روان  ✦", "center", "#E9D5FF", True),
                "fluent": (x_left + 26, y_top + 10, "روان", "w", "#60CDFF", True),
                "ios": (x_left + 16, y_top + 11, " روان", "w", "#D2D2D7", True),
                "glass": (cx, y_top + 11, "💎  روان", "center", "#A0D0FF", True),
                "neon": (cx, y_top + 11, "// RAVAAN HUD //", "center", "#FF007F", False),
                "material": (cx, y_top + 11, "🎨 روان", "center", "#D0BCFF", True),
                "compact": (x_left + 14, y_top + 8, "روان", "w", "#8E8E96", True),
                "minimal": (cx, y_top + 10, "⋯ روان ⋯", "center", "#808088", True),
                "macos": (cx, y_top + 11, "روان", "center", "#94949E", True),
            }
            if style in headers_spec:
                hx, hy, htxt, hanc, hcol, hrtl = headers_spec[style]
                backdrop_canvas.create_text(hx, hy, text=htxt, anchor=hanc, fill=hcol, font=get_ui_font(size=8, bold=True, rtl=hrtl))

            candidates = [
                ("سلام علیکم", "1", True, "[ادامه]"),
                ("سلام", "2", False, ""),
                ("سلسفیلا", "3", False, ""),
                ("سلیس", "4", False, ""),
                ("سلاح", "5", False, ""),
            ]
            r1_y = y_top + (30 if style == "compact" else (34 if style == "classic" else 38))
            step_y = 25 if style == "compact" else 26

            for idx, (cand_text, badge_num, is_sel, tag) in enumerate(candidates):
                row_y = r1_y + idx * step_y
                if custom_colors:
                    fg_c = custom_colors.get("highlight_fg", "#FFFFFF") if is_sel else custom_colors.get("fg", "#F5F5F7")
                    b_fg = custom_colors.get("highlight_fg", "#FFFFFF") if is_sel else custom_colors.get("accent", "#0A84FF")
                elif is_sel:
                    fg_c = "#00FF66" if style == "neon" else "#FFFFFF"
                    b_fg = "#FF007F" if style == "neon" else ("#60CDFF" if style == "fluent" else "#FFFFFF")
                elif style == "neon":
                    fg_c, b_fg = "#00FF66", "#FF007F"
                elif style == "classic":
                    fg_c, b_fg = "#000000", "#000000"
                elif style == "fluent":
                    fg_c, b_fg = ("#E0E0E0", "#60CDFF") if is_dark_preview else ("#1F2328", "#0067C0")
                elif style == "modern":
                    fg_c, b_fg = ("#F3E8FF", "#C77DFF") if is_dark_preview else ("#2B1E4A", "#7C3AED")
                elif style == "glass":
                    fg_c, b_fg = ("#FFFFFF", "#8FA6BC") if is_dark_preview else ("#1F2328", "#4A6580")
                elif style == "material":
                    fg_c, b_fg = ("#E6E1E5", "#CAC4D0") if is_dark_preview else ("#1C1B1F", "#49454F")
                else:
                    fg_c, b_fg = ("#C4C4CF", "#8C8C96") if is_dark_preview else ("#1F2328", "#57606A")

                backdrop_canvas.create_text(
                    x_right - 20, row_y, text=cand_text, anchor="e", fill=fg_c, font=get_ui_font(size=10 if is_sel else 9, bold=is_sel, rtl=True)
                )
                backdrop_canvas.create_text(
                    x_left + 18, row_y, text=badge_num, anchor="center" if style in ("material", "minimal") else "w", fill=b_fg, font=get_ui_font(size=8, bold=is_sel)
                )
                if is_sel:
                    m_col = "#00FF66" if style == "neon" else ("#60CDFF" if style == "fluent" else "#FFFFFF")
                    backdrop_canvas.create_oval(
                        x_left + 32, row_y - 3, x_left + 38, row_y + 3, fill=m_col, outline=""
                    )
                    if tag:
                        tag_col = "#A6E2FF" if style == "neon" else ("#EAE6DD" if style == "classic" else "#DCEEFF")
                        backdrop_canvas.create_text(x_left + 44, row_y, text=tag, anchor="w", fill=tag_col, font=get_ui_font(size=7, rtl=True))

            if tokens.show_hint_bar and style != "compact":
                hint_mock = (
                    "[ESC: CLOSE  |  ENTER: ACCEPT  |  1-5: QUICK PICK]"
                    if style == "neon"
                    else ("بستن: Esc  ·  تأیید: Enter  ·  انتخاب: ۱-۵ سریع" if rtl_ui else "Esc: Close  ·  Enter: Accept  ·  1-5: Pick")
                )
                hint_fg_map = {"neon": "#FF007F", "classic": "#505050", "fluent": "#60CDFF", "modern": "#A894C4", "glass": "#8AB4D8"}
                backdrop_canvas.create_text(
                    cx, y_top + card_h - 10, text=hint_mock, anchor="center", fill=hint_fg_map.get(style, "#787884"), font=get_ui_font(size=7, rtl=rtl_ui)
                )

        backdrop_canvas.update_idletasks()
        init_w = backdrop_canvas.winfo_width()
        _draw_content(init_w if init_w > 50 else 320)
        backdrop_canvas.bind("<Configure>", lambda e: _draw_content(e.width))

        info_bar = tk.Frame(preview, bg=palette.bg_surface, padx=8, pady=3)
        info_bar.pack(fill="x", pady=(2, 0))
        is_horizontal = tokens.layout == "horizontal"
        layout_txt = ("افقی (رو‌به‌روی هم)" if is_horizontal else "عمودی (زیر هم)") if rtl_ui else ("Horizontal Ribbon" if is_horizontal else "Vertical Stack")
        custom_txt = (" · رنگ‌های سفارشی" if rtl_ui else " · Custom Colors") if use_custom else ""
        ttk.Label(info_bar, text=f"{style_icon}  {style.upper()} ({layout_txt}{custom_txt})", style="Card.TLabel", font=get_ui_font(size=9, bold=True), foreground=palette.accent).pack(side="left", padx=(4, 8))
        ttk.Label(info_bar, text=trait_text, style="CardSub.TLabel").pack(side="left", fill="x", expand=True)

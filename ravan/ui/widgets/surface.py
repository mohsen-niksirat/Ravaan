"""Fluent 2 surface containers, anti-aliased rounded banners, cards, and badges."""

from __future__ import annotations

import re
import tkinter as tk
from functools import lru_cache
from typing import Any

from PIL import Image, ImageDraw, ImageTk

from ravan.ui.theme_palettes import Palette, get_active_palette, get_dpi_scale, get_ui_font
from ravan.ui.widgets.icons import get_icon, resolve_icon_name


def _rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    try:
        h = hex_color.strip().lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        rgb = int(h[:6], 16)
        return ((rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF, alpha)
    except Exception:
        return (41, 43, 47, alpha)


@lru_cache(maxsize=256)
def render_rounded_surface(
    width: int,
    height: int,
    radius: int,
    fill_hex: str,
    border_hex: str = "",
    bg_hex: str = "#202124",
    accent_bar_hex: str = "",
    rtl: bool = False,
) -> Image.Image:
    """Render a 2x-supersampled anti-aliased rounded rectangle card onto `bg_hex`."""
    w = max(16, int(width))
    h = max(16, int(height))
    ss = 2
    sw, sh = w * ss, h * ss
    r = min(sw // 2, sh // 2, max(0, int(radius * ss)))

    img = Image.new("RGBA", (sw, sh), _rgba(bg_hex, 255))
    draw = ImageDraw.Draw(img)

    fill_c = _rgba(fill_hex, 255)
    border_c = _rgba(border_hex, 255) if border_hex else None
    bw = 2 if border_c else 0

    draw.rounded_rectangle(
        [1, 1, sw - 2, sh - 2],
        radius=r,
        fill=fill_c,
        outline=border_c,
        width=bw,
    )

    if accent_bar_hex:
        bar_c = _rgba(accent_bar_hex, 255)
        bar_w = 6
        bar_m = max(12, r)
        if rtl:
            draw.rounded_rectangle([sw - bar_w - 4, bar_m, sw - 4, sh - bar_m], radius=3, fill=bar_c)
        else:
            draw.rounded_rectangle([4, bar_m, 4 + bar_w, sh - bar_m], radius=3, fill=bar_c)

    return img.resize((w, h), Image.Resampling.LANCZOS)


def _strip_leading_emoji(title: str) -> tuple[str | None, str]:
    """Extract leading emoji/symbol from a card title so we can render a crisp vector icon instead."""
    clean = (title or "").strip()
    if not clean:
        return None, ""
    parts = clean.split(None, 1)
    first = parts[0]
    if any(ord(c) > 0x2000 for c in first) and not re.search(r"[\u0600-\u06FFa-zA-Z0-9]", first):
        rest = parts[1].strip() if len(parts) > 1 else ""
        return resolve_icon_name(first), rest
    return None, clean


class FluentSectionBanner(tk.Frame):
    """Prominent Fluent 2 section header card with 2x-AA rounded surface and vector icon badge."""

    def __init__(
        self,
        parent: tk.Misc,
        icon: str,
        title: str,
        subtitle: str = "",
        palette: Palette | None = None,
        rtl: bool = False,
    ) -> None:
        pal = palette or get_active_palette("auto")
        super().__init__(
            parent,
            bg=pal.bg_elevated,
            bd=0,
            highlightthickness=1,
            highlightbackground=pal.border_subtle,
            highlightcolor=pal.border_subtle,
            padx=16,
            pady=12,
        )
        self.palette = pal
        self.rtl = rtl

        side_lead = "right" if rtl else "left"
        anchor = "e" if rtl else "w"
        justify = "right" if rtl else "left"

        # Accent vector icon badge container
        dpi = get_dpi_scale(self)
        icon_photo = get_icon(icon, size=20, color=pal.accent, dpi=dpi, master=self)
        self._icon_photo = icon_photo

        badge_frm = tk.Frame(
            self,
            bg=pal.badge_bg,
            padx=8,
            pady=8,
            bd=0,
            highlightthickness=1,
            highlightbackground=pal.border_subtle,
        )
        badge_frm.pack(side=side_lead, padx=(12, 0) if rtl else (0, 12), anchor="center")

        if icon_photo is not None:
            tk.Label(badge_frm, image=icon_photo, bg=pal.badge_bg, bd=0).pack()
        else:
            tk.Label(
                badge_frm,
                text="◆",
                bg=pal.badge_bg,
                fg=pal.accent,
                font=get_ui_font(size=11, bold=True),
            ).pack()

        text_col = tk.Frame(self, bg=pal.bg_elevated)
        text_col.pack(side=side_lead, fill="both", expand=True)

        tk.Label(
            text_col,
            text=title,
            bg=pal.bg_elevated,
            fg=pal.fg,
            font=get_ui_font(size=12, bold=True, rtl=rtl),
            anchor=anchor,
            justify=justify,
        ).pack(fill="x", anchor=anchor)

        if subtitle:
            tk.Label(
                text_col,
                text=subtitle,
                bg=pal.bg_elevated,
                fg=pal.subtext,
                font=get_ui_font(size=8, rtl=rtl),
                anchor=anchor,
                justify=justify,
            ).pack(fill="x", anchor=anchor, pady=(2, 0))


class FluentCard(tk.LabelFrame):
    """Fluent 2 elevated card with custom vector-icon header and 1px hairline subtle border.

    Subclasses `tk.LabelFrame` with a custom `labelwidget` so callers can freely use
    either `.grid(row=0, ...)` or `.pack(...)` directly on the card or on `card.body`.
    """

    def __init__(
        self,
        parent: tk.Misc,
        title: str = "",
        padding: int = 12,
        palette: Palette | None = None,
        rtl: bool = False,
        icon: str | None = None,
        **kwargs: Any,
    ) -> None:
        pal = palette or get_active_palette("auto")
        extracted_icon, clean_title = _strip_leading_emoji(title)
        eff_icon = icon or extracted_icon

        hdr_frame = tk.Frame(parent, bg=pal.bg_surface, padx=6, pady=2)
        side = "right" if rtl else "left"

        if eff_icon:
            dpi = get_dpi_scale(parent)
            photo = get_icon(eff_icon, size=14, color=pal.accent, dpi=dpi, master=parent)
            self._hdr_icon_photo = photo
            if photo is not None:
                tk.Label(hdr_frame, image=photo, bg=pal.bg_surface, bd=0).pack(
                    side=side, padx=(4, 0) if rtl else (0, 6)
                )

        if clean_title:
            tk.Label(
                hdr_frame,
                text=clean_title,
                bg=pal.bg_surface,
                fg=pal.accent,
                font=get_ui_font(size=10, bold=True, rtl=rtl),
            ).pack(side=side)

        super().__init__(
            parent,
            labelwidget=hdr_frame if (clean_title or eff_icon) else None,
            labelanchor="ne" if rtl else "nw",
            bg=pal.bg_surface,
            fg=pal.fg,
            bd=0,
            relief="flat",
            highlightthickness=1,
            highlightbackground=pal.border_subtle,
            highlightcolor=pal.border_subtle,
            padx=padding,
            pady=padding,
            **kwargs,
        )
        self.palette = pal
        self.rtl = rtl
        self.header_frame = hdr_frame

    @property
    def body(self) -> FluentCard:
        """Return the card content container (self)."""
        return self


class FluentBadge(tk.Canvas):
    """2x-AA Pillow rounded pill badge for version tags, status pills, and keycaps."""

    def __init__(
        self,
        parent: tk.Misc,
        text: str,
        palette: Palette | None = None,
        bg_color: str | None = None,
        fg_color: str | None = None,
        parent_bg: str | None = None,
        rtl: bool = False,
    ) -> None:
        pal = palette or get_active_palette("auto")
        self._pal = pal
        self._text = text
        self._fill = bg_color or pal.badge_bg
        self._fg = fg_color or pal.badge_fg
        self._parent_bg = parent_bg or pal.bg_surface
        self._rtl = rtl
        self._photo: ImageTk.PhotoImage | None = None

        f = get_ui_font(size=8, bold=True, rtl=rtl)
        est_w = max(44, len(text) * 7 + 20)
        est_h = 22
        super().__init__(
            parent,
            width=est_w,
            height=est_h,
            bg=self._parent_bg,
            bd=0,
            highlightthickness=0,
        )
        self._font = f
        self._redraw(est_w, est_h)

    def _redraw(self, w: int, h: int) -> None:
        self.delete("all")
        pil_img = render_rounded_surface(
            w,
            h,
            radius=h // 2,
            fill_hex=self._fill,
            border_hex=self._pal.border_subtle,
            bg_hex=self._parent_bg,
        )
        try:
            self._photo = ImageTk.PhotoImage(pil_img, master=self)
            self.create_image(w // 2, h // 2, image=self._photo)
        except Exception:
            pass
        self.create_text(w // 2, h // 2, text=self._text, fill=self._fg, font=self._font)

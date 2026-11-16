"""Fluent 2 pack preview dialog for Ravaan Hub (.ravaanpack inspection)."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any

from ravan.core.hub import HubPack
from ravan.core.i18n import is_rtl, t
from ravan.ui.theme import (
    Palette,
    apply_window_decorations,
    get_active_palette,
    get_dpi_scale,
    get_ui_font,
)
from ravan.ui.widgets import FluentBadge, FluentPillButton, get_icon


def open_hub_preview_modal(
    parent: tk.Misc | None,
    pack: HubPack,
    *,
    installed: bool,
    has_update: bool,
    on_install: Callable[[HubPack], None],
    on_uninstall: Callable[[HubPack], None],
    theme_mode: str = "auto",
) -> tk.Toplevel:
    """Open a clean Fluent 2 modal displaying pack details, SHA-256 status & trigger previews."""
    pal: Palette = get_active_palette(theme_mode)
    rtl = is_rtl()
    is_dark = pal.name in ("dark", "high_contrast")
    lead, trail = ("right", "left") if rtl else ("left", "right")
    anchor, justify = ("e", "right") if rtl else ("w", "left")

    win = tk.Toplevel(parent)
    win.withdraw()
    title = pack.title_fa if rtl else pack.title_en
    win.title(f"{title} — Ravaan Hub")
    win.configure(bg=pal.bg_base)
    win.resizable(False, False)
    if parent is not None and getattr(parent, "winfo_ismapped", lambda: False)():
        win.transient(parent)
    win.attributes("-topmost", True)
    apply_window_decorations(win, pal)

    body = tk.Frame(win, bg=pal.bg_surface, highlightthickness=1, highlightbackground=pal.border_subtle, padx=18, pady=16)
    body.pack(fill="both", expand=True, padx=10, pady=10)

    hdr = tk.Frame(body, bg=pal.bg_surface)
    hdr.pack(fill="x", pady=(0, 8))
    dpi = get_dpi_scale(win)
    ic_photo = get_icon("hub", size=20, color=pal.accent, dpi=dpi, master=win)
    if ic_photo is not None:
        lbl_ic = tk.Label(hdr, image=ic_photo, bg=pal.bg_surface, bd=0)
        lbl_ic.image = ic_photo  # type: ignore[attr-defined]
        lbl_ic.pack(side=lead, padx=(8, 0) if rtl else (0, 8))

    tk.Label(
        hdr, text=title, bg=pal.bg_surface, fg=pal.fg,
        font=get_ui_font(size=12, bold=True, rtl=rtl), anchor=anchor,
    ).pack(side=lead)

    FluentBadge(hdr, text=f"v{pack.version}", palette=pal, parent_bg=pal.bg_surface, rtl=rtl).pack(side=lead, padx=8)
    if pack.verified:
        v_bg = "#1c3d2d" if is_dark else "#e2f6ea"
        v_fg = "#7ee2a8" if is_dark else "#0f5132"
        FluentBadge(
            hdr, text=t("hub.sha_verified", "SHA-256 ✓"), palette=pal,
            bg_color=v_bg, fg_color=v_fg, parent_bg=pal.bg_surface, rtl=rtl,
        ).pack(side=lead)

    desc = pack.description_fa if rtl else pack.description_en
    tk.Label(
        body, text=desc, bg=pal.bg_surface, fg=pal.subtext, wraplength=440,
        font=get_ui_font(size=9, rtl=rtl), anchor=anchor, justify=justify,
    ).pack(fill="x", pady=(0, 6))

    digest_txt = pack.sha256[:24] + "…" if pack.sha256 else t("hub.builtin_sha", "امضای SHA-256 خودکار حین نصب" if rtl else "Verified via manifest SHA-256 digest")
    meta_txt = (
        f"سازنده: {pack.author}  ·  تعداد میانبر: {pack.snippet_count}"
        if rtl
        else f"Author: {pack.author}  ·  {pack.snippet_count} snippets  ·  {digest_txt}"
    )
    tk.Label(
        body, text=meta_txt, bg=pal.bg_surface, fg=pal.subtext,
        font=get_ui_font(size=8, rtl=rtl), anchor=anchor,
    ).pack(fill="x", pady=(0, 10))

    prev_box = tk.Frame(body, bg=pal.bg_elevated, highlightthickness=1, highlightbackground=pal.border_subtle, padx=10, pady=8)
    prev_box.pack(fill="both", expand=True, pady=(0, 12))
    tk.Label(
        prev_box, text=t("hub.preview_header", "نمونه میانبرهای این بسته:" if rtl else "Included Snippet Previews:"),
        bg=pal.bg_elevated, fg=pal.accent, font=get_ui_font(size=9, bold=True, rtl=rtl), anchor=anchor,
    ).pack(fill="x", pady=(0, 6))

    for trig, repl in pack.preview_items[:6]:
        row = tk.Frame(prev_box, bg=pal.bg_elevated)
        row.pack(fill="x", pady=2)
        FluentBadge(row, text=trig, palette=pal, parent_bg=pal.bg_elevated, rtl=False).pack(side=lead, padx=(8, 0) if rtl else (0, 8))
        tk.Label(
            row, text=repl, bg=pal.bg_elevated, fg=pal.fg, wraplength=390,
            font=get_ui_font(size=8, rtl=rtl), anchor=anchor, justify=justify,
        ).pack(side=lead, fill="x", expand=True)

    footer = tk.Frame(body, bg=pal.bg_surface)
    footer.pack(fill="x")

    def _act_install() -> None:
        win.destroy()
        on_install(pack)

    def _act_uninstall() -> None:
        win.destroy()
        on_uninstall(pack)

    if has_update:
        FluentPillButton(
            footer, text=t("hub.btn_update", "بروزرسانی بسته" if rtl else "Update Pack"),
            icon="replace", variant="primary", palette=pal, rtl=rtl, parent_bg=pal.bg_surface, height=32, width=136, command=_act_install,
        ).pack(side=lead)
    elif installed:
        FluentPillButton(
            footer, text=t("hub.btn_uninstall", "حذف بسته" if rtl else "Uninstall"),
            icon="close", variant="danger", palette=pal, rtl=rtl, parent_bg=pal.bg_surface, height=32, width=118, command=_act_uninstall,
        ).pack(side=lead)
    else:
        FluentPillButton(
            footer, text=t("hub.btn_install", "نصب یک‌کلیکی" if rtl else "1-Click Install"),
            icon="check", variant="primary", palette=pal, rtl=rtl, parent_bg=pal.bg_surface, height=32, width=138, command=_act_install,
        ).pack(side=lead)

    FluentPillButton(
        footer, text=t("hub.btn_close", "بستن (Esc)" if rtl else "Close (Esc)"),
        icon="close", variant="ghost", palette=pal, rtl=rtl, parent_bg=pal.bg_surface, height=32, width=106, command=win.destroy,
    ).pack(side=trail)

    win.bind("<Escape>", lambda _e: win.destroy())
    win.update_idletasks()
    w, h = max(540, win.winfo_reqwidth()), max(360, win.winfo_reqheight())
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    win.geometry(f"{w}x{h}+{max(20, (sw - w) // 2)}+{max(20, (sh - h) // 3)}")
    win.deiconify()
    return win


def get_hub_badge_colors(palette: Palette) -> tuple[str, str]:
    """Return contrasting background & foreground colors for verified SHA-256 badge."""
    if palette.name in ("dark", "high_contrast"):
        return ("#1c3d2d", "#7ee2a8")
    return ("#e2f6ea", "#0f5132")


__all__: list[str] = ["open_hub_preview_modal", "get_hub_badge_colors"]
_UNUSED_ANY = Any

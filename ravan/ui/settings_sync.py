"""Background sync UI builder for SettingsWindow (Gist and WebDAV)."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk
from typing import Any

from ravan.core.i18n import is_rtl, t
from ravan.ui.settings_builder import _get_win_palette, _make_card, _make_section_banner
from ravan.ui.settings_sync_actions import do_sync_pull, do_sync_push
from ravan.ui.theme import get_ui_font

log = logging.getLogger(__name__)


def build_sync_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    """Build the Cloud Sync settings UI section with Gist and WebDAV support."""
    rtl = is_rtl()
    palette = _get_win_palette(win)
    row = start_row
    align = "e" if rtl else "w"
    pack_side = "right" if rtl else "left"
    frm.columnconfigure(0, weight=1)

    sub = t(
        "settings.sync_desc",
        "Sync your user words and snippets securely across PCs via GitHub Gist or WebDAV (Nextcloud).",
    )
    banner = _make_section_banner(
        frm,
        "☁️",
        t("settings.sync_header", "Cloud Sync (GitHub Gist / WebDAV)"),
        sub,
        palette,
        rtl,
    )
    banner.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    row += 1

    # Privacy Badge Banner
    priv_card = tk.Frame(
        frm,
        bg=palette.card_bg,
        highlightthickness=1,
        highlightbackground=palette.success,
        padx=14,
        pady=8,
    )
    priv_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    row += 1

    tk.Label(
        priv_card,
        text=t(
            "settings.sync_privacy_guarantee",
            "🛡️ Privacy Guarantee: Only your custom dictionary words, snippets, and preferences are synchronized. "
            "Ravaan NEVER logs, stores, or uploads your typed text, keystrokes, clipboard contents, or passwords.",
        ),
        bg=palette.card_bg,
        fg=palette.success,
        font=get_ui_font(size=8, rtl=rtl),
        wraplength=540,
        justify="right" if rtl else "left",
        anchor=align,
    ).pack(fill="x", anchor=align)

    # ── Card 1: Provider & Credentials ──
    prov_title = "🔑 سرویس ابری و اطلاعات اتصال" if rtl else "🔑 Cloud Provider & Credentials"
    prov_card = _make_card(frm, prov_title, padding=12)
    prov_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    prov_card.columnconfigure(1, weight=1)
    row += 1

    p_row = 0
    ttk.Label(prov_card, text=t("settings.sync_backend", "Sync Backend:")).grid(
        row=p_row, column=0, sticky=align, **pad
    )
    current_backend = getattr(win.cfg, "sync_backend", "gist").lower()
    backend_display = (
        t("settings.sync_backend_webdav", "WebDAV (Nextcloud / ownCloud)")
        if current_backend == "webdav"
        else t("settings.sync_backend_gist", "GitHub Gist")
    )
    win._sync_backend_var = tk.StringVar(value=backend_display)
    backend_box = ttk.Combobox(
        prov_card,
        textvariable=win._sync_backend_var,
        values=[
            t("settings.sync_backend_gist", "GitHub Gist"),
            t("settings.sync_backend_webdav", "WebDAV (Nextcloud / ownCloud)"),
        ],
        state="readonly",
        width=32,
    )
    backend_box.grid(row=p_row, column=1, columnspan=2, sticky="w", **pad)
    p_row += 1

    container = ttk.Frame(prov_card)
    container.grid(row=p_row, column=0, columnspan=3, sticky="we", pady=(4, 4))
    p_row += 1

    # Frame 1: Gist
    gist_frm = ttk.Frame(container)
    ttk.Label(gist_frm, text=t("settings.sync_pat_label", "Gist Token:")).grid(
        row=0, column=0, sticky=align, **pad
    )
    win._gist_token_var = tk.StringVar(value=getattr(win.cfg, "gist_token", ""))
    token_entry = ttk.Entry(gist_frm, textvariable=win._gist_token_var, width=30, show="*")
    token_entry.grid(row=0, column=1, sticky="w", **pad)

    def toggle_show_token() -> None:
        token_entry.config(show="" if token_entry.cget("show") == "*" else "*")

    ttk.Button(
        gist_frm,
        text=t("settings.show_hide", "Show/Hide"),
        command=toggle_show_token,
        width=9,
    ).grid(row=0, column=2, sticky="w", **pad)

    ttk.Label(gist_frm, text=t("settings.sync_gist_id", "Gist ID:")).grid(
        row=1, column=0, sticky=align, **pad
    )
    win._gist_id_var = tk.StringVar(value=getattr(win.cfg, "gist_id", ""))
    ttk.Entry(gist_frm, textvariable=win._gist_id_var, width=30).grid(
        row=1, column=1, sticky="w", **pad
    )
    ttk.Label(
        gist_frm, text=t("settings.gist_url_hint", "Found in gist URL"), style="Sub.TLabel"
    ).grid(row=1, column=2, sticky="w", **pad)

    # Frame 2: WebDAV
    webdav_frm = ttk.Frame(container)
    ttk.Label(webdav_frm, text=t("settings.sync_webdav_url", "WebDAV URL:")).grid(
        row=0, column=0, sticky=align, **pad
    )
    win._webdav_url_var = tk.StringVar(value=getattr(win.cfg, "webdav_url", ""))
    ttk.Entry(webdav_frm, textvariable=win._webdav_url_var, width=38).grid(
        row=0, column=1, columnspan=2, sticky="w", **pad
    )

    ttk.Label(webdav_frm, text=t("settings.sync_webdav_username", "Username:")).grid(
        row=1, column=0, sticky=align, **pad
    )
    win._webdav_username_var = tk.StringVar(value=getattr(win.cfg, "webdav_username", ""))
    ttk.Entry(webdav_frm, textvariable=win._webdav_username_var, width=30).grid(
        row=1, column=1, sticky="w", **pad
    )

    ttk.Label(webdav_frm, text=t("settings.sync_webdav_password", "Password:")).grid(
        row=2, column=0, sticky=align, **pad
    )
    win._webdav_password_var = tk.StringVar(value=getattr(win.cfg, "webdav_password", ""))
    pass_entry = ttk.Entry(
        webdav_frm, textvariable=win._webdav_password_var, width=30, show="*"
    )
    pass_entry.grid(row=2, column=1, sticky="w", **pad)

    def toggle_show_pass() -> None:
        pass_entry.config(show="" if pass_entry.cget("show") == "*" else "*")

    ttk.Button(
        webdav_frm,
        text=t("settings.show_hide", "Show/Hide"),
        command=toggle_show_pass,
        width=9,
    ).grid(row=2, column=2, sticky="w", **pad)

    def on_backend_selected(_event: object = None) -> None:
        val = win._sync_backend_var.get().lower()
        if "webdav" in val:
            gist_frm.pack_forget()
            webdav_frm.pack(fill="x", expand=True)
        else:
            webdav_frm.pack_forget()
            gist_frm.pack(fill="x", expand=True)

    backend_box.bind("<<ComboboxSelected>>", on_backend_selected)
    on_backend_selected()

    # ── Card 2: Schedule & Actions ──
    sched_title = "🔄 زمان‌بندی و عملیات همگام‌سازی" if rtl else "🔄 Sync Schedule & Manual Actions"
    sched_card = _make_card(frm, sched_title, padding=12)
    sched_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    sched_card.columnconfigure(1, weight=1)
    row += 1

    sc_row = 0
    win._cloud_sync_var = tk.BooleanVar(value=getattr(win.cfg, "cloud_sync_enabled", False))
    ttk.Checkbutton(
        sched_card,
        text=t("settings.sync_auto", "Enable automatic background sync"),
        variable=win._cloud_sync_var,
    ).grid(row=sc_row, column=0, columnspan=2, sticky=align, **pad)
    sc_row += 1

    win._sync_learning_var = tk.BooleanVar(
        value=getattr(win.cfg, "sync_learning_profile", False)
    )
    ttk.Checkbutton(
        sched_card,
        text=t("settings.sync_learning", "Include learned typing profile in cloud sync"),
        variable=win._sync_learning_var,
    ).grid(row=sc_row, column=0, columnspan=2, sticky=align, **pad)
    sc_row += 1

    ttk.Label(sched_card, text=t("settings.sync_interval_label", "Sync Interval:")).grid(
        row=sc_row, column=0, sticky=align, **pad
    )
    cur_interval = getattr(win.cfg, "sync_interval_min", 0)
    int_display = (
        t("settings.sync_interval_15", "Every 15 minutes")
        if cur_interval == 15
        else (
            t("settings.sync_interval_60", "Every 60 minutes")
            if cur_interval == 60
            else t("settings.sync_interval_off", "Manual only (Off)")
        )
    )
    win._sync_interval_display_var = tk.StringVar(value=int_display)
    win._sync_interval_var = tk.StringVar(value=str(cur_interval))

    interval_opts = [
        (t("settings.sync_interval_off", "Manual only (Off)"), "0"),
        (t("settings.sync_interval_15", "Every 15 minutes"), "15"),
        (t("settings.sync_interval_60", "Every 60 minutes"), "60"),
    ]
    int_box = ttk.Combobox(
        sched_card,
        textvariable=win._sync_interval_display_var,
        values=[opt[0] for opt in interval_opts],
        state="readonly",
        width=26,
    )
    int_box.grid(row=sc_row, column=1, sticky="w", **pad)

    def on_interval_selected(_event: object = None) -> None:
        sel = win._sync_interval_display_var.get()
        for label, val in interval_opts:
            if sel == label:
                win._sync_interval_var.set(val)
                break

    int_box.bind("<<ComboboxSelected>>", on_interval_selected)
    sc_row += 1

    sync_btn_bar = ttk.Frame(sched_card)
    sync_btn_bar.grid(row=sc_row, column=0, columnspan=3, sticky=align, padx=10, pady=(8, 4))
    ttk.Button(
        sync_btn_bar,
        text=t("settings.sync_push_btn", "⬆ Push to Cloud"),
        style="Accent.TButton",
        command=win._sync_push,
    ).pack(side=pack_side, padx=(6, 0) if rtl else (0, 6))
    ttk.Button(
        sync_btn_bar,
        text=t("settings.sync_pull_btn", "⬇ Pull from Cloud"),
        command=win._sync_pull,
    ).pack(side=pack_side, padx=6)
    sc_row += 1

    last_time = getattr(win.cfg, "last_sync_time", "") or t("settings.never", "Never")
    win._last_sync_label_var = tk.StringVar(
        value=t("settings.sync_last", "Last sync: {time}", time=last_time)
    )
    ttk.Label(sched_card, textvariable=win._last_sync_label_var, style="Sub.TLabel").grid(
        row=sc_row, column=0, columnspan=3, sticky=align, **pad
    )
    sc_row += 1

    win._sync_status_var = tk.StringVar(value="")
    ttk.Label(sched_card, textvariable=win._sync_status_var, font=get_ui_font(size=9, bold=True, rtl=rtl)).grid(
        row=sc_row, column=0, columnspan=3, sticky=align, **pad
    )
    sc_row += 1

    ttk.Button(
        frm,
        text=t("settings.reset_tab_btn", "↺ Reset tab defaults"),
        command=lambda: win._reset_tab_defaults("sync"),
    ).grid(row=row, column=0, sticky=align, pady=(4, 4))
    row += 1

    return row


__all__ = ["build_sync_section", "do_sync_pull", "do_sync_push"]

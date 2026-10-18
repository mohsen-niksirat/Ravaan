"""Background sync UI builder for SettingsWindow (Gist and WebDAV)."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk
from typing import Any

from ravan.core.i18n import is_rtl, t
from ravan.ui.settings_sync_actions import do_sync_pull, do_sync_push

log = logging.getLogger(__name__)


def build_sync_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    """Build the Cloud Sync settings UI section with Gist and WebDAV support."""
    rtl = is_rtl()
    row = start_row
    align = "e" if rtl else "w"
    pack_side = "right" if rtl else "left"

    ttk.Label(
        frm,
        text=t("settings.sync_header", "Cloud Sync (GitHub Gist / WebDAV)"),
        font=("Segoe UI", 11, "bold"),
    ).grid(row=row, column=0, columnspan=3, sticky=align, pady=(0, 4))
    row += 1

    ttk.Label(
        frm,
        text=t(
            "settings.sync_desc",
            "Sync your user words and snippets securely across PCs via GitHub Gist or WebDAV (Nextcloud).",
        ),
        foreground="#444444",
    ).grid(row=row, column=0, columnspan=3, sticky=align, pady=(0, 8))
    row += 1

    # Backend Selector
    ttk.Label(frm, text=t("settings.sync_backend", "Sync Backend:")).grid(
        row=row, column=0, sticky=align, **pad
    )
    current_backend = getattr(win.cfg, "sync_backend", "gist").lower()
    backend_display = (
        t("settings.sync_backend_webdav", "WebDAV (Nextcloud / ownCloud)")
        if current_backend == "webdav"
        else t("settings.sync_backend_gist", "GitHub Gist")
    )
    win._sync_backend_var = tk.StringVar(value=backend_display)
    backend_box = ttk.Combobox(
        frm,
        textvariable=win._sync_backend_var,
        values=[
            t("settings.sync_backend_gist", "GitHub Gist"),
            t("settings.sync_backend_webdav", "WebDAV (Nextcloud / ownCloud)"),
        ],
        state="readonly",
        width=30,
    )
    backend_box.grid(row=row, column=1, columnspan=2, sticky="w", **pad)
    row += 1

    # Dynamic backend frames container
    container = ttk.Frame(frm)
    container.grid(row=row, column=0, columnspan=3, sticky="we", pady=(4, 4))
    row += 1

    # Frame 1: Gist
    gist_frm = ttk.Frame(container)
    ttk.Label(gist_frm, text=t("settings.sync_pat_label", "Gist Token:")).grid(
        row=0, column=0, sticky=align, **pad
    )
    win._gist_token_var = tk.StringVar(value=getattr(win.cfg, "gist_token", ""))
    token_entry = ttk.Entry(gist_frm, textvariable=win._gist_token_var, width=28, show="*")
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
    ttk.Entry(gist_frm, textvariable=win._gist_id_var, width=28).grid(
        row=1, column=1, sticky="w", **pad
    )
    ttk.Label(
        gist_frm, text=t("settings.gist_url_hint", "Found in gist URL"), foreground="gray"
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
    ttk.Entry(webdav_frm, textvariable=win._webdav_username_var, width=28).grid(
        row=1, column=1, sticky="w", **pad
    )

    ttk.Label(webdav_frm, text=t("settings.sync_webdav_password", "Password:")).grid(
        row=2, column=0, sticky=align, **pad
    )
    win._webdav_password_var = tk.StringVar(value=getattr(win.cfg, "webdav_password", ""))
    pass_entry = ttk.Entry(
        webdav_frm, textvariable=win._webdav_password_var, width=28, show="*"
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

    # Background sync & interval
    win._cloud_sync_var = tk.BooleanVar(value=getattr(win.cfg, "cloud_sync_enabled", False))
    ttk.Checkbutton(
        frm,
        text=t("settings.sync_auto", "Enable automatic background sync"),
        variable=win._cloud_sync_var,
    ).grid(row=row, column=0, columnspan=2, sticky=align, **pad)
    row += 1

    ttk.Label(frm, text=t("settings.sync_interval_label", "Sync Interval:")).grid(
        row=row, column=0, sticky=align, **pad
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
        frm,
        textvariable=win._sync_interval_display_var,
        values=[opt[0] for opt in interval_opts],
        state="readonly",
        width=24,
    )
    int_box.grid(row=row, column=1, sticky="w", **pad)

    def on_interval_selected(_event: object = None) -> None:
        sel = win._sync_interval_display_var.get()
        for label, val in interval_opts:
            if sel == label:
                win._sync_interval_var.set(val)
                break

    int_box.bind("<<ComboboxSelected>>", on_interval_selected)
    row += 1

    # Action buttons
    sync_btn_bar = ttk.Frame(frm)
    sync_btn_bar.grid(row=row, column=0, columnspan=3, sticky=align, pady=(8, 4))
    ttk.Button(
        sync_btn_bar,
        text=t("settings.sync_push_btn", "⬆ Push to Cloud"),
        command=win._sync_push,
    ).pack(side=pack_side, padx=(6, 0) if rtl else (0, 6))
    ttk.Button(
        sync_btn_bar,
        text=t("settings.sync_pull_btn", "⬇ Pull from Cloud"),
        command=win._sync_pull,
    ).pack(side=pack_side, padx=6)
    row += 1

    last_time = getattr(win.cfg, "last_sync_time", "") or t("settings.never", "Never")
    win._last_sync_label_var = tk.StringVar(
        value=t("settings.sync_last", "Last sync: {time}", time=last_time)
    )
    ttk.Label(frm, textvariable=win._last_sync_label_var, foreground="#555555").grid(
        row=row, column=0, columnspan=3, sticky=align, **pad
    )
    row += 1

    win._sync_status_var = tk.StringVar(value="")
    ttk.Label(frm, textvariable=win._sync_status_var, font=("Segoe UI", 9, "bold")).grid(
        row=row, column=0, columnspan=3, sticky=align, **pad
    )
    row += 1

    ttk.Separator(frm, orient="horizontal").grid(
        row=row, column=0, columnspan=3, sticky="we", pady=6
    )
    row += 1

    ttk.Button(
        frm,
        text=t("settings.reset_tab_btn", "↺ Reset tab defaults"),
        command=lambda: win._reset_tab_defaults("sync"),
    ).grid(row=row, column=0, sticky=align, **pad)
    row += 1

    return row


__all__ = ["build_sync_section", "do_sync_pull", "do_sync_push"]

"""Exclusions, Snippets, Sync, and About tab builders for SettingsWindow."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from ravan.core.i18n import is_rtl, t
from ravan.ui.settings_general import _get_win_palette
from ravan.ui.settings_prediction import _style_text_widget
from ravan.ui.theme import get_active_palette, get_ui_font
from ravan.ui.widgets import FluentCard, FluentPillButton, FluentSectionBanner


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
    banner = FluentSectionBanner(
        frm, "shield", t("settings.tab_exclusions", "Excluded Apps"), sub, palette, rtl
    )
    banner.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    row += 1

    excl_card = FluentCard(
        frm, t("settings.excl_header", "Excluded apps (one per line)"), padding=12, palette=palette, rtl=rtl, icon="shield"
    )
    excl_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    excl_card.columnconfigure(0, weight=1)
    row += 1

    win._excl_text = tk.Text(excl_card, width=48, height=6)
    _style_text_widget(win._excl_text, palette, rtl=False)
    win._excl_text.insert("1.0", "\n".join(win.cfg.excluded_apps))
    win._excl_text.grid(row=0, column=0, columnspan=3, sticky="ew", **pad)

    excl_tools = tk.Frame(excl_card, bg=palette.bg_surface)
    excl_tools.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=(6, 4))

    pack_side = "right" if rtl else "left"
    win._detected_app_var = tk.StringVar(value=t("settings.active_app", "Active app: {app}", app="—"))
    ttk.Label(excl_tools, textvariable=win._detected_app_var, style="CardSub.TLabel").pack(
        side=pack_side, padx=(8, 0) if rtl else (0, 8)
    )
    FluentPillButton(
        excl_tools,
        text=t("settings.detect_active_app", "Detect Active App"),
        icon="search",
        variant="secondary",
        palette=palette,
        rtl=rtl,
        command=win._detect_active_app,
    ).pack(side=pack_side, padx=3)
    win._add_detected_btn = FluentPillButton(
        excl_tools,
        text=t("settings.add_to_exclusions", "+ Add to Exclusions"),
        variant="primary",
        palette=palette,
        rtl=rtl,
        state="disabled",
        command=win._add_detected_to_exclusions,
    )
    win._add_detected_btn.pack(side=pack_side, padx=3)
    FluentPillButton(
        excl_tools,
        text=t("settings.btn_pick_window", "Pick Window…"),
        variant="secondary",
        palette=palette,
        rtl=rtl,
        command=win._open_window_picker,
    ).pack(side=pack_side, padx=3)

    FluentPillButton(
        frm,
        text=t("settings.reset_tab_btn", "Reset tab defaults").replace("↺", "").strip(),
        icon="reset",
        variant="secondary",
        palette=palette,
        rtl=rtl,
        parent_bg=palette.bg_base,
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
    banner = FluentSectionBanner(
        frm, "code", t("settings.snippets_header", "Snippets"), sub, palette, rtl
    )
    banner.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    row += 1

    snip_card = FluentCard(
        frm, t("settings.snippets_header", "Snippets"), padding=12, palette=palette, rtl=rtl, icon="code"
    )
    snip_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    snip_card.columnconfigure(0, weight=1)
    row += 1

    snip_hdr = tk.Frame(snip_card, bg=palette.bg_surface)
    snip_hdr.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 6))
    FluentPillButton(
        snip_hdr,
        text=t("settings.snippets_editor_btn", "Open Snippet Editor…"),
        icon="code",
        variant="primary",
        palette=palette,
        rtl=rtl,
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

    FluentPillButton(
        snip_hdr,
        text=t("packages.import_btn", "Import Package…"),
        icon="hub",
        variant="secondary",
        palette=palette,
        rtl=rtl,
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

    from ravan.ui.hub_browser import RavaanHubPanel

    win._hub_browser = RavaanHubPanel(frm, win, palette=palette, rtl=rtl)
    win._hub_browser.card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    row += 1

    FluentPillButton(
        frm,
        text=t("settings.reset_tab_btn", "Reset tab defaults").replace("↺", "").strip(),
        icon="reset",
        variant="secondary",
        palette=palette,
        rtl=rtl,
        parent_bg=palette.bg_base,
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

    hero = FluentSectionBanner(
        frm,
        "feather",
        t("settings.about_title", "Ravaan (روان)"),
        t("settings.about_subtitle", "Windows typing assistant for bilingual Persian/English typists"),
        palette,
        rtl,
    )
    hero.pack(fill="x", pady=(0, 10))

    info_card = FluentCard(
        frm,
        "ℹ️ مشخصات و حریم خصوصی" if rtl else "ℹ️ Version & Privacy Guarantee",
        padding=12,
        palette=palette,
        rtl=rtl,
        icon="info",
    )
    info_card.pack(fill="x", pady=(0, 10))

    ttk.Label(
        info_card,
        text=t("settings.about_version", "Version {version} — MIT License", version=__version__),
        style="Card.TLabel",
        font=get_ui_font(size=9, bold=True, rtl=rtl),
    ).pack(anchor=anchor, pady=(0, 4))
    ttk.Label(
        info_card,
        text=t("settings.about_github", "GitHub: https://github.com/mohsen-niksirat/Ravaan"),
        style="Card.TLabel",
        foreground=palette.accent,
    ).pack(anchor=anchor, pady=(0, 4))
    ttk.Label(
        info_card,
        text=t("settings.about_data_privacy", "Data & Privacy: 100% local-first, DPAPI-encrypted (see DATA.md)"),
        style="Card.TLabel",
        foreground=palette.success,
    ).pack(anchor=anchor, pady=(0, 4))

    feat_card = FluentCard(
        frm,
        "✨ قابلیت‌های کلیدی" if rtl else "✨ Key Capabilities",
        padding=12,
        palette=palette,
        rtl=rtl,
        icon="sparkle",
    )
    feat_card.pack(fill="x", pady=(0, 6))

    features_text = t(
        "settings.about_features",
        "Key Features:\n• Layout Conversion (Pause)\n• Word Prediction & Autocorrect\n• Smart Half-Space (ZWNJ)\n• Clipboard History (Alt+V)\n• Quick Text Stats (Ctrl+Alt+S)\n• Math & Jalali Macros\n• Snippets 2.0 & Cloud Sync\n• Data Manifest & Zero Telemetry",
    )
    ttk.Label(feat_card, text=features_text, style="Card.TLabel", justify=justify).pack(anchor=anchor, pady=2)

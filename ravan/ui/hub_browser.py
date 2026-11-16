"""Searchable Fluent 2 Ravaan Hub (.ravaanpack) community pack browser card grid."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from typing import Any

from ravan.core.hub import HUB_CATEGORIES, HubManager, HubPack
from ravan.core.i18n import is_rtl, t
from ravan.ui.hub_preview_modal import get_hub_badge_colors, open_hub_preview_modal
from ravan.ui.theme import Palette, get_active_palette, get_ui_font
from ravan.ui.widgets import FluentBadge, FluentCard, FluentEntry, FluentPillButton


class RavaanHubPanel:
    """Embeddable Fluent 2 card grid browser for discovering and installing `.ravaanpack` bundles."""

    def __init__(
        self,
        parent: tk.Misc,
        win: Any,
        *,
        palette: Palette | None = None,
        rtl: bool | None = None,
        manager: HubManager | None = None,
    ) -> None:
        self.parent = parent
        self.win = win
        self.palette = palette or get_active_palette(getattr(getattr(win, "cfg", None), "theme_mode", "auto"))
        self.rtl = is_rtl() if rtl is None else rtl
        self.manager = manager or HubManager()

        self._selected_category = "all"
        self._packs: list[HubPack] = []
        self._cat_buttons: dict[str, FluentPillButton] = {}
        self._search_var = tk.StringVar(value="")
        self._status_var = tk.StringVar(value="")
        self._preview_win: tk.Toplevel | None = None

        self.card = FluentCard(
            parent,
            t("hub.card_title", "مخزن بسته‌های آماده (Ravaan Hub)" if self.rtl else "Ravaan Hub — Community Snippet Packs"),
            padding=12, palette=self.palette, rtl=self.rtl, icon="hub",
        )
        self.card.columnconfigure(0, weight=1)
        self._build_controls()
        self._cards_frame = tk.Frame(self.card, bg=self.palette.bg_surface)
        self._cards_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 2))
        self._cards_frame.columnconfigure(0, weight=1, uniform="hubcol")
        self._cards_frame.columnconfigure(1, weight=1, uniform="hubcol")

        self._packs = self.manager.fetch_index(force_refresh=False)
        self._render_cards()

    def _build_controls(self) -> None:
        p, rtl = self.palette, self.rtl
        lead, trail = ("right", "left") if rtl else ("left", "right")

        top_bar = tk.Frame(self.card, bg=p.bg_surface)
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        self._search_entry = FluentEntry(
            top_bar, textvariable=self._search_var,
            placeholder=t("hub.search_placeholder", "جستجو در بسته‌های آماده..." if rtl else "Search community packs..."),
            width=26, palette=p, rtl=rtl, leading_icon="search", clearable=True,
        )
        self._search_entry.pack(side=lead, fill="x", expand=True, padx=(8, 0) if rtl else (0, 8))
        self._search_var.trace_add("write", lambda *_: self._render_cards())

        self._btn_refresh = FluentPillButton(
            top_bar, text=t("hub.refresh_btn", "بروزرسانی فهرست" if rtl else "Refresh"),
            icon="cloud", variant="secondary", palette=p, rtl=rtl, parent_bg=p.bg_surface,
            height=28, width=118, command=self.refresh_index,
        )
        self._btn_refresh.pack(side=lead, padx=2)
        tk.Label(
            top_bar, textvariable=self._status_var, bg=p.bg_surface, fg=p.subtext,
            font=get_ui_font(size=8, rtl=rtl),
        ).pack(side=trail, padx=6)

        cat_bar = tk.Frame(self.card, bg=p.bg_surface)
        cat_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        cats = list(reversed(HUB_CATEGORIES)) if rtl else list(HUB_CATEGORIES)
        for cid, lbl_fa, lbl_en in cats:
            lbl = t(f"hub.cat_{cid}", lbl_fa if rtl else lbl_en)
            bw = max(78, len(lbl) * (6 if rtl else 7) + 22)
            btn = FluentPillButton(
                cat_bar, text=lbl, variant="primary" if cid == self._selected_category else "secondary",
                palette=p, rtl=rtl, parent_bg=p.bg_surface, height=26, width=bw,
                command=lambda c=cid: self.select_category(c),
            )
            btn.pack(side="right" if rtl else "left", padx=2)
            self._cat_buttons[cid] = btn

    def select_category(self, category_id: str) -> None:
        self._selected_category = category_id
        for cid, btn in self._cat_buttons.items():
            btn.configure(variant="primary" if cid == category_id else "secondary")
        self._render_cards()

    def filtered_packs(self) -> list[HubPack]:
        q = (self._search_entry.get() if hasattr(self, "_search_entry") else self._search_var.get()).strip().lower()
        out: list[HubPack] = []
        for pack in self._packs:
            if self._selected_category != "all" and pack.category != self._selected_category:
                continue
            if q:
                hay = " ".join([pack.pack_id, pack.title_en, pack.title_fa, pack.description_en, pack.description_fa, *pack.tags]).lower()
                if q not in hay:
                    continue
            out.append(pack)
        return out

    def _render_cards(self) -> None:
        for ch in self._cards_frame.winfo_children():
            ch.destroy()
        p, rtl = self.palette, self.rtl
        packs = self.filtered_packs()
        if not packs:
            ttk.Label(
                self._cards_frame, text=t("hub.no_matches", "بسته‌ای با این مشخصات یافت نشد." if rtl else "No matching packs found."),
                style="CardSub.TLabel",
            ).grid(row=0, column=0, columnspan=2, pady=12)
            return

        for idx, pack in enumerate(packs):
            row_i = idx // 2
            col_i = (1 - (idx % 2)) if rtl else (idx % 2)
            self._build_pack_card(pack, row_i, col_i, p, rtl)

    def _build_pack_card(self, pack: HubPack, row_i: int, col_i: int, p: Palette, rtl: bool) -> None:
        lead, trail = ("right", "left") if rtl else ("left", "right")
        anchor, justify = ("e", "right") if rtl else ("w", "left")
        installed = self.manager.is_installed(pack.pack_id)
        has_upd = self.manager.has_update(pack)

        card = tk.Frame(
            self._cards_frame, bg=p.bg_elevated, highlightthickness=1,
            highlightbackground=p.border_focus if has_upd else p.border_subtle, padx=12, pady=10,
        )
        card.grid(row=row_i, column=col_i, sticky="nsew", padx=4, pady=4)

        title = pack.title_fa if rtl else pack.title_en
        tk.Label(
            card, text=title, bg=p.bg_elevated, fg=p.fg,
            font=get_ui_font(size=10, bold=True, rtl=rtl), anchor=anchor, justify=justify,
        ).pack(fill="x", pady=(0, 3))

        badge_row = tk.Frame(card, bg=p.bg_elevated)
        badge_row.pack(fill="x", pady=(0, 5))
        FluentBadge(badge_row, text=f"v{pack.version}", palette=p, parent_bg=p.bg_elevated, rtl=rtl).pack(side=lead, padx=(0, 4) if not rtl else (4, 0))
        if pack.verified:
            v_bg, v_fg = get_hub_badge_colors(p)
            FluentBadge(
                badge_row, text=t("hub.sha_verified", "SHA-256 ✓"), palette=p,
                bg_color=v_bg, fg_color=v_fg, parent_bg=p.bg_elevated, rtl=rtl,
            ).pack(side=lead, padx=2)

        desc = pack.description_fa if rtl else pack.description_en
        tk.Label(
            card, text=desc, bg=p.bg_elevated, fg=p.subtext, wraplength=280,
            font=get_ui_font(size=8, rtl=rtl), anchor=anchor, justify=justify,
        ).pack(fill="x", pady=(0, 6))

        meta_lbl = (
            f"{pack.snippet_count} میانبر  ·  {pack.author}"
            if rtl
            else f"{pack.snippet_count} snippets  ·  {pack.author}"
        )
        tk.Label(card, text=meta_lbl, bg=p.bg_elevated, fg=p.subtext, font=get_ui_font(size=8, rtl=rtl), anchor=anchor).pack(fill="x", pady=(0, 8))

        act_row = tk.Frame(card, bg=p.bg_elevated)
        act_row.pack(fill="x")
        FluentPillButton(
            act_row, text=t("hub.btn_preview", "پیش‌نمایش" if rtl else "Preview"),
            icon="eye", variant="ghost", palette=p, rtl=rtl, parent_bg=p.bg_elevated,
            height=26, width=96, command=lambda pk=pack: self._open_preview(pk),
        ).pack(side=lead)

        if has_upd:
            btn_txt, btn_var, btn_ic, cmd = t("hub.btn_update_short", "بروزرسانی" if rtl else "Update"), "primary", "replace", lambda pk=pack: self.install_pack(pk)
        elif installed:
            btn_txt, btn_var, btn_ic, cmd = t("hub.btn_uninstall", "حذف" if rtl else "Uninstall"), "danger", "close", lambda pk=pack: self.uninstall_pack(pk)
        else:
            btn_txt, btn_var, btn_ic, cmd = t("hub.btn_install_short", "نصب" if rtl else "Install"), "primary", "check", lambda pk=pack: self.install_pack(pk)

        FluentPillButton(
            act_row, text=btn_txt, icon=btn_ic, variant=btn_var, palette=p, rtl=rtl,
            parent_bg=p.bg_elevated, height=26, width=102, command=cmd,
        ).pack(side=trail)

    def _schedule_ui(self, fn: Any) -> None:
        if self.card.winfo_exists():
            try:
                self.card.after(0, fn)
            except Exception:
                pass

    def refresh_index(self) -> None:
        self._status_var.set(t("hub.refreshing", "در حال دریافت..." if self.rtl else "Refreshing..."))

        def _worker() -> None:
            packs = self.manager.fetch_index(force_refresh=True)
            self._schedule_ui(lambda: self._on_index_loaded(packs))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_index_loaded(self, packs: list[HubPack]) -> None:
        self._packs = packs
        self._status_var.set(f"{len(packs)} " + t("hub.packs_count", "بسته" if self.rtl else "packs"))
        self._render_cards()

    def _open_preview(self, pack: HubPack) -> None:
        self._preview_win = open_hub_preview_modal(
            getattr(self.win, "_root", None),
            pack,
            installed=self.manager.is_installed(pack.pack_id),
            has_update=self.manager.has_update(pack),
            on_install=self.install_pack,
            on_uninstall=self.uninstall_pack,
            theme_mode=getattr(getattr(self.win, "cfg", None), "theme_mode", "auto"),
        )

    def install_pack(self, pack: HubPack) -> None:
        self._status_var.set(t("hub.installing", "در حال نصب و بررسی SHA-256..." if self.rtl else "Installing & verifying..."))
        existing = list(getattr(self.win, "_managed_snippets", []))
        groups = list(getattr(getattr(self.win, "cfg", None), "snippet_groups", []) or [])

        def _worker() -> None:
            try:
                new_snips, new_groups, _manifest = self.manager.install_pack(pack, existing, groups)
                self._schedule_ui(lambda: self._apply_pack_changes(new_snips, new_groups, pack, installed=True))
            except Exception as exc:  # noqa: BLE001
                err = str(exc)[:60]
                self._schedule_ui(lambda m=err: self._status_var.set(m))

        threading.Thread(target=_worker, daemon=True).start()

    def uninstall_pack(self, pack: HubPack) -> None:
        existing = list(getattr(self.win, "_managed_snippets", []))
        new_snips = self.manager.uninstall_pack(pack.pack_id, existing)
        groups = list(getattr(getattr(self.win, "cfg", None), "snippet_groups", []) or [])
        self._apply_pack_changes(new_snips, groups, pack, installed=False)

    def _apply_pack_changes(self, new_snips: list[Any], new_groups: list[Any], pack: HubPack, *, installed: bool) -> None:
        self.win._managed_snippets = new_snips
        if getattr(self.win, "cfg", None) is not None:
            self.win.cfg.snippets = list(new_snips)
            self.win.cfg.snippet_groups = list(new_groups)
        if hasattr(self.win, "_update_snip_display"):
            self.win._update_snip_display()
        title = pack.title_fa if self.rtl else pack.title_en
        msg = (
            f"✓ {title}" if installed else f"{t('hub.uninstalled', 'حذف شد:' if self.rtl else 'Uninstalled:')} {title}"
        )
        self._status_var.set(msg)
        self._render_cards()

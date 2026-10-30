"""Quick tips, shortcuts cheat sheet, and in-app help guide window for Ravaan."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk
from typing import Any

from ravan.core.config import Config
from ravan.core.i18n import is_rtl, t
from ravan.ui.theme import (
    apply_theme_to_ttk,
    apply_window_decorations,
    get_active_palette,
    get_ui_font,
)

log = logging.getLogger(__name__)


def _get_tips_data() -> list[dict[str, Any]]:
    """Return categorized quick tips with bilingual localized strings."""
    return [
        {
            "category": t("tips.cat_shortcuts", "Essential Keyboard Shortcuts"),
            "items": [
                {
                    "badge": "Pause",
                    "title": t("tips.hk_convert_title", "Reverse Mis-typed Layout"),
                    "desc": t(
                        "tips.hk_convert_desc",
                        "Instantly converts the last word or selected text between Persian and English (e.g. 'sghl' ↔ 'سلام').",
                    ),
                    "tags": ["pause", "layout", "convert", "چیدمان", "تبدیل"],
                },
                {
                    "badge": "Shift + Space",
                    "title": t("tips.hk_zwnj_title", "Persian Half-Space (ZWNJ)"),
                    "desc": t(
                        "tips.hk_zwnj_desc",
                        "Inserts a standard zero-width non-joiner (نیم‌فاصله) in any application (e.g. 'می‌روم', 'کتاب‌ها').",
                    ),
                    "tags": ["shift", "space", "zwnj", "half-space", "نیم فاصله", "فاصله"],
                },
                {
                    "badge": "Ctrl + Shift + Z",
                    "title": t("tips.hk_undo_title", "Instant Undo Correction"),
                    "desc": t(
                        "tips.hk_undo_desc",
                        "Reverts the last auto-correction or layout conversion back to exactly what you typed.",
                    ),
                    "tags": ["undo", "revert", "لغو", "برگشت"],
                },
                {
                    "badge": "Alt + V",
                    "title": t("tips.hk_clip_title", "Clipboard History Popup"),
                    "desc": t(
                        "tips.hk_clip_desc",
                        "Opens recent clipboard clips right at your caret. Press 1–5 or use arrows to paste instantly.",
                    ),
                    "tags": ["clipboard", "paste", "history", "کلیپ بورد", "تاریخچه"],
                },
                {
                    "badge": "Ctrl + Alt + S",
                    "title": t("tips.hk_stats_title", "Quick Text Statistics"),
                    "desc": t(
                        "tips.hk_stats_desc",
                        "Shows word count, character count, and estimated reading time for selected text.",
                    ),
                    "tags": ["stats", "word count", "آمار", "کلمات", "تعداد"],
                },
                {
                    "badge": "Ctrl + Alt + Pause",
                    "title": t("tips.hk_pause_title", "Pause / Resume Ravaan"),
                    "desc": t(
                        "tips.hk_pause_desc",
                        "Temporarily pauses Ravaan assistance (for 10 minutes) or resumes it immediately.",
                    ),
                    "tags": ["pause", "resume", "stop", "مکث", "ادامه"],
                },
                {
                    "badge": "Ctrl + Shift + F12",
                    "title": t("tips.hk_clean_title", "Clean Clipboard Text"),
                    "desc": t(
                        "tips.hk_clean_desc",
                        "Standardizes Persian characters (ي/ك to ی/ک), removes extra spaces, and fixes half-spaces on clipboard.",
                    ),
                    "tags": ["clean", "normalize", "پاکسازی", "استاندارد"],
                },
            ],
        },
        {
            "category": t("tips.cat_features", "Smart Everyday Features"),
            "items": [
                {
                    "badge": "Smart ZWNJ",
                    "title": t("tips.feat_zwnj_title", "Automatic Half-Spacing"),
                    "desc": t(
                        "tips.feat_zwnj_desc",
                        "Automatically places half-spaces for Persian prefixes (می/نمی) and suffixes (ها/تر/ترین/هایم).",
                    ),
                    "tags": ["zwnj", "prefixes", "suffixes", "نیم فاصله", "پیشوند", "پسوند"],
                },
                {
                    "badge": "Calc on '='",
                    "title": t("tips.feat_calc_title", "Inline Quick Calculator"),
                    "desc": t(
                        "tips.feat_calc_desc",
                        "Type any math expression ending with '=' (e.g. '2500*4=' or '1200*1.09=') to replace with the answer.",
                    ),
                    "tags": ["calculator", "math", "حساب", "محاسبه", "ریاضی"],
                },
                {
                    "badge": "Auto-Fix",
                    "title": t("tips.feat_autofix_title", "Automatic Wrong-Layout Detection"),
                    "desc": t(
                        "tips.feat_autofix_desc",
                        "Detects when you type Persian words with English layout active (e.g. 'sghl ') and fixes them automatically.",
                    ),
                    "tags": ["autofix", "wrong layout", "تشخیص خودکار", "چیدمان اشتباه"],
                },
                {
                    "badge": "Snippets",
                    "title": t("tips.feat_snip_title", "Text Snippets (Shortcuts)"),
                    "desc": t(
                        "tips.feat_snip_desc",
                        "Type customizable triggers like ';email' or ';addr' to expand into full text templates anywhere.",
                    ),
                    "tags": ["snippets", "macro", "متن آماده", "میانبر"],
                },
                {
                    "badge": "Finglish",
                    "title": t("tips.feat_translit_title", "Phonetic Finglish Typing"),
                    "desc": t(
                        "tips.feat_translit_desc",
                        "Press Ctrl+Alt+T to type Persian words using English letters phonetically ('salam' → 'سلام').",
                    ),
                    "tags": ["finglish", "transliteration", "فینگلیش", "فارسی"],
                },
            ],
        },
        {
            "category": t("tips.cat_trust", "Privacy, Safety & Peace of Mind"),
            "items": [
                {
                    "badge": "100% Local",
                    "title": t("tips.trust_privacy_title", "Zero Keystroke Logging"),
                    "desc": t(
                        "tips.trust_privacy_desc",
                        "Ravaan operates 100% offline on your PC. No keystrokes or typed words are ever recorded or sent anywhere.",
                    ),
                    "tags": ["privacy", "offline", "امنیت", "حریم خصوصی"],
                },
                {
                    "badge": "Password Safe",
                    "title": t("tips.trust_pwd_title", "Automatic Password Suppression"),
                    "desc": t(
                        "tips.trust_pwd_desc",
                        "All popups and keystroke handling automatically suspend whenever a password field is active.",
                    ),
                    "tags": ["password", "suppression", "رمز عبور", "امنیت"],
                },
                {
                    "badge": "Tray Menu",
                    "title": t("tips.trust_tray_title", "One-Click Controls"),
                    "desc": t(
                        "tips.trust_tray_desc",
                        "Right-click the Ravaan tray icon near the Windows clock to pause, toggle features, or open Settings.",
                    ),
                    "tags": ["tray", "menu", "آیکون", "سینی سیستم"],
                },
            ],
        },
    ]


class QuickTipsWindow:
    """Friendly in-app tips and shortcuts reference window."""

    def __init__(self, parent: tk.Misc | None = None, cfg: Config | None = None) -> None:
        self.cfg = cfg or Config()
        self.parent = parent
        self._top: tk.Toplevel | None = None
        self._search_var: tk.StringVar | None = None
        self._items_container: ttk.Frame | None = None
        self._card_widgets: list[tuple[dict[str, Any], ttk.Frame]] = []
        self._no_results_lbl: ttk.Label | None = None

    def show(self) -> None:
        """Create or bring to front the Quick Tips window."""
        if self._top is not None and self._top.winfo_exists():
            self._top.deiconify()
            self._top.lift()
            self._top.focus_force()
            return

        rtl = is_rtl()
        p = get_active_palette(getattr(self.cfg, "theme_mode", "auto"))

        top = tk.Toplevel(self.parent) if isinstance(self.parent, tk.Misc) else tk.Tk()
        top.title(t("tips.window_title", "Ravaan — Quick Tips & Shortcuts"))
        top.geometry("640x560")
        top.minsize(540, 420)
        top.configure(bg=p.bg)
        apply_window_decorations(top, p)
        apply_theme_to_ttk(top, p)

        # Center on screen
        try:
            top.update_idletasks()
            sw = top.winfo_screenwidth()
            sh = top.winfo_screenheight()
            x = max(20, (sw - 640) // 2)
            y = max(20, (sh - 560) // 2)
            top.geometry(f"+{x}+{y}")
        except Exception:
            pass

        # Header Frame
        hdr = ttk.Frame(top, padding=(16, 14, 16, 8))
        hdr.pack(fill="x")

        title_lbl = ttk.Label(
            hdr,
            text=t("tips.header_title", "💡 Quick Tips & Shortcuts"),
            font=get_ui_font(size=14, bold=True, rtl=rtl),
        )
        title_lbl.pack(anchor="e" if rtl else "w")

        sub_lbl = ttk.Label(
            hdr,
            text=t("tips.header_subtitle", "Everything you need to type faster and more comfortably with Ravaan."),
            font=get_ui_font(size=9, bold=False, rtl=rtl),
            foreground="gray",
        )
        sub_lbl.pack(anchor="e" if rtl else "w", pady=(2, 8))

        # Search bar
        search_frm = ttk.Frame(hdr)
        search_frm.pack(fill="x", pady=(2, 6))

        pack_side = "right" if rtl else "left"
        ttk.Label(
            search_frm,
            text=t("tips.search_label", "🔍 Search:"),
            font=get_ui_font(size=9, bold=True, rtl=rtl),
        ).pack(side=pack_side, padx=(6, 4) if rtl else (0, 6))

        self._search_var = tk.StringVar(value="")
        entry = ttk.Entry(search_frm, textvariable=self._search_var)
        entry.pack(side=pack_side, fill="x", expand=True)
        ttk.Button(
            search_frm,
            text="✕",
            width=3,
            command=lambda: self._search_var.set("") if self._search_var else None,
        ).pack(side=pack_side, padx=(4, 0))

        # Scrollable area
        canvas_frm = ttk.Frame(top, padding=(16, 0, 16, 8))
        canvas_frm.pack(fill="both", expand=True)

        canvas = tk.Canvas(canvas_frm, bg=p.card_bg, highlightthickness=1, highlightbackground=p.border)
        v_scroll = ttk.Scrollbar(canvas_frm, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=v_scroll.set)

        v_scroll.pack(side="left" if rtl else "right", fill="y")
        canvas.pack(side="right" if rtl else "left", fill="both", expand=True)

        items_container = ttk.Frame(canvas, padding=12)
        win_id = canvas.create_window((0, 0), window=items_container, anchor="nw")

        def _on_canvas_configure(e: tk.Event) -> None:
            canvas.itemconfig(win_id, width=e.width)

        def _on_frame_configure(_e: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        canvas.bind("<Configure>", _on_canvas_configure)
        items_container.bind("<Configure>", _on_frame_configure)

        # Mousewheel scrolling
        def _on_mousewheel(e: tk.Event) -> None:
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._items_container = items_container
        self._card_widgets.clear()

        # Build cards
        tips_data = _get_tips_data()
        for cat in tips_data:
            cat_lbl = ttk.Label(
                items_container,
                text=f"📌 {cat['category']}",
                font=get_ui_font(size=11, bold=True, rtl=rtl),
            )
            cat_lbl.pack(anchor="e" if rtl else "w", pady=(10, 6), fill="x")

            for item in cat["items"]:
                card = ttk.Frame(items_container, padding=(12, 10), style="Card.TFrame")
                card.pack(fill="x", pady=4, anchor="e" if rtl else "w")

                top_row = ttk.Frame(card, style="Card.TFrame")
                top_row.pack(fill="x")

                badge = tk.Label(
                    top_row,
                    text=f" {item['badge']} ",
                    bg=p.badge_bg,
                    fg=p.badge_fg,
                    font=get_ui_font(size=8, bold=True),
                    relief="solid",
                    bd=1,
                    padx=6,
                    pady=2,
                )
                badge.pack(side="right" if rtl else "left", padx=(0, 6) if not rtl else (6, 0))

                title = ttk.Label(
                    top_row,
                    text=item["title"],
                    font=get_ui_font(size=10, bold=True, rtl=rtl),
                )
                title.pack(side="right" if rtl else "left", fill="x", expand=True)

                desc = ttk.Label(
                    card,
                    text=item["desc"],
                    font=get_ui_font(size=9, bold=False, rtl=rtl),
                    wraplength=520,
                    justify="right" if rtl else "left",
                )
                desc.pack(anchor="e" if rtl else "w", pady=(4, 0))

                self._card_widgets.append((item, card))

        self._no_results_lbl = ttk.Label(
            items_container,
            text=t("tips.no_results", "No tips match your search."),
            font=get_ui_font(size=10, bold=False, rtl=rtl),
            foreground="gray",
        )

        # Search filter callback
        def _filter_cards(*_args: Any) -> None:
            q = (self._search_var.get() if self._search_var else "").strip().lower()
            visible_count = 0
            for item, card in self._card_widgets:
                matches = (
                    not q
                    or q in item["badge"].lower()
                    or q in item["title"].lower()
                    or q in item["desc"].lower()
                    or any(q in tag.lower() for tag in item.get("tags", []))
                )
                if matches:
                    card.pack(fill="x", pady=4, anchor="e" if rtl else "w")
                    visible_count += 1
                else:
                    card.pack_forget()

            if visible_count == 0:
                if self._no_results_lbl:
                    self._no_results_lbl.pack(pady=20)
            else:
                if self._no_results_lbl:
                    self._no_results_lbl.pack_forget()

        self._search_var.trace_add("write", _filter_cards)

        # Footer Frame
        footer = ttk.Frame(top, padding=(16, 8, 16, 12))
        footer.pack(fill="x", side="bottom")

        btn_close = ttk.Button(
            footer,
            text=t("tips.btn_close", "Close (Esc)"),
            command=self.close,
        )
        btn_close.pack(side="left" if rtl else "right")

        top.bind("<Escape>", lambda _e: self.close())
        top.protocol("WM_DELETE_WINDOW", self.close)

        self._top = top
        top.focus_set()

    def tick(self) -> None:
        """Periodic tick for maintaining window event loop if standalone."""
        if self._top is not None and self._top.winfo_exists():
            try:
                self._top.update()
            except Exception:
                pass

    def close(self) -> None:
        """Close the Quick Tips window cleanly."""
        if self._top is not None:
            try:
                self._top.destroy()
            except Exception:
                pass
            self._top = None

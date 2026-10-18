"""First-Run Onboarding Wizard (Milestone M16 / Phase 3).

A single-screen, friendly 20-second intro modal for new users:
- UI language selector (Persian / English)
- 5 essential hotkeys tour card
- "Get Started" and "Skip" buttons
- Keyboard accessible (Return / Escape)
"""

from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable

from ravan.core.config import Config, save_config
from ravan.core.i18n import get_locale, is_rtl, set_locale
from ravan.ui.theme import get_active_palette, get_ui_font

log = logging.getLogger(__name__)

_HOTKEYS_FA = [
    ("F12", "تغییر چیدمان متن اشتباه تایپ‌شده (fa ↔ en)"),
    ("Shift + Space", "درج نیم‌فاصله هوشمند (ZWNJ)"),
    ("Alt + L", "تصحیح چیدمان آخرین کلمهٔ تایپ‌شده"),
    ("Alt + V", "تاریخچه و جست‌وجوی کلیپ‌بورد"),
    ("Ctrl + Alt + P", "مکث موقت یا ادامهٔ فعالیت روان"),
]

_HOTKEYS_EN = [
    ("F12", "Reverse layout of mis-typed text (fa ↔ en)"),
    ("Shift + Space", "Insert zero-width non-joiner (smart ZWNJ)"),
    ("Alt + L", "Fix layout of last typed word"),
    ("Alt + V", "Clipboard history and search"),
    ("Ctrl + Alt + P", "Pause or resume Ravaan"),
]


class FirstRunWizard:
    """Friendly single-screen onboarding wizard for first-time launch."""

    def __init__(
        self,
        cfg: Config,
        on_complete: Callable[[], None] | None = None,
        parent: tk.Tk | tk.Toplevel | None = None,
    ) -> None:
        self.cfg = cfg
        self.on_complete = on_complete
        self.parent = parent
        self._open = False
        self._built = False
        self._root: tk.Toplevel | None = None
        self._lang_var: tk.StringVar | None = None

    @property
    def open(self) -> bool:
        return self._open

    def show(self) -> None:
        self._open = True

    def tick(self) -> None:
        if not self._open:
            return
        if not self._built:
            self._build()
            self._built = True
        if self._root is None:
            return
        try:
            self._root.update_idletasks()
            self._root.update()
        except (tk.TclError, RuntimeError):
            pass

    def _close(self, completed: bool = True) -> None:
        self.cfg.has_seen_onboarding = True
        if self._lang_var is not None:
            self.cfg.language = self._lang_var.get()
            set_locale(self.cfg.language)
        save_config(self.cfg)
        self._open = False
        if self._root is not None:
            try:
                self._root.destroy()
            except tk.TclError:
                pass
            self._root = None
        if self.on_complete is not None:
            try:
                self.on_complete()
            except Exception:  # noqa: BLE001
                pass

    def _build(self) -> None:
        palette = get_active_palette()
        parent = self.parent or tk._default_root
        win = tk.Toplevel(parent) if parent is not None else tk.Toplevel()
        self._root = win
        win.title("Welcome to Ravaan • به روان خوش آمدید")
        win.geometry("540x510")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.configure(bg=palette.bg)
        win.protocol("WM_DELETE_WINDOW", lambda: self._close(completed=False))

        # Center on screen
        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        px = max(20, (sw - 540) // 2)
        py = max(20, (sh - 510) // 2)
        win.geometry(f"540x510+{px}+{py}")

        current_lang = self.cfg.language if self.cfg.language in ("fa", "en") else get_locale()
        self._lang_var = tk.StringVar(value=current_lang)

        self._container = tk.Frame(win, bg=palette.bg, padx=24, pady=20)
        self._container.pack(fill="both", expand=True)

        self._render_content()

        # Keyboard shortcuts
        win.bind("<Return>", lambda _: self._close(completed=True))
        win.bind("<Escape>", lambda _: self._close(completed=False))
        win.focus_set()

    def _on_lang_changed(self) -> None:
        if self._lang_var is None:
            return
        new_lang = self._lang_var.get()
        set_locale(new_lang)
        self.cfg.language = new_lang
        for widget in self._container.winfo_children():
            widget.destroy()
        self._render_content()

    def _render_content(self) -> None:
        palette = get_active_palette()
        rtl = is_rtl()
        align = "e" if rtl else "w"
        f_title = get_ui_font(size=14, bold=True, rtl=rtl)
        f_sub = get_ui_font(size=10, bold=False, rtl=rtl)
        f_hk_key = get_ui_font(size=9, bold=True, rtl=False)
        f_hk_desc = get_ui_font(size=9, bold=False, rtl=rtl)
        f_btn = get_ui_font(size=10, bold=True, rtl=rtl)

        # Header Frame
        hdr = tk.Frame(self._container, bg=palette.bg)
        hdr.pack(fill="x", pady=(0, 10))

        title_text = "✨ به برنامهٔ روان خوش آمدید!" if rtl else "✨ Welcome to Ravaan!"
        tk.Label(
            hdr,
            text=title_text,
            font=f_title,
            bg=palette.bg,
            fg=palette.accent,
        ).pack(anchor=align)

        sub_text = (
            "دستیار هوشمند و سبک کیبورد و تایپ فارسی برای ویندوز"
            if rtl
            else "Lightweight intelligent Persian typing assistant for Windows"
        )
        tk.Label(
            hdr,
            text=sub_text,
            font=f_sub,
            bg=palette.bg,
            fg=palette.subtext,
        ).pack(anchor=align, pady=(2, 0))

        # Language selector bar
        lang_bar = tk.Frame(
            self._container,
            bg=palette.card_bg,
            highlightbackground=palette.border,
            highlightthickness=1,
            padx=12,
            pady=8,
        )
        lang_bar.pack(fill="x", pady=10)

        lang_label = "زبان رابط کاربری:" if rtl else "Interface Language:"
        tk.Label(
            lang_bar,
            text=lang_label,
            font=f_sub,
            bg=palette.card_bg,
            fg=palette.fg,
        ).pack(side="right" if rtl else "left", padx=(0, 8))

        side = "right" if rtl else "left"
        r_fa = tk.Radiobutton(
            lang_bar,
            text="فارسی",
            value="fa",
            variable=self._lang_var,
            command=self._on_lang_changed,
            bg=palette.card_bg,
            fg=palette.fg,
            selectcolor=palette.card_bg,
            activebackground=palette.card_bg,
            activeforeground=palette.fg,
            font=get_ui_font(size=9, bold=True, rtl=True),
        )
        r_fa.pack(side=side, padx=6)

        r_en = tk.Radiobutton(
            lang_bar,
            text="English",
            value="en",
            variable=self._lang_var,
            command=self._on_lang_changed,
            bg=palette.card_bg,
            fg=palette.fg,
            selectcolor=palette.card_bg,
            activebackground=palette.card_bg,
            activeforeground=palette.fg,
            font=get_ui_font(size=9, bold=True, rtl=False),
        )
        r_en.pack(side=side, padx=6)

        # Tour Card Frame
        tour_label = "کلیدهای میانبر اصلی و ضروری:" if rtl else "Essential Hotkeys Tour:"
        tk.Label(
            self._container,
            text=tour_label,
            font=get_ui_font(size=10, bold=True, rtl=rtl),
            bg=palette.bg,
            fg=palette.fg,
        ).pack(anchor=align, pady=(4, 6))

        card = tk.Frame(
            self._container,
            bg=palette.card_bg,
            highlightbackground=palette.border,
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        card.pack(fill="both", expand=True, pady=(0, 14))

        hotkeys = _HOTKEYS_FA if rtl else _HOTKEYS_EN
        for key, desc in hotkeys:
            row = tk.Frame(card, bg=palette.card_bg)
            row.pack(fill="x", pady=3)

            # Badge for hotkey
            badge = tk.Label(
                row,
                text=f" {key} ",
                font=f_hk_key,
                bg=palette.highlight if palette.name == "dark" else "#e8f0fe",
                fg=palette.highlight_fg if palette.name == "dark" else "#1a73e8",
                padx=6,
                pady=2,
                relief="flat",
            )
            badge.pack(side="left" if not rtl else "right", padx=(0, 8) if not rtl else (8, 0))

            tk.Label(
                row,
                text=desc,
                font=f_hk_desc,
                bg=palette.card_bg,
                fg=palette.fg,
                anchor="e" if rtl else "w",
            ).pack(side="right" if rtl else "left", fill="x", expand=True)

        # Buttons Frame
        btn_bar = tk.Frame(self._container, bg=palette.bg)
        btn_bar.pack(fill="x", pady=(4, 0))

        start_text = "شروع به کار" if rtl else "Get Started"
        skip_text = "رد کردن" if rtl else "Skip"

        btn_start = tk.Button(
            btn_bar,
            text=start_text,
            font=f_btn,
            bg=palette.accent,
            fg="#ffffff" if palette.name != "high_contrast" else "#000000",
            activebackground=palette.highlight,
            activeforeground="#ffffff",
            relief="flat",
            padx=18,
            pady=6,
            cursor="hand2",
            command=lambda: self._close(completed=True),
        )

        btn_skip = tk.Button(
            btn_bar,
            text=skip_text,
            font=f_sub,
            bg=palette.card_bg,
            fg=palette.subtext,
            activebackground=palette.bg,
            activeforeground=palette.fg,
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=lambda: self._close(completed=False),
        )

        if rtl:
            btn_start.pack(side="right", padx=(8, 0))
            btn_skip.pack(side="right")
        else:
            btn_start.pack(side="left", padx=(0, 8))
            btn_skip.pack(side="left")

        btn_start.focus_set()

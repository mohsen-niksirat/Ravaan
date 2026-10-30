"""Enhanced First-Run Onboarding Wizard (Phase 6).

3-step interactive onboarding experience for Persian & English typists:
1. Language & Preset Selection: Simple, Standard (Recommended), and Power User modes.
2. Essential Hotkeys & Conversion Shortcut Selector.
3. 30-Second Interactive Demo & Typing Sandbox (live ZWNJ, auto-fix, and suggestions).
"""

from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Any

from ravan.core.config import Config, save_config
from ravan.core.i18n import get_locale, is_rtl, set_locale, t
from ravan.ui.theme import (
    apply_theme_to_ttk,
    apply_window_decorations,
    get_active_palette,
    get_ui_font,
)

log = logging.getLogger(__name__)

_HOTKEYS_FA = [
    ("Pause", "تغییر چیدمان متن اشتباه تایپ‌شده (fa ↔ en)"),
    ("Shift + Space", "درج نیم‌فاصله هوشمند (ZWNJ)"),
    ("Alt + L", "نمایش نشانگر زبان نزدیک نشانگر متن"),
    ("Alt + V", "تاریخچه و جست‌وجوی کلیپ‌بورد"),
    ("Ctrl + Alt + P", "مکث موقت یا ادامهٔ فعالیت روان"),
]

_HOTKEYS_EN = [
    ("Pause", "Reverse layout of mis-typed text (fa ↔ en)"),
    ("Shift + Space", "Insert zero-width non-joiner (smart ZWNJ)"),
    ("Alt + L", "Show language indicator near caret"),
    ("Alt + V", "Clipboard history and search"),
    ("Ctrl + Alt + P", "Pause or resume Ravaan"),
]

_CONVERT_HOTKEY_OPTIONS = ["Pause", "Alt+L", "Ctrl+Shift+L", "F12", "Alt+Shift"]


def apply_preset(cfg: Config, preset: str) -> None:
    """Apply sensible feature defaults based on chosen user preset."""
    if preset == "simple":
        cfg.word_prediction_enabled = False
        cfg.next_word_prediction = False
        cfg.autofix_wrong_layout = False
        cfg.auto_zwnj = True
        cfg.fix_punctuation = True
        cfg.shift_space_zwnj = True
        cfg.clipboard_history_enabled = False
        cfg.inline_calc_enabled = False
    elif preset == "power":
        cfg.word_prediction_enabled = True
        cfg.next_word_prediction = True
        cfg.autofix_wrong_layout = True
        cfg.auto_zwnj = True
        cfg.fix_punctuation = True
        cfg.shift_space_zwnj = True
        cfg.clipboard_history_enabled = True
        cfg.inline_calc_enabled = True
    else:  # "standard" (recommended)
        cfg.word_prediction_enabled = True
        cfg.next_word_prediction = False
        cfg.autofix_wrong_layout = True
        cfg.auto_zwnj = True
        cfg.fix_punctuation = True
        cfg.shift_space_zwnj = True
        cfg.clipboard_history_enabled = False
        cfg.inline_calc_enabled = False


class FirstRunWizard:
    """Friendly 3-step onboarding wizard for first-time launch."""

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
        self._step = 1  # 1: Language & Preset, 2: Hotkeys, 3: Interactive Demo
        self._total_steps = 3

        self._lang_var: tk.StringVar | None = None
        self._preset_var: tk.StringVar | None = None
        self._convert_hk_var: tk.StringVar | None = None

        self._container: tk.Frame | None = None
        self._demo_entry: tk.Entry | None = None
        self._demo_badge: tk.Label | None = None
        self._demo_cand_frame: tk.Frame | None = None

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
            new_l = self._lang_var.get()
            if hasattr(self.cfg, "ui_language"):
                self.cfg.ui_language = new_l
            else:
                self.cfg.language = new_l
            set_locale(new_l)

        if completed:
            preset = self._preset_var.get() if self._preset_var is not None else "standard"
            apply_preset(self.cfg, preset)
            # Save chosen conversion hotkey
            if self._convert_hk_var is not None and hasattr(self.cfg.convert_hotkey, "key"):
                self.cfg.convert_hotkey.key = self._convert_hk_var.get()

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
        parent = self.parent or getattr(tk, "_default_root", None)
        win = tk.Toplevel(parent) if parent is not None else tk.Toplevel()
        self._root = win

        win.title(t("wizard.title", "Welcome to Ravaan • به روان خوش آمدید"))
        win.geometry("640x560")
        win.minsize(580, 520)
        win.resizable(True, True)
        win.attributes("-topmost", True)
        win.configure(bg=palette.bg)
        apply_window_decorations(win, palette)
        apply_theme_to_ttk(win, palette)
        win.protocol("WM_DELETE_WINDOW", lambda: self._close(completed=False))

        # Center on screen
        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        px = max(20, (sw - 640) // 2)
        py = max(20, (sh - 560) // 2)
        win.geometry(f"640x560+{px}+{py}")

        cfg_lang = getattr(self.cfg, "ui_language", getattr(self.cfg, "language", None))
        current_lang = cfg_lang if cfg_lang in ("fa", "en") else get_locale()
        self._lang_var = tk.StringVar(win, value=current_lang)
        self._preset_var = tk.StringVar(win, value="standard")
        self._convert_hk_var = tk.StringVar(
            win, value=getattr(self.cfg.convert_hotkey, "key", "Pause")
        )

        self._container = tk.Frame(win, bg=palette.bg, padx=24, pady=16)
        self._container.pack(fill="both", expand=True)

        self._render_step()

        # Keyboard shortcuts
        win.bind("<Return>", self._on_return_pressed)
        win.bind("<Escape>", lambda _: self._close(completed=False))
        win.focus_set()

    def _on_return_pressed(self, _event: Any) -> None:
        if self._step < self._total_steps:
            self._next_step()
        else:
            self._close(completed=True)

    def _next_step(self) -> None:
        if self._step < self._total_steps:
            self._step += 1
            self._render_step()

    def _prev_step(self) -> None:
        if self._step > 1:
            self._step -= 1
            self._render_step()

    def _on_lang_changed(self) -> None:
        new_lang = self._lang_var.get()
        set_locale(new_lang)
        if hasattr(self.cfg, "ui_language"):
            self.cfg.ui_language = new_lang
        else:
            self.cfg.language = new_lang
        self._render_step()

    def _render_step(self) -> None:
        if self._container is None:
            return
        for widget in self._container.winfo_children():
            widget.destroy()

        palette = get_active_palette()
        rtl = is_rtl()
        align = "e" if rtl else "w"

        # ── 1. Top Bar: Step Indicator & Title ──
        top_bar = tk.Frame(self._container, bg=palette.bg)
        top_bar.pack(fill="x", pady=(0, 10))

        step_text = t(
            "wizard.step_indicator",
            "Step {current} of {total}",
            current=self._step,
            total=self._total_steps,
        )
        tk.Label(
            top_bar,
            text=f" {step_text} ",
            font=get_ui_font(size=9, bold=True, rtl=rtl),
            bg=palette.badge_bg,
            fg=palette.accent,
            padx=10,
            pady=3,
        ).pack(side="right" if rtl else "left")

        # Language switcher in top corner
        lang_frm = tk.Frame(top_bar, bg=palette.bg)
        lang_frm.pack(side="left" if rtl else "right")
        current_l = self._lang_var.get() if self._lang_var is not None else get_locale()
        for val, label in (("fa", "فارسی"), ("en", "English")):
            r = tk.Radiobutton(
                lang_frm,
                text=label,
                value=val,
                variable=self._lang_var,
                command=self._on_lang_changed,
                bg=palette.bg,
                fg=palette.fg,
                selectcolor=palette.bg,
                activebackground=palette.bg,
                activeforeground=palette.fg,
                font=get_ui_font(size=9, bold=(current_l == val), rtl=(val == "fa")),
            )
            r.pack(side="left", padx=4)

        # ── 2. Content Area for Current Step ──
        content_box = tk.Frame(self._container, bg=palette.bg)
        content_box.pack(fill="both", expand=True, pady=(0, 10))

        if self._step == 1:
            self._render_step1_presets(content_box, palette, rtl, align)
        elif self._step == 2:
            self._render_step2_hotkeys(content_box, palette, rtl, align)
        elif self._step == 3:
            self._render_step3_demo(content_box, palette, rtl, align)

        # ── 3. Bottom Navigation Bar ──
        self._render_nav_bar(palette, rtl)

    def _render_step1_presets(
        self, parent: tk.Frame, palette: Any, rtl: bool, align: str
    ) -> None:
        f_title = get_ui_font(size=13, bold=True, rtl=rtl)
        f_sub = get_ui_font(size=9, bold=False, rtl=rtl)
        f_card_t = get_ui_font(size=10, bold=True, rtl=rtl)
        f_card_d = get_ui_font(size=8, bold=False, rtl=rtl)

        tk.Label(
            parent,
            text=t("wizard.step1_title", "✨ Welcome to Ravaan!"),
            font=f_title,
            bg=palette.bg,
            fg=palette.accent,
        ).pack(anchor=align, pady=(0, 2))

        tk.Label(
            parent,
            text=t("wizard.step1_sub", "Choose your language and preferred mode"),
            font=f_sub,
            bg=palette.bg,
            fg=palette.subtext,
        ).pack(anchor=align, pady=(0, 12))

        # Preset selection cards
        tk.Label(
            parent,
            text=t("wizard.preset_title", "Choose your preset:"),
            font=f_card_t,
            bg=palette.bg,
            fg=palette.fg,
        ).pack(anchor=align, pady=(0, 6))

        presets = [
            (
                "standard",
                t("wizard.preset_standard_title", "Standard Mode (Recommended)"),
                t(
                    "wizard.preset_standard_desc",
                    "Smart word prediction, auto-ZWNJ, and safe layout auto-fix.",
                ),
            ),
            (
                "simple",
                t("wizard.preset_simple_title", "Simple Mode"),
                t(
                    "wizard.preset_simple_desc",
                    "Ultra-lightweight: smart ZWNJ and punctuation spacing only. No prediction popups.",
                ),
            ),
            (
                "power",
                t("wizard.preset_power_title", "Power User Mode"),
                t(
                    "wizard.preset_power_desc",
                    "Full power: next-word prediction, clipboard history (Alt+V), calc (=), and macros.",
                ),
            ),
        ]

        curr_preset = self._preset_var.get() if self._preset_var is not None else "standard"
        for val, title, desc in presets:
            card = tk.Frame(
                parent,
                bg=palette.card_bg,
                highlightbackground=palette.highlight if curr_preset == val else palette.border,
                highlightthickness=2 if curr_preset == val else 1,
                padx=12,
                pady=8,
            )
            card.pack(fill="x", pady=4)

            top_row = tk.Frame(card, bg=palette.card_bg)
            top_row.pack(fill="x")

            r = tk.Radiobutton(
                top_row,
                text=title,
                value=val,
                variable=self._preset_var,
                command=self._render_step,
                bg=palette.card_bg,
                fg=palette.fg,
                selectcolor=palette.card_bg,
                activebackground=palette.card_bg,
                activeforeground=palette.fg,
                font=f_card_t,
            )
            r.pack(side="right" if rtl else "left")

            if val == "standard":
                tk.Label(
                    top_row,
                    text="★ پیشنهادی" if rtl else "★ Recommended",
                    font=get_ui_font(size=8, bold=True, rtl=rtl),
                    bg=palette.badge_bg,
                    fg=palette.badge_fg,
                    padx=6,
                    pady=1,
                ).pack(side="left" if rtl else "right", padx=6)

            tk.Label(
                card,
                text=desc,
                font=f_card_d,
                bg=palette.card_bg,
                fg=palette.subtext,
                justify="right" if rtl else "left",
                wraplength=540,
            ).pack(anchor=align, padx=(20, 0) if not rtl else (0, 20), pady=(2, 0))

    def _render_step2_hotkeys(
        self, parent: tk.Frame, palette: Any, rtl: bool, align: str
    ) -> None:
        f_title = get_ui_font(size=13, bold=True, rtl=rtl)
        f_sub = get_ui_font(size=9, bold=False, rtl=rtl)
        f_hk_key = get_ui_font(size=9, bold=True, rtl=False)
        f_hk_desc = get_ui_font(size=9, bold=False, rtl=rtl)

        tk.Label(
            parent,
            text=t("wizard.step2_title", "⌨️ Essential Hotkeys"),
            font=f_title,
            bg=palette.bg,
            fg=palette.accent,
        ).pack(anchor=align, pady=(0, 2))

        tk.Label(
            parent,
            text=t("wizard.step2_sub", "Review and customize your primary shortcut"),
            font=f_sub,
            bg=palette.bg,
            fg=palette.subtext,
        ).pack(anchor=align, pady=(0, 8))

        # Primary shortcut customization row
        hk_select_frame = tk.Frame(
            parent,
            bg=palette.card_bg,
            highlightbackground=palette.border,
            highlightthickness=1,
            padx=12,
            pady=8,
        )
        hk_select_frame.pack(fill="x", pady=(0, 10))

        tk.Label(
            hk_select_frame,
            text=t("wizard.convert_hotkey_label", "Primary Layout Reverse Hotkey:"),
            font=get_ui_font(size=9, bold=True, rtl=rtl),
            bg=palette.card_bg,
            fg=palette.fg,
        ).pack(side="right" if rtl else "left", padx=6)

        combo = ttk.Combobox(
            hk_select_frame,
            textvariable=self._convert_hk_var,
            values=_CONVERT_HOTKEY_OPTIONS,
            state="readonly",
            width=14,
        )
        combo.pack(side="right" if rtl else "left", padx=6)

        # Hotkey cards list
        card = tk.Frame(
            parent,
            bg=palette.card_bg,
            highlightbackground=palette.border,
            highlightthickness=1,
            padx=12,
            pady=8,
        )
        card.pack(fill="both", expand=True)

        hotkeys = _HOTKEYS_FA if rtl else _HOTKEYS_EN
        for key, desc in hotkeys:
            row = tk.Frame(card, bg=palette.card_bg)
            row.pack(fill="x", pady=2)

            badge = tk.Label(
                row,
                text=f" {key} ",
                font=f_hk_key,
                bg=palette.highlight if palette.name == "dark" else "#e8f0fe",
                fg=palette.highlight_fg if palette.name == "dark" else "#1a73e8",
                padx=6,
                pady=1,
            )
            badge.pack(side="left" if not rtl else "right", padx=(0, 6) if not rtl else (6, 0))

            tk.Label(
                row,
                text=desc,
                font=f_hk_desc,
                bg=palette.card_bg,
                fg=palette.fg,
                anchor="e" if rtl else "w",
            ).pack(side="right" if rtl else "left", fill="x", expand=True)

    def _render_step3_demo(
        self, parent: tk.Frame, palette: Any, rtl: bool, align: str
    ) -> None:
        f_title = get_ui_font(size=13, bold=True, rtl=rtl)
        f_sub = get_ui_font(size=9, bold=False, rtl=rtl)

        tk.Label(
            parent,
            text=t("wizard.step3_title", "🎯 30-Second Interactive Demo"),
            font=f_title,
            bg=palette.bg,
            fg=palette.accent,
        ).pack(anchor=align, pady=(0, 2))

        tk.Label(
            parent,
            text=t(
                "wizard.step3_sub",
                "Try typing in the sandbox below to experience Ravaan live!",
            ),
            font=f_sub,
            bg=palette.bg,
            fg=palette.subtext,
        ).pack(anchor=align, pady=(0, 10))

        demo_card = tk.Frame(
            parent,
            bg=palette.card_bg,
            highlightbackground=palette.border,
            highlightthickness=1,
            padx=16,
            pady=14,
        )
        demo_card.pack(fill="both", expand=True)

        # Sandbox prompt instructions
        hint_text = (
            "💡 تست کنید: کلمه «sghl » را تایپ کنید تا تبدیل به «سلام» شود، یا تایپ کنید «می » برای درج خودکار نیم‌فاصله!"
            if rtl
            else "💡 Try it: Type 'sghl ' to watch it auto-convert to 'سلام', or type 'می ' to test smart auto-ZWNJ!"
        )
        tk.Label(
            demo_card,
            text=hint_text,
            font=get_ui_font(size=9, bold=False, rtl=rtl),
            bg=palette.card_bg,
            fg=palette.subtext,
            wraplength=540,
            justify="right" if rtl else "left",
        ).pack(anchor=align, pady=(0, 10))

        # Live typing input box
        self._demo_entry = tk.Entry(
            demo_card,
            font=("Segoe UI" if not rtl else "Vazirmatn", 12),
            bg=palette.bg,
            fg=palette.fg,
            insertbackground=palette.fg,
            relief="solid",
            bd=1,
        )
        self._demo_entry.pack(fill="x", ipady=6, pady=(0, 8))
        self._demo_entry.bind("<KeyRelease>", self._on_demo_typing)
        self._demo_entry.focus_set()

        # Status Badge Pill
        self._demo_badge = tk.Label(
            demo_card,
            text="",
            font=get_ui_font(size=9, bold=True, rtl=rtl),
            bg=palette.card_bg,
            fg="#0f9d58",
        )
        self._demo_badge.pack(anchor=align, pady=(0, 6))

        # Live Candidates frame
        cand_lbl = tk.Label(
            demo_card,
            text=t("wizard.demo_pred_label", "Live Suggestions:"),
            font=get_ui_font(size=8, bold=True, rtl=rtl),
            bg=palette.card_bg,
            fg=palette.subtext,
        )
        cand_lbl.pack(anchor=align, pady=(0, 2))

        self._demo_cand_frame = tk.Frame(demo_card, bg=palette.card_bg)
        self._demo_cand_frame.pack(anchor=align)

    def _on_demo_typing(self, _event: Any) -> None:
        """Interactive typing demo simulation for layout auto-fix, ZWNJ, and suggestions."""
        if self._demo_entry is None or self._demo_badge is None:
            return

        txt = self._demo_entry.get()

        # Case 1: Wrong layout simulation ("sghl " -> "سلام ")
        if "sghl " in txt.lower():
            new_txt = txt.replace("sghl ", "سلام ").replace("SGHL ", "سلام ")
            self._demo_entry.delete(0, tk.END)
            self._demo_entry.insert(0, new_txt)
            self._demo_badge.configure(
                text=t("wizard.demo_autofix_badge", "✓ Layout Converted ('sghl' → 'سلام')"),
                fg="#0f9d58",
            )

        # Case 2: Smart ZWNJ simulation ("می " -> "می‌")
        elif txt.endswith("می "):
            new_txt = txt[:-1] + "\u200c"
            self._demo_entry.delete(0, tk.END)
            self._demo_entry.insert(0, new_txt)
            self._demo_badge.configure(
                text=t("wizard.demo_zwnj_badge", "✓ Smart ZWNJ Inserted ('می‌')"),
                fg="#0f9d58",
            )

        # Case 3: Live prediction simulation
        if self._demo_cand_frame is not None:
            for w in self._demo_cand_frame.winfo_children():
                w.destroy()

            palette = get_active_palette()
            tokens = txt.split()
            last_tok = tokens[-1] if tokens else ""

            suggestions: list[str] = []
            if last_tok.startswith("سل"):
                suggestions = ["1: سلام", "2: سلسله", "3: سلول"]
            elif last_tok.lower().startswith("th"):
                suggestions = ["1: the", "2: that", "3: this"]
            elif last_tok.startswith("بر"):
                suggestions = ["1: برنامه", "2: برای", "3: بررسی"]

            for cand in suggestions:
                lbl = tk.Label(
                    self._demo_cand_frame,
                    text=f" {cand} ",
                    font=get_ui_font(size=8, bold=True, rtl=is_rtl()),
                    bg=palette.highlight if palette.name == "dark" else "#e8f0fe",
                    fg=palette.highlight_fg if palette.name == "dark" else "#1a73e8",
                    padx=6,
                    pady=2,
                )
                lbl.pack(side="left", padx=4)

    def _render_nav_bar(self, palette: Any, rtl: bool) -> None:
        nav = tk.Frame(self._container, bg=palette.bg)
        nav.pack(fill="x", pady=(10, 0))

        btn_font = get_ui_font(size=10, bold=True, rtl=rtl)

        # Skip button
        btn_skip = tk.Button(
            nav,
            text=t("wizard.btn_skip", "Skip"),
            font=get_ui_font(size=9, bold=False, rtl=rtl),
            bg=palette.card_bg,
            fg=palette.subtext,
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=lambda: self._close(completed=False),
        )
        btn_skip.pack(side="left" if not rtl else "right")

        # Next / Finish Button
        is_last = self._step == self._total_steps
        action_text = (
            t("wizard.btn_finish", "Start using Ravaan")
            if is_last
            else t("wizard.btn_next", "Next →")
        )
        btn_action = tk.Button(
            nav,
            text=action_text,
            font=btn_font,
            bg=palette.highlight,
            fg=palette.highlight_fg,
            activebackground=palette.accent_hover,
            activeforeground=palette.highlight_fg,
            relief="flat",
            padx=20,
            pady=7,
            cursor="hand2",
            command=lambda: self._close(completed=True) if is_last else self._next_step(),
        )
        btn_action.bind("<Enter>", lambda _: btn_action.config(bg=palette.accent_hover))
        btn_action.bind("<Leave>", lambda _: btn_action.config(bg=palette.highlight))
        btn_action.pack(side="right" if not rtl else "left", padx=(8, 0) if not rtl else (0, 8))

        # Back Button (steps 2 and 3)
        if self._step > 1:
            btn_back = tk.Button(
                nav,
                text=t("wizard.btn_back", "← Back"),
                font=get_ui_font(size=9, bold=False, rtl=rtl),
                bg=palette.card_bg,
                fg=palette.fg,
                activebackground=palette.button_hover,
                activeforeground=palette.fg,
                relief="flat",
                padx=14,
                pady=7,
                cursor="hand2",
                command=self._prev_step,
            )
            btn_back.bind("<Enter>", lambda _: btn_back.config(bg=palette.button_hover))
            btn_back.bind("<Leave>", lambda _: btn_back.config(bg=palette.card_bg))
            btn_back.pack(side="right" if not rtl else "left", padx=4)

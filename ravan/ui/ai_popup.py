"""Floating modal popup for AI Text Assistant."""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from collections.abc import Callable

from ravan.ui.theme import apply_popup_window_attributes, get_active_palette, get_ui_font

log = logging.getLogger(__name__)


class AIAssistantPopup:
    """Floating UI dialog providing one-click AI text transformations."""

    def __init__(
        self,
        parent: tk.Misc | None,
        on_replace: Callable[[str], None],
        on_copy: Callable[[str], None],
        process_callback: Callable[[str, str, str], str],
        theme_mode: str = "auto",
    ) -> None:
        self.parent = parent
        self.on_replace = on_replace
        self.on_copy = on_copy
        self.process_callback = process_callback
        self.theme_mode = theme_mode
        self._top: tk.Toplevel | None = None
        self._input_text: str = ""
        self._result_var: tk.StringVar | None = None
        self._status_var: tk.StringVar | None = None
        self._txt_output: tk.Text | None = None
        self._ent_custom: tk.Entry | None = None

    def show(self, text: str, x: int, y: int) -> None:
        self._input_text = text
        p = get_active_palette(self.theme_mode)

        if self._top is not None and self._top.winfo_exists():
            self._top.destroy()

        top = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self._top = top
        top.title("Ravaan AI Assistant")
        top.attributes("-topmost", True)
        top.configure(bg=p.bg)
        try:
            top.attributes("-alpha", p.alpha)
        except tk.TclError:
            pass

        apply_popup_window_attributes(top, p)

        container = tk.Frame(top, bg=p.bg, padx=14, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        header_font = get_ui_font(size=10, bold=True, rtl=True)
        btn_font = get_ui_font(size=9, bold=False, rtl=True)

        # Header title
        lbl_head = tk.Label(
            container,
            text="✨ دستیار هوشمند روان (AI Text Assistant)",
            bg=p.bg,
            fg=p.fg,
            font=header_font,
            anchor="e",
        )
        lbl_head.pack(fill=tk.X, pady=(0, 8))

        # Action buttons row
        btn_frame = tk.Frame(container, bg=p.bg)
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        actions = [
            ("بازنویسی", "rewrite"),
            ("اصلاح رسم‌الخط", "fix_grammar"),
            ("ترجمه", "translate"),
            ("خلاصه‌سازی", "summarize"),
        ]

        for label, act in actions:
            btn = tk.Button(
                btn_frame,
                text=label,
                bg=p.card_bg,
                fg=p.fg,
                activebackground=p.highlight,
                activeforeground=p.highlight_fg,
                font=btn_font,
                relief=tk.FLAT,
                padx=6,
                pady=3,
                command=lambda a=act: self._trigger_action(a),
            )
            btn.pack(side=tk.RIGHT, padx=3)

        # Custom instruction row
        cust_frame = tk.Frame(container, bg=p.bg)
        cust_frame.pack(fill=tk.X, pady=(0, 8))

        self._ent_custom = tk.Entry(
            cust_frame,
            bg=p.card_bg,
            fg=p.fg,
            insertbackground=p.fg,
            font=get_ui_font(size=9),
            bd=1,
            relief=tk.SOLID,
        )
        self._ent_custom.insert(0, "دستور دلخواه (اختیاری)...")
        self._ent_custom.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self._ent_custom.bind("<Return>", lambda e: self._trigger_action("custom"))

        btn_run = tk.Button(
            cust_frame,
            text="ارسال",
            bg=p.highlight,
            fg=p.highlight_fg,
            font=btn_font,
            relief=tk.FLAT,
            padx=8,
            pady=2,
            command=lambda: self._trigger_action("custom"),
        )
        btn_run.pack(side=tk.RIGHT)

        # Status indicator
        self._status_var = tk.StringVar(value="آماده")
        lbl_status = tk.Label(
            container,
            textvariable=self._status_var,
            bg=p.bg,
            fg=p.subtext,
            font=get_ui_font(size=8, rtl=True),
            anchor="w",
        )
        lbl_status.pack(fill=tk.X, pady=(0, 4))

        # Output Text Area
        self._txt_output = tk.Text(
            container,
            bg=p.card_bg,
            fg=p.fg,
            insertbackground=p.fg,
            font=get_ui_font(size=10, rtl=True),
            height=6,
            wrap=tk.WORD,
            bd=1,
            relief=tk.SOLID,
        )
        self._txt_output.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Action Footer: Replace or Copy
        footer = tk.Frame(container, bg=p.bg)
        footer.pack(fill=tk.X)

        btn_replace = tk.Button(
            footer,
            text="✔ جایگزینی در متن (Enter)",
            bg=p.highlight,
            fg=p.highlight_fg,
            font=get_ui_font(size=9, bold=True, rtl=True),
            relief=tk.FLAT,
            padx=10,
            pady=4,
            command=self._do_replace,
        )
        btn_replace.pack(side=tk.LEFT)

        btn_copy = tk.Button(
            footer,
            text="📋 کپی پاسخ",
            bg=p.card_bg,
            fg=p.fg,
            font=btn_font,
            relief=tk.FLAT,
            padx=8,
            pady=4,
            command=self._do_copy,
        )
        btn_copy.pack(side=tk.LEFT, padx=6)

        btn_esc = tk.Button(
            footer,
            text="بستن (Esc)",
            bg=p.card_bg,
            fg=p.subtext,
            font=btn_font,
            relief=tk.FLAT,
            padx=8,
            pady=4,
            command=self.hide,
        )
        btn_esc.pack(side=tk.RIGHT)

        top.bind("<Escape>", lambda e: self.hide())

        # Position window near caret/mouse
        top.update_idletasks()
        w = max(top.winfo_reqwidth(), 380)
        h = max(top.winfo_reqheight(), 260)
        from ravan.platform import winapi as wapi

        m_left, m_top, m_right, m_bottom = wapi.get_monitor_work_area(x, y)
        px = max(m_left + 8, min(x, m_right - w - 8))
        py = max(m_top + 8, min(y + 24, m_bottom - h - 8))
        top.geometry(f"{w}x{h}+{px}+{py}")
        top.deiconify()

    def _trigger_action(self, action: str) -> None:
        custom_inst = ""
        if action == "custom" and self._ent_custom:
            val = self._ent_custom.get().strip()
            if val != "دستور دلخواه (اختیاری)...":
                custom_inst = val

        if self._status_var:
            self._status_var.set("در حال پردازش هوش مصنوعی...")

        def _bg_call() -> None:
            try:
                res = self.process_callback(action, self._input_text, custom_inst)
                if self._top and self._top.winfo_exists():
                    self._top.after(0, lambda: self._update_output(res, ok=True))
            except Exception as exc:  # noqa: BLE001
                err_msg = str(exc)
                if self._top and self._top.winfo_exists():
                    self._top.after(0, lambda: self._update_output(err_msg, ok=False))

        threading.Thread(target=_bg_call, daemon=True).start()

    def _update_output(self, text: str, ok: bool) -> None:
        if self._txt_output:
            self._txt_output.delete("1.0", tk.END)
            self._txt_output.insert(tk.END, text)
        if self._status_var:
            self._status_var.set("تکمیل شد." if ok else f"خطا: {text}")

    def _do_replace(self) -> None:
        if self._txt_output:
            text = self._txt_output.get("1.0", tk.END).strip()
            if text:
                self.hide()
                self.on_replace(text)

    def _do_copy(self) -> None:
        if self._txt_output:
            text = self._txt_output.get("1.0", tk.END).strip()
            if text:
                self.hide()
                self.on_copy(text)

    def hide(self) -> None:
        if self._top is not None and self._top.winfo_exists():
            self._top.destroy()
            self._top = None

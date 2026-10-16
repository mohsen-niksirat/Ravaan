"""Settings window (Tkinter) — hotkeys, toggles, snippets, exclusions."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from ravan.core.config import (
    Config,
    Snippet,
    hotkey_to_text,
    save_config,
    text_to_hotkey,
)
from ravan.platform.startup import is_startup_enabled, set_startup


class SettingsWindow:
    """Settings window driven by the app's main loop (no own mainloop).

    Tk is not thread-safe, so the window is created and pumped from the
    same thread that owns the overlay's Tk root. `show()` only requests
    opening; `tick()` builds and pumps the window.
    """

    def __init__(
        self,
        cfg: Config,
        on_saved: Callable[[Config], None] | None = None,
    ) -> None:
        self.cfg = cfg
        self.on_saved = on_saved
        self._open = False
        self._built = False
        self._root: tk.Tk | None = None
        self._snippet_editor = None
        self._managed_snippets = list(self.cfg.snippets)
        self._last_snip_text = ""

    @property
    def open(self) -> bool:
        return self._open

    def show(self) -> None:
        """Request opening (thread-safe; actual build happens in tick())."""
        self._open = True

    def tick(self) -> None:
        if not self._open:
            return
        if not self._built:
            self._build()
            self._built = True
        if self._snippet_editor is not None and self._snippet_editor.open:
            self._snippet_editor.tick()
        if self._root is None:
            return
        try:
            self._root.update_idletasks()
            self._root.update()
        except (tk.TclError, RuntimeError):
            pass

    # ── UI construction ──────────────────────────────────────────────

    def _build(self) -> None:
        self._root = tk.Toplevel()
        self._root.title("Ravan — Settings")
        self._root.attributes("-topmost", True)
        self._root.resizable(False, False)
        self._root.protocol("WM_DELETE_WINDOW", self._close)

        pad = {"padx": 10, "pady": 4}
        frm = ttk.Frame(self._root, padding=12)
        frm.pack(fill="both", expand=True)

        row = 0

        # ── Hotkeys ──
        ttk.Label(frm, text="Hotkeys", font=("Segoe UI", 11, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )
        row += 1

        ttk.Label(frm, text="Convert last word:").grid(row=row, column=0, sticky="w", **pad)
        self._convert_var = tk.StringVar(value=hotkey_to_text(self.cfg.convert_hotkey))
        ttk.Entry(frm, textvariable=self._convert_var, width=22).grid(
            row=row, column=1, sticky="w", **pad
        )
        ttk.Label(frm, text="e.g. F12  or  Ctrl+Shift+C", foreground="gray").grid(
            row=row, column=2, sticky="w", **pad
        )
        row += 1

        ttk.Label(frm, text="Show language chip:").grid(row=row, column=0, sticky="w", **pad)
        self._lang_var = tk.StringVar(
            value=hotkey_to_text(self.cfg.lang_indicator_hotkey)
        )
        ttk.Entry(frm, textvariable=self._lang_var, width=22).grid(
            row=row, column=1, sticky="w", **pad
        )
        ttk.Label(frm, text="e.g. Alt+L", foreground="gray").grid(
            row=row, column=2, sticky="w", **pad
        )
        row += 1

        ttk.Label(frm, text="Clipboard history:").grid(row=row, column=0, sticky="w", **pad)
        self._clip_var = tk.StringVar(
            value=hotkey_to_text(self.cfg.clipboard_history_hotkey)
        )
        ttk.Entry(frm, textvariable=self._clip_var, width=22).grid(
            row=row, column=1, sticky="w", **pad
        )
        ttk.Label(frm, text="e.g. Alt+V", foreground="gray").grid(
            row=row, column=2, sticky="w", **pad
        )
        row += 1

        ttk.Label(frm, text="Normalize text:").grid(row=row, column=0, sticky="w", **pad)
        self._norm_var = tk.StringVar(
            value=hotkey_to_text(self.cfg.normalize_hotkey)
        )
        ttk.Entry(frm, textvariable=self._norm_var, width=22).grid(
            row=row, column=1, sticky="w", **pad
        )
        ttk.Label(frm, text="e.g. Ctrl+F12", foreground="gray").grid(
            row=row, column=2, sticky="w", **pad
        )
        row += 1

        ttk.Label(frm, text="Cycle text case:").grid(row=row, column=0, sticky="w", **pad)
        self._case_var = tk.StringVar(
            value=hotkey_to_text(self.cfg.case_hotkey)
        )
        ttk.Entry(frm, textvariable=self._case_var, width=22).grid(
            row=row, column=1, sticky="w", **pad
        )
        ttk.Label(frm, text="e.g. Shift+F12", foreground="gray").grid(
            row=row, column=2, sticky="w", **pad
        )
        row += 1

        ttk.Label(frm, text="Undo autocorrect:").grid(row=row, column=0, sticky="w", **pad)
        self._undo_var = tk.StringVar(
            value=hotkey_to_text(self.cfg.undo_autocorrect_hotkey)
        )
        ttk.Entry(frm, textvariable=self._undo_var, width=22).grid(
            row=row, column=1, sticky="w", **pad
        )
        ttk.Label(frm, text="e.g. Ctrl+Shift+Z (or Backspace)", foreground="gray").grid(
            row=row, column=2, sticky="w", **pad
        )
        row += 2

        # ── Features ──
        ttk.Label(frm, text="Features", font=("Segoe UI", 11, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )
        row += 1

        self._prediction_var = tk.BooleanVar(value=self.cfg.prediction_enabled)
        ttk.Checkbutton(
            frm, text="Word prediction popup", variable=self._prediction_var
        ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
        row += 1

        self._autocorrect_var = tk.BooleanVar(value=self.cfg.autocorrect_enabled)
        ttk.Checkbutton(
            frm, text="Passive autocorrect on word boundary", variable=self._autocorrect_var
        ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
        row += 1

        self._zwnj_var = tk.BooleanVar(value=self.cfg.auto_zwnj_enabled)
        ttk.Checkbutton(
            frm, text="Smart Persian half-space (ZWNJ: می/نمی & ها/تر/ترین)", variable=self._zwnj_var
        ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
        row += 1

        self._shift_space_var = tk.BooleanVar(value=self.cfg.shift_space_zwnj)
        ttk.Checkbutton(
            frm, text="Shift+Space injects half-space (ZWNJ)", variable=self._shift_space_var
        ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
        row += 1

        self._cliphist_var = tk.BooleanVar(value=self.cfg.clipboard_history_enabled)
        ttk.Checkbutton(
            frm, text="Clipboard history ring buffer (Alt+V)", variable=self._cliphist_var
        ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
        row += 1

        self._calc_var = tk.BooleanVar(value=self.cfg.inline_calc_enabled)
        ttk.Checkbutton(
            frm, text="Inline math calculator on '=' (e.g. 1200*1.09=)", variable=self._calc_var
        ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
        row += 1

        self._digits_var = tk.BooleanVar(value=self.cfg.quickpick_digits)
        ttk.Checkbutton(
            frm, text="Digits 1–5 quick-pick in popup", variable=self._digits_var
        ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
        row += 1

        self._en_dict_var = tk.BooleanVar(value=self.cfg.english_dict_enabled)
        ttk.Checkbutton(frm, text="English dictionary", variable=self._en_dict_var).grid(
            row=row, column=0, columnspan=3, sticky="w", **pad
        )
        row += 1

        self._fa_dict_var = tk.BooleanVar(value=self.cfg.persian_dict_enabled)
        ttk.Checkbutton(frm, text="Persian dictionary", variable=self._fa_dict_var).grid(
            row=row, column=0, columnspan=3, sticky="w", **pad
        )
        row += 1

        self._sound_var = tk.BooleanVar(value=self.cfg.sound_feedback_enabled)
        ttk.Checkbutton(
            frm, text="Audio feedback on keyboard layout switch", variable=self._sound_var
        ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
        row += 1

        self._punct_spacing_var = tk.BooleanVar(value=self.cfg.fix_punctuation_spacing)
        ttk.Checkbutton(
            frm, text="Fix Persian spacing before punctuation (e.g. کتاب . -> کتاب.)", variable=self._punct_spacing_var
        ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
        row += 2

        # ── Tuning ──
        ttk.Label(frm, text="Tuning", font=("Segoe UI", 11, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )
        row += 1

        ttk.Label(frm, text="Debounce (ms):").grid(row=row, column=0, sticky="w", **pad)
        self._debounce_var = tk.IntVar(value=self.cfg.prediction_debounce_ms)
        ttk.Spinbox(
            frm, from_=0, to=500, increment=10, textvariable=self._debounce_var, width=8
        ).grid(row=row, column=1, sticky="w", **pad)
        row += 1

        ttk.Label(frm, text="Max candidates:").grid(row=row, column=0, sticky="w", **pad)
        self._maxcand_var = tk.IntVar(value=self.cfg.prediction_max_candidates)
        ttk.Spinbox(
            frm, from_=1, to=9, textvariable=self._maxcand_var, width=8
        ).grid(row=row, column=1, sticky="w", **pad)
        row += 1

        ttk.Label(frm, text="Min prefix length:").grid(row=row, column=0, sticky="w", **pad)
        self._minlen_var = tk.IntVar(value=self.cfg.min_prefix_len)
        ttk.Spinbox(frm, from_=1, to=6, textvariable=self._minlen_var, width=8).grid(
            row=row, column=1, sticky="w", **pad
        )
        row += 2

        # ── Startup ──
        self._startup_var = tk.BooleanVar(value=is_startup_enabled())
        ttk.Checkbutton(
            frm, text="Launch at Windows startup", variable=self._startup_var
        ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
        row += 2

        # ── Excluded apps ──
        ttk.Label(frm, text="Excluded apps (one per line)", font=("Segoe UI", 11, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )
        row += 1
        self._excl_text = tk.Text(frm, width=40, height=4)
        self._excl_text.insert("1.0", "\n".join(self.cfg.excluded_apps))
        self._excl_text.grid(row=row, column=0, columnspan=3, sticky="w", **pad)
        row += 1

        # Interactive detection & test tool
        excl_tools = ttk.Frame(frm)
        excl_tools.grid(row=row, column=0, columnspan=3, sticky="w", **pad)
        row += 2

        self._detected_app_var = tk.StringVar(value="Active app: —")
        ttk.Label(excl_tools, textvariable=self._detected_app_var, foreground="#444444").pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            excl_tools, text="Detect Active App", command=self._detect_active_app
        ).pack(side="left", padx=3)
        self._add_detected_btn = ttk.Button(
            excl_tools, text="+ Add to Exclusions", command=self._add_detected_to_exclusions, state="disabled"
        )
        self._add_detected_btn.pack(side="left", padx=3)


        # ── Snippets ──
        snip_hdr = ttk.Frame(frm)
        snip_hdr.grid(row=row, column=0, columnspan=3, sticky="w", pady=(0, 6))
        ttk.Label(
            snip_hdr, text="Snippets", font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=(0, 10))
        ttk.Button(
            snip_hdr, text="Open Snippet Editor…", command=self._open_snippet_editor
        ).pack(side="left")
        row += 1
        self._snip_text = tk.Text(frm, width=40, height=4)
        self._update_snip_display()
        self._snip_text.grid(row=row, column=0, columnspan=3, sticky="w", **pad)
        row += 2

        # ── User Custom Words ──
        from ravan.core.user_dict import load_user_words

        ttk.Label(
            frm, text="Custom words / names (one per line)",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(0, 6))
        row += 1
        self._user_words_text = tk.Text(frm, width=40, height=4)
        self._user_words_text.insert("1.0", "\n".join(load_user_words()))
        self._user_words_text.grid(row=row, column=0, columnspan=3, sticky="w", **pad)
        row += 2

        # ── Buttons ──
        btns = ttk.Frame(frm)
        btns.grid(row=row, column=0, columnspan=3, sticky="e", pady=(8, 0))
        ttk.Button(btns, text="Cancel", command=self._close).pack(side="left", padx=4)
        ttk.Button(btns, text="Save", command=self._save).pack(side="left", padx=4)

        self._root.update_idletasks()
        self._center()

    def _center(self) -> None:
        w = self._root.winfo_width()
        h = self._root.winfo_height()
        x = (self._root.winfo_screenwidth() - w) // 2
        y = (self._root.winfo_screenheight() - h) // 3
        self._root.geometry(f"+{x}+{y}")

    # ── Actions ──────────────────────────────────────────────────────

    def _get_current_exclusions_from_text(self) -> list[str]:
        raw = self._excl_text.get("1.0", "end").strip()
        return [line.strip().lower() for line in raw.splitlines() if line.strip()]

    def _detect_active_app(self) -> None:
        from ravan.core.config import is_app_excluded
        from ravan.platform.focus import active_window_info

        info = active_window_info()
        exe = info.get("exe")
        if not exe:
            self._detected_app_var.set("Active app: could not detect")
            self._add_detected_btn.config(state="disabled")
            return

        current_excls = self._get_current_exclusions_from_text()
        status = "EXCLUDED" if is_app_excluded(exe, current_excls) else "ACTIVE"
        self._last_detected_exe = exe
        self._detected_app_var.set(f"{exe}  [{status}]")
        self._add_detected_btn.config(state="normal")

    def _add_detected_to_exclusions(self) -> None:
        exe = getattr(self, "_last_detected_exe", None)
        if not exe:
            return
        current = self._get_current_exclusions_from_text()
        if exe.lower() not in current:
            text = self._excl_text.get("1.0", "end").rstrip()
            if text:
                text += "\n" + exe.lower() + "\n"
            else:
                text = exe.lower() + "\n"
            self._excl_text.delete("1.0", "end")
            self._excl_text.insert("1.0", text)
            self._detect_active_app()

    def _update_snip_display(self) -> None:
        if self._snip_text is None:
            return
        lines = []
        for s in self._managed_snippets:
            preview = s.replacement.replace("\n", "\\n")
            lines.append(f"{s.trigger} => {preview}")
        text = "\n".join(lines)
        self._snip_text.delete("1.0", "end")
        self._snip_text.insert("1.0", text)
        self._last_snip_text = text

    def _open_snippet_editor(self) -> None:
        from ravan.ui.snippet_editor import SnippetEditorWindow

        def on_editor_saved(snippets: list[Snippet]) -> None:
            self._managed_snippets = snippets
            self._update_snip_display()

        self._snippet_editor = SnippetEditorWindow(
            self._managed_snippets, on_saved=on_editor_saved
        )
        self._snippet_editor.show()

    def _close(self) -> None:
        self._open = False
        self._built = False
        if self._root is not None:
            try:
                self._root.destroy()
            except tk.TclError:
                pass
            self._root = None

    def _save(self) -> None:
        convert = text_to_hotkey(self._convert_var.get())
        lang = text_to_hotkey(self._lang_var.get())
        clip = text_to_hotkey(self._clip_var.get())
        norm = text_to_hotkey(self._norm_var.get())
        case = text_to_hotkey(self._case_var.get())
        undo = text_to_hotkey(self._undo_var.get())
        if self._convert_var.get().strip() and convert is None:
            messagebox.showwarning("Ravan", "Invalid convert hotkey", parent=self._root)
            return
        if self._lang_var.get().strip() and lang is None:
            messagebox.showwarning("Ravan", "Invalid language hotkey", parent=self._root)
            return
        if self._clip_var.get().strip() and clip is None:
            messagebox.showwarning("Ravan", "Invalid clipboard history hotkey", parent=self._root)
            return
        if self._norm_var.get().strip() and norm is None:
            messagebox.showwarning("Ravan", "Invalid normalize hotkey", parent=self._root)
            return
        if self._case_var.get().strip() and case is None:
            messagebox.showwarning("Ravan", "Invalid case hotkey", parent=self._root)
            return
        if self._undo_var.get().strip() and undo is None:
            messagebox.showwarning("Ravan", "Invalid undo autocorrect hotkey", parent=self._root)
            return

        cfg = self.cfg
        if convert:
            cfg.convert_hotkey = convert
        if lang:
            cfg.lang_indicator_hotkey = lang
        if clip:
            cfg.clipboard_history_hotkey = clip
        if norm:
            cfg.normalize_hotkey = norm
        if case:
            cfg.case_hotkey = case
        if undo:
            cfg.undo_autocorrect_hotkey = undo
        cfg.prediction_enabled = self._prediction_var.get()
        cfg.autocorrect_enabled = self._autocorrect_var.get()
        cfg.fix_punctuation_spacing = self._punct_spacing_var.get()
        cfg.auto_zwnj_enabled = self._zwnj_var.get()
        cfg.shift_space_zwnj = self._shift_space_var.get()
        cfg.clipboard_history_enabled = self._cliphist_var.get()
        cfg.inline_calc_enabled = self._calc_var.get()
        cfg.quickpick_digits = self._digits_var.get()
        cfg.english_dict_enabled = self._en_dict_var.get()
        cfg.persian_dict_enabled = self._fa_dict_var.get()
        def _safe_int(var: tk.IntVar, default: int, min_val: int, max_val: int) -> int:
            try:
                val = int(var.get())
                return max(min_val, min(max_val, val))
            except (tk.TclError, ValueError, TypeError):
                return default

        cfg.prediction_debounce_ms = _safe_int(self._debounce_var, 50, 0, 5000)
        cfg.prediction_max_candidates = _safe_int(self._maxcand_var, 5, 1, 9)
        cfg.min_prefix_len = _safe_int(self._minlen_var, 2, 1, 6)

        excl = [
            ln.strip().lower()
            for ln in self._excl_text.get("1.0", "end").splitlines()
            if ln.strip()
        ]
        cfg.excluded_apps = excl

        cur_snip_text = self._snip_text.get("1.0", "end").strip()
        if cur_snip_text == self._last_snip_text.strip():
            cfg.snippets = list(self._managed_snippets)
        else:
            snippets: list[Snippet] = []
            for ln in cur_snip_text.splitlines():
                if "=>" not in ln:
                    continue
                trigger, _, repl = ln.partition("=>")
                trigger = trigger.strip()
                repl = repl.strip().replace("\\n", "\n")
                if trigger and repl:
                    snippets.append(Snippet(trigger=trigger, replacement=repl))
            cfg.snippets = snippets

        if self._startup_var.get() != is_startup_enabled():
            if not set_startup(self._startup_var.get()):
                messagebox.showwarning(
                    "Ravan", "Could not update startup entry", parent=self._root
                )
        cfg.launch_at_startup = self._startup_var.get()

        from ravan.core.user_dict import save_user_words

        user_words = [
            ln.strip()
            for ln in self._user_words_text.get("1.0", "end").splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        save_user_words(user_words)

        save_config(cfg)
        if self.on_saved:
            self.on_saved(cfg)
        self._close()

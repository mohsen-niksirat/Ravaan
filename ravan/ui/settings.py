"""Settings window (Tkinter) — hotkeys, toggles, snippets, exclusions."""

from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from ravan.core.config import (
    Config,
    Snippet,
    save_config,
    text_to_hotkey,
)
from ravan.platform.startup import is_startup_enabled, set_startup

log = logging.getLogger(__name__)


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
        self._root: tk.Toplevel | None = None
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
            self._built = True
            try:
                self._build()
            except Exception as exc:  # noqa: BLE001
                self._open = False
                if self._root is not None:
                    try:
                        self._root.destroy()
                    except Exception:  # noqa: BLE001
                        pass
                    self._root = None
                log.exception("SettingsWindow build failed: %s", exc)
                return
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
        self._root.withdraw()
        self._root.title("Ravan — Settings")
        self._root.attributes("-topmost", True)
        self._root.resizable(False, False)
        self._root.protocol("WM_DELETE_WINDOW", self._close)

        pad = {"padx": 10, "pady": 4}
        frm = ttk.Frame(self._root, padding=10)
        frm.pack(fill="both", expand=True)

        nb = ttk.Notebook(frm)
        nb.pack(fill="both", expand=True, pady=(0, 10))

        tab_hotkeys = ttk.Frame(nb, padding=10)
        tab_features = ttk.Frame(nb, padding=10)
        tab_tuning = ttk.Frame(nb, padding=10)
        tab_words = ttk.Frame(nb, padding=10)

        nb.add(tab_hotkeys, text="Hotkeys")
        nb.add(tab_features, text="Features")
        nb.add(tab_tuning, text="Tuning & Exclusions")
        nb.add(tab_words, text="Words & Snippets")

        from ravan.ui.settings_builder import (
            build_exclusions_section,
            build_features_section,
            build_hotkeys_section,
            build_snippets_and_dict_section,
            build_tuning_section,
        )

        build_hotkeys_section(self, tab_hotkeys, 0, pad)
        build_features_section(self, tab_features, 0, pad)
        r = build_tuning_section(self, tab_tuning, 0, pad)
        build_exclusions_section(self, tab_tuning, r, pad)
        build_snippets_and_dict_section(self, tab_words, 0, pad)

        # ── Buttons ──
        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=(4, 0))
        ttk.Button(btns, text="Cancel", command=self._close).pack(side="right", padx=4)
        ttk.Button(btns, text="Save", command=self._save).pack(side="right", padx=4)

        self._root.update_idletasks()
        self._center()
        self._root.deiconify()
        self._root.focus_set()

    def _center(self) -> None:
        if self._root is None:
            return
        self._root.update_idletasks()
        w = self._root.winfo_reqwidth()
        h = self._root.winfo_reqheight()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        x = max(20, (sw - w) // 2)
        y = max(20, (sh - h) // 3)
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

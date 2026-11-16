"""AI & Voice Studio tab builder for SettingsWindow."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from typing import Any

from ravan.core.ai import AI_PROVIDER_PRESETS, list_ollama_models, probe_provider_connection
from ravan.core.config import HotkeySpec, hotkey_to_text
from ravan.core.i18n import is_rtl, t
from ravan.ui.settings_general import _bind_live_capture, _get_win_palette
from ravan.ui.settings_voice_panel import build_voice_card
from ravan.ui.widgets import (
    FluentCard,
    FluentEntry,
    FluentPillButton,
    FluentSectionBanner,
    FluentToggleSwitch,
)


def build_ai_voice_section(win: Any, frm: ttk.Frame, start_row: int, pad: dict[str, Any]) -> int:
    """Build the AI Assistant & Voice 2.0 Settings section."""
    rtl = is_rtl()
    pal = _get_win_palette(win)
    row = start_row
    align = "e" if rtl else "w"
    frm.columnconfigure(0, weight=1)

    sub = (
        "پیکربندی دستیار هوش مصنوعی (Ollama محلی یا OpenAI/Gemini/Groq) و دیکته صوتی آفلاین/ابری"
        if rtl
        else "Configure local Ollama or Cloud AI providers, DPAPI keys, offline Whisper models & microphone"
    )
    FluentSectionBanner(
        frm, "sparkle", t("settings.tab_ai_voice", "هوش مصنوعی و صدا" if rtl else "AI & Voice"), sub, pal, rtl
    ).grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    row += 1

    row = _build_ai_card(win, frm, row, pad, pal, rtl, align)
    row = build_voice_card(win, frm, row, pad)

    rst_bar = tk.Frame(frm, bg=pal.bg_base)
    rst_bar.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(4, 8))
    FluentPillButton(
        rst_bar, text=t("settings.reset_tab", "بازگردانی این تب به پیش‌فرض" if rtl else "Reset Tab to Defaults"),
        icon="reset", variant="secondary", palette=pal, rtl=rtl, parent_bg=pal.bg_base,
        height=30, command=lambda: win._reset_tab_defaults("ai_voice"),
    ).pack(side="right" if rtl else "left")
    return row + 1


def _build_ai_card(
    win: Any, frm: ttk.Frame, row: int, pad: dict[str, Any], pal: Any, rtl: bool, align: str
) -> int:
    ai_card = FluentCard(
        frm, t("settings.ai_card_title", "دستیار متنی هوش مصنوعی (AI 2.0)" if rtl else "AI Text Assistant (AI 2.0)"),
        padding=12, palette=pal, rtl=rtl, icon="sparkle",
    )
    ai_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 10))
    ai_card.columnconfigure(1, weight=1)
    r = 0

    win._ai_enabled_var = tk.BooleanVar(value=bool(getattr(win.cfg, "ai_assistant_enabled", False)))
    FluentToggleSwitch(
        ai_card, text=t("settings.enable_ai", "فعال‌سازی پالت فرمان هوش مصنوعی" if rtl else "Enable AI Command Palette"),
        subtitle=t("settings.enable_ai_sub", "بازنویسی، رسمی‌سازی، فینگلیش به فارسی و ترجمه فوری متن انتخابی" if rtl else "Instant rewrite, formal Persian, grammar fix, Pinglish → FA & translation via hotkey"),
        variable=win._ai_enabled_var, palette=pal, rtl=rtl,
    ).grid(row=r, column=0, columnspan=3, sticky="ew", **pad)
    r += 1

    ai_hk = getattr(win.cfg, "ai_assistant_hotkey", None) or HotkeySpec("G", ["Ctrl", "Shift"])
    win._ai_hotkey_var = tk.StringVar(value=hotkey_to_text(ai_hk))
    ttk.Label(ai_card, text=t("settings.ai_hotkey_lbl", "میانبر دستیار AI:" if rtl else "AI Hotkey:"), style="Card.TLabel").grid(row=r, column=0, sticky=align, **pad)
    hk_ent = ttk.Entry(ai_card, textvariable=win._ai_hotkey_var, width=20, justify="center")
    hk_ent.grid(row=r, column=1, sticky=align, **pad)
    _bind_live_capture(hk_ent, win._ai_hotkey_var)
    r += 1

    cur_pid = str(getattr(win.cfg, "ai_provider", "ollama") or "ollama").strip().lower()
    if cur_pid not in AI_PROVIDER_PRESETS:
        cur_pid = "ollama"
    disp_map = {
        pid: (preset.label_fa if rtl else preset.label_en) for pid, preset in AI_PROVIDER_PRESETS.items()
    }
    inv_disp = {v: k for k, v in disp_map.items()}
    win._ai_provider_var = tk.StringVar(value=cur_pid)
    win._ai_provider_display_var = tk.StringVar(value=disp_map[cur_pid])
    win._ai_endpoint_var = tk.StringVar(
        value=str(getattr(win.cfg, "ai_endpoint_url", "") or AI_PROVIDER_PRESETS[cur_pid].endpoint_url)
    )
    win._ai_model_var = tk.StringVar(
        value=str(getattr(win.cfg, "ai_model", "") or AI_PROVIDER_PRESETS[cur_pid].default_model)
    )
    win._ai_api_key_var = tk.StringVar(value=str(getattr(win.cfg, "ai_api_key", "")))
    win._ai_test_status_var = tk.StringVar(value="")

    ttk.Label(ai_card, text=t("settings.ai_provider_lbl", "سرویس‌دهنده:" if rtl else "AI Provider:"), style="Card.TLabel").grid(row=r, column=0, sticky=align, **pad)
    cb_prov = ttk.Combobox(ai_card, textvariable=win._ai_provider_display_var, values=list(disp_map.values()), state="readonly", width=28)
    cb_prov.grid(row=r, column=1, sticky="ew", **pad)
    r += 1

    ttk.Label(ai_card, text=t("settings.ai_endpoint_lbl", "آدرس سرور (Endpoint):" if rtl else "Base URL:"), style="Card.TLabel").grid(row=r, column=0, sticky=align, **pad)
    FluentEntry(ai_card, textvariable=win._ai_endpoint_var, placeholder="http://localhost:11434", width=34, palette=pal, rtl=False).grid(row=r, column=1, columnspan=2, sticky="ew", **pad)
    r += 1

    ttk.Label(ai_card, text=t("settings.ai_model_lbl", "مدل زبانی:" if rtl else "Model Name:"), style="Card.TLabel").grid(row=r, column=0, sticky=align, **pad)
    cb_model = ttk.Combobox(ai_card, textvariable=win._ai_model_var, values=[AI_PROVIDER_PRESETS[cur_pid].default_model], width=26)
    cb_model.grid(row=r, column=1, sticky="ew", **pad)

    def _on_prov_changed(_e: object = None) -> None:
        new_pid = inv_disp.get(win._ai_provider_display_var.get(), "ollama")
        old_defaults = {pr.endpoint_url for pr in AI_PROVIDER_PRESETS.values()}
        old_models = {pr.default_model for pr in AI_PROVIDER_PRESETS.values()}
        win._ai_provider_var.set(new_pid)
        preset = AI_PROVIDER_PRESETS[new_pid]
        if not win._ai_endpoint_var.get().strip() or win._ai_endpoint_var.get().strip() in old_defaults:
            win._ai_endpoint_var.set(preset.endpoint_url)
        if not win._ai_model_var.get().strip() or win._ai_model_var.get().strip() in old_models:
            win._ai_model_var.set(preset.default_model)
        cb_model.configure(values=[preset.default_model])
        btn_probe.configure(state="normal" if new_pid == "ollama" else "disabled")

    def _schedule_ui(fn: Any) -> None:
        root = getattr(win, "_root", None)
        if root is not None:
            try:
                if root.winfo_exists():
                    root.after(0, fn)
            except Exception:
                pass

    def _probe_ollama() -> None:
        ep = win._ai_endpoint_var.get().strip() or "http://localhost:11434"
        win._ai_test_status_var.set(t("settings.ai_probing", "در حال بررسی..." if rtl else "Probing..."))

        def _worker() -> None:
            try:
                models = list_ollama_models(ep)
                msg = f"{len(models)} مدل یافت شد" if rtl else f"{len(models)} models found"
                _schedule_ui(lambda: (cb_model.configure(values=models or [AI_PROVIDER_PRESETS["ollama"].default_model]), win._ai_model_var.set(models[0]) if models and not win._ai_model_var.get().strip() else None, win._ai_test_status_var.set(msg)))
            except Exception as exc:  # noqa: BLE001
                err = str(exc)[:46]
                _schedule_ui(lambda m=err: win._ai_test_status_var.set(m))

        threading.Thread(target=_worker, daemon=True).start()

    btn_probe = FluentPillButton(
        ai_card, text=t("settings.ai_probe_btn", "مدل‌های Ollama" if rtl else "Probe Models"),
        icon="search", variant="secondary", palette=pal, rtl=rtl, parent_bg=pal.bg_surface,
        height=28, width=140, state="normal" if cur_pid == "ollama" else "disabled", command=_probe_ollama,
    )
    btn_probe.grid(row=r, column=2, sticky=align, **pad)
    cb_prov.bind("<<ComboboxSelected>>", _on_prov_changed)
    r += 1

    ttk.Label(ai_card, text=t("settings.ai_key_lbl", "کلید API (امن DPAPI):" if rtl else "API Key (DPAPI):"), style="Card.TLabel").grid(row=r, column=0, sticky=align, **pad)
    FluentEntry(
        ai_card, textvariable=win._ai_api_key_var, placeholder="sk-... (optional for Ollama)",
        width=28, palette=pal, rtl=False, leading_icon="key", clearable=True, password=True,
    ).grid(row=r, column=1, sticky="ew", **pad)

    def _test_conn() -> None:
        pid = win._ai_provider_var.get().strip().lower()
        ep = win._ai_endpoint_var.get().strip()
        key = win._ai_api_key_var.get().strip()
        win._ai_test_status_var.set(t("settings.ai_testing", "در حال تست اتصال..." if rtl else "Testing connection..."))

        def _worker() -> None:
            ok, detail = probe_provider_connection(pid, ep, api_key=key)
            prefix = "✓ " if ok else "✕ "
            _schedule_ui(lambda: win._ai_test_status_var.set(f"{prefix}{detail}"))

        threading.Thread(target=_worker, daemon=True).start()

    FluentPillButton(
        ai_card, text=t("settings.ai_test_btn", "تست اتصال" if rtl else "Test Connection"),
        icon="bolt", variant="primary", palette=pal, rtl=rtl, parent_bg=pal.bg_surface,
        height=28, width=140, command=_test_conn,
    ).grid(row=r, column=2, sticky=align, **pad)
    r += 1

    ttk.Label(ai_card, textvariable=win._ai_test_status_var, style="CardSub.TLabel").grid(row=r, column=1, columnspan=2, sticky=align, **pad)
    return row + 1

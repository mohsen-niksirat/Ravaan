"""Voice Dictation card, Model Manager & live mic level meter for Settings."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from typing import Any

from ravan.core.i18n import is_rtl, t
from ravan.core.model_manager import VOICE_MODELS, ModelManager
from ravan.platform.audio import MicrophoneCapture, list_input_devices
from ravan.ui.settings_general import _bind_live_capture, _get_win_palette
from ravan.ui.widgets import (
    FluentCard,
    FluentEntry,
    FluentPillButton,
    FluentSegmentedControl,
    FluentToggleSwitch,
)


def stop_voice_preview(win: Any) -> None:
    """Stop any running microphone test stream and model download on tab/window close."""
    dl_cancel = getattr(win, "_voice_dl_cancel", None)
    if dl_cancel is not None:
        try:
            dl_cancel.set()
        except Exception:
            pass
        win._voice_dl_cancel = None

    job = getattr(win, "_mic_meter_job", None)
    root = getattr(win, "_root", None)
    if job is not None and root is not None:
        try:
            root.after_cancel(job)
        except Exception:
            pass
        win._mic_meter_job = None

    cap = getattr(win, "_mic_test_capture", None)
    if cap is not None:
        try:
            cap.stop()
        except Exception:
            pass
        win._mic_test_capture = None


def build_voice_card(win: Any, frm: ttk.Frame, row: int, pad: dict[str, Any]) -> int:
    """Render the Voice 2.0 card (Engine Mode, Model Manager, Mic Test, Cloud Whisper)."""
    rtl = is_rtl()
    pal = _get_win_palette(win)
    align, opp = ("e", "w") if rtl else ("w", "e")

    v_card = FluentCard(
        frm, t("settings.voice_card_title", "دیکته صوتی هوشمند (Voice 2.0)" if rtl else "Voice Dictation (Voice 2.0)"),
        padding=12, palette=pal, rtl=rtl, icon="mic",
    )
    v_card.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
    v_card.columnconfigure(1, weight=1)
    r = 0

    win._voice_enabled_var = tk.BooleanVar(value=bool(getattr(win.cfg, "voice_dictation_enabled", False)))
    FluentToggleSwitch(
        v_card, text=t("settings.enable_voice", "فعال‌سازی تایپ صوتی با میانبر" if rtl else "Enable global Voice Dictation"),
        subtitle=t("settings.enable_voice_sub", "ضبط ایمن در حافظه رم (بدون ذخیره فایل صوتی روی دیسک)" if rtl else "Streams mic audio strictly in RAM — never writes temp audio files to disk"),
        variable=win._voice_enabled_var, palette=pal, rtl=rtl,
    ).grid(row=r, column=0, columnspan=3, sticky="ew", **pad)
    r += 1

    from ravan.core.config import HotkeySpec, hotkey_to_text

    v_hk = getattr(win.cfg, "voice_dictation_hotkey", None) or HotkeySpec("V", ["Ctrl", "Alt"])
    win._voice_hotkey_var = tk.StringVar(value=hotkey_to_text(v_hk))
    ttk.Label(v_card, text=t("settings.voice_hotkey_lbl", "میانبر دیکته صوتی:" if rtl else "Voice Hotkey:"), style="Card.TLabel").grid(row=r, column=0, sticky=align, **pad)
    v_hk_ent = ttk.Entry(v_card, textvariable=win._voice_hotkey_var, width=20, justify="center")
    v_hk_ent.grid(row=r, column=1, sticky=align, **pad)
    _bind_live_capture(v_hk_ent, win._voice_hotkey_var)
    r += 1

    win._voice_mode_var = tk.StringVar(value=str(getattr(win.cfg, "voice_mode", "offline")))
    ttk.Label(v_card, text=t("settings.voice_mode_lbl", "حالت موتور صوتی:" if rtl else "Voice Engine Mode:"), style="Card.TLabel").grid(row=r, column=0, sticky=align, **pad)
    FluentSegmentedControl(
        v_card,
        options=[
            ("offline", t("settings.voice_mode_off", "آفلاین محلی" if rtl else "Offline")),
            ("hybrid", t("settings.voice_mode_hyb", "هیبرید" if rtl else "Hybrid")),
            ("cloud", t("settings.voice_mode_cld", "ابری API" if rtl else "Cloud API")),
        ],
        variable=win._voice_mode_var, palette=pal, rtl=rtl,
    ).grid(row=r, column=1, columnspan=2, sticky=align, **pad)
    r += 1

    win._voice_lang_var = tk.StringVar(value=str(getattr(win.cfg, "voice_language", "fa")))
    ttk.Label(v_card, text=t("settings.voice_lang_lbl", "زبان گفتار:" if rtl else "Spoken Language:"), style="Card.TLabel").grid(row=r, column=0, sticky=align, **pad)
    FluentSegmentedControl(
        v_card,
        options=[("fa", "فارسی" if rtl else "Persian (FA)"), ("en", "انگلیسی" if rtl else "English (EN)"), ("auto", "خودکار" if rtl else "Auto")],
        variable=win._voice_lang_var, palette=pal, rtl=rtl,
    ).grid(row=r, column=1, columnspan=2, sticky=align, **pad)
    r += 1

    # Microphone Selector + Live Level Bar Test
    r = _build_mic_row(win, v_card, r, pad, pal, rtl, align)
    # Offline Whisper Model Manager
    r = _build_model_manager_row(win, v_card, r, pad, pal, rtl, align)

    # Cloud Whisper Fields
    win._voice_cloud_endpoint_var = tk.StringVar(value=str(getattr(win.cfg, "voice_cloud_endpoint", "https://api.openai.com/v1")))
    ttk.Label(v_card, text=t("settings.voice_cloud_ep", "آدرس Whisper ابری:" if rtl else "Cloud Endpoint:"), style="Card.TLabel").grid(row=r, column=0, sticky=align, **pad)
    FluentEntry(v_card, textvariable=win._voice_cloud_endpoint_var, placeholder="https://api.openai.com/v1", width=34, palette=pal, rtl=False).grid(row=r, column=1, columnspan=2, sticky="ew", **pad)
    r += 1

    win._voice_cloud_model_var = tk.StringVar(value=str(getattr(win.cfg, "voice_cloud_model", "whisper-1")))
    ttk.Label(v_card, text=t("settings.voice_cloud_mdl", "مدل صوتی ابری:" if rtl else "Cloud Model:"), style="Card.TLabel").grid(row=r, column=0, sticky=align, **pad)
    FluentEntry(v_card, textvariable=win._voice_cloud_model_var, placeholder="whisper-1", width=26, palette=pal, rtl=False).grid(row=r, column=1, sticky="ew", **pad)
    r += 1

    win._voice_api_key_var = tk.StringVar(value=str(getattr(win.cfg, "voice_api_key", "")))
    ttk.Label(v_card, text=t("settings.voice_api_key", "کلید API صوتی (DPAPI):" if rtl else "Voice API Key (DPAPI):"), style="Card.TLabel").grid(row=r, column=0, sticky=align, **pad)
    FluentEntry(v_card, textvariable=win._voice_api_key_var, placeholder="sk-... / gsk_...", width=32, palette=pal, rtl=False, leading_icon="key", clearable=True, password=True).grid(row=r, column=1, columnspan=2, sticky="ew", **pad)
    return row + 1


def _build_mic_row(win: Any, card: FluentCard, r: int, pad: dict[str, Any], pal: Any, rtl: bool, align: str) -> int:
    devices = list_input_devices()
    default_lbl = t("settings.mic_default", "میکروفن پیش‌فرض سیستم" if rtl else "System Default Microphone")
    dev_map: dict[str, int] = {default_lbl: -1}
    for did, name in devices:
        dev_map[f"{name} (#{did})"] = did
    win._voice_device_map = dev_map
    cur_did = int(getattr(win.cfg, "voice_device_id", -1))
    inv_map = {v: k for k, v in dev_map.items()}
    win._voice_device_id_var = tk.IntVar(value=cur_did)
    win._voice_device_display_var = tk.StringVar(value=inv_map.get(cur_did, default_lbl))

    ttk.Label(card, text=t("settings.voice_mic_lbl", "میکروفن ورودی:" if rtl else "Input Microphone:"), style="Card.TLabel").grid(row=r, column=0, sticky=align, **pad)
    cb_dev = ttk.Combobox(card, textvariable=win._voice_device_display_var, values=list(dev_map.keys()), state="readonly", width=28)
    cb_dev.grid(row=r, column=1, sticky="ew", **pad)

    def _on_dev_pick(_e: object = None) -> None:
        win._voice_device_id_var.set(win._voice_device_map.get(win._voice_device_display_var.get(), -1))

    cb_dev.bind("<<ComboboxSelected>>", _on_dev_pick)
    meter_canvas = tk.Canvas(card, width=150, height=16, bg=pal.bg_interactive, highlightthickness=1, highlightbackground=pal.border_subtle)
    meter_canvas.grid(row=r + 1, column=1, sticky="ew", **pad)

    def _draw_meter(level: float) -> None:
        if not meter_canvas.winfo_exists():
            return
        w = max(80, int(meter_canvas.winfo_width() or 150))
        fill_w = max(0, int(w * max(0.0, min(1.0, level))))
        meter_canvas.delete("all")
        if fill_w > 0:
            col = pal.danger if level > 0.85 else (pal.success if level > 0.2 else pal.accent)
            meter_canvas.create_rectangle(2, 2, max(4, fill_w - 2), 14, fill=col, outline="")

    win._mic_test_capture = None
    win._mic_meter_job = None
    win._voice_mic_status_var = tk.StringVar(value="")

    def _poll_meter() -> None:
        cap = getattr(win, "_mic_test_capture", None)
        if cap is None or not cap.is_recording or not meter_canvas.winfo_exists():
            _draw_meter(0.0)
            return
        _draw_meter(cap.latest_rms)
        root = getattr(win, "_root", None)
        if root is not None:
            win._mic_meter_job = root.after(50, _poll_meter)

    def _toggle_mic_test() -> None:
        if getattr(win, "_mic_test_capture", None) is not None and win._mic_test_capture.is_recording:
            stop_voice_preview(win)
            btn_mic.configure(text=t("settings.test_mic", "تست میکروفن" if rtl else "Test Mic"), variant="secondary")
            win._voice_mic_status_var.set("")
            _draw_meter(0.0)
            return
        _on_dev_pick()
        cap = MicrophoneCapture(device_id=win._voice_device_id_var.get())
        if cap.start():
            win._mic_test_capture = cap
            btn_mic.configure(text=t("settings.stop_mic", "توقف تست" if rtl else "Stop Test"), variant="danger")
            win._voice_mic_status_var.set(t("settings.mic_listening", "در حال تست..." if rtl else "Listening..."))
            _poll_meter()
        else:
            win._voice_mic_status_var.set(cap.last_error or t("voice.mic_unavailable", "Mic unavailable"))

    btn_mic = FluentPillButton(
        card, text=t("settings.test_mic", "تست میکروفن" if rtl else "Test Mic"),
        icon="mic", variant="secondary", palette=pal, rtl=rtl, height=28, width=114, command=_toggle_mic_test,
    )
    btn_mic.grid(row=r, column=2, sticky=align, **pad)
    ttk.Label(card, textvariable=win._voice_mic_status_var, style="CardSub.TLabel").grid(row=r + 1, column=2, sticky=align, **pad)
    return r + 2


def _build_model_manager_row(win: Any, card: FluentCard, r: int, pad: dict[str, Any], pal: Any, rtl: bool, align: str) -> int:
    mgr = ModelManager()
    model_labels = {spec.model_id: (spec.name_fa if rtl else spec.name_en) for spec in VOICE_MODELS}
    inv_models = {v: k for k, v in model_labels.items()}
    cur_mid = str(getattr(win.cfg, "voice_model_id", "whisper-base"))
    win._voice_model_id_var = tk.StringVar(value=cur_mid)
    win._voice_model_display_var = tk.StringVar(value=model_labels.get(cur_mid, model_labels["whisper-base"]))
    win._voice_model_status_var = tk.StringVar(value="")

    ttk.Label(card, text=t("settings.voice_model_lbl", "مدل آفلاین Whisper:" if rtl else "Offline Whisper Model:"), style="Card.TLabel").grid(row=r, column=0, sticky=align, **pad)
    cb_m = ttk.Combobox(card, textvariable=win._voice_model_display_var, values=list(model_labels.values()), state="readonly", width=32)
    cb_m.grid(row=r, column=1, sticky="ew", **pad)

    acts = tk.Frame(card, bg=pal.bg_surface)
    acts.grid(row=r, column=2, sticky=align, **pad)
    prog_bar = ttk.Progressbar(card, mode="determinate", maximum=100, length=180)
    prog_bar.grid(row=r + 1, column=1, sticky="ew", **pad)
    ttk.Label(card, textvariable=win._voice_model_status_var, style="CardSub.TLabel").grid(row=r + 1, column=2, sticky=align, **pad)

    def _refresh_status() -> None:
        mid = inv_models.get(win._voice_model_display_var.get(), "whisper-base")
        win._voice_model_id_var.set(mid)
        installed = mgr.is_installed(mid)
        spec = mgr.get_spec(mid)
        if installed:
            win._voice_model_status_var.set(t("settings.model_ready", "نصب‌شده ✓ (SHA-256)" if rtl else "Installed ✓ (SHA-256)"))
            prog_bar["value"] = 100
        else:
            win._voice_model_status_var.set(f"{t('settings.model_missing', 'نصب‌نشده' if rtl else 'Not installed')} (~{spec.size_mb} MB)")
            prog_bar["value"] = 0
        btn_del.configure(state="normal" if installed else "disabled")

    def _start_dl() -> None:
        if getattr(win, "_voice_dl_cancel", None) is not None:
            win._voice_dl_cancel.set()
            win._voice_dl_cancel = None
            btn_dl.configure(text=t("settings.model_download", "دانلود" if rtl else "Download"), variant="primary")
            return
        mid = inv_models.get(win._voice_model_display_var.get(), "whisper-base")
        cancel_ev = threading.Event()
        win._voice_dl_cancel = cancel_ev
        btn_dl.configure(text=t("settings.model_cancel", "لغو" if rtl else "Cancel"), variant="danger")

        def _ui(fn: Any) -> None:
            root = getattr(win, "_root", None)
            if root is not None:
                try:
                    if root.winfo_exists():
                        root.after(0, fn)
                except Exception:
                    pass

        def _worker() -> None:
            def _on_prog(done: int, total: int, stage: str) -> None:
                pct = int((done * 100) / max(1, total))
                _ui(lambda p_val=pct, st=stage: (prog_bar.__setitem__("value", p_val), win._voice_model_status_var.set(f"{st} ({p_val}%)")))

            try:
                mgr.download_model(mid, on_progress=_on_prog, cancel_event=cancel_ev)
                _ui(lambda: (setattr(win, "_voice_dl_cancel", None), btn_dl.configure(text=t("settings.model_download", "دانلود" if rtl else "Download"), variant="primary"), _refresh_status()))
            except Exception as exc:  # noqa: BLE001
                err = str(exc)[:48]
                _ui(lambda m=err: (setattr(win, "_voice_dl_cancel", None), btn_dl.configure(text=t("settings.model_download", "دانلود" if rtl else "Download"), variant="primary"), win._voice_model_status_var.set(m)))

        threading.Thread(target=_worker, daemon=True).start()

    def _delete_model() -> None:
        mid = win._voice_model_id_var.get()
        mgr.delete_model(mid)
        _refresh_status()

    btn_dl = FluentPillButton(acts, text=t("settings.model_download", "دانلود" if rtl else "Download"), icon="cloud", variant="primary", palette=pal, rtl=rtl, parent_bg=pal.bg_surface, height=26, width=98, command=_start_dl)
    btn_dl.pack(side="right" if rtl else "left", padx=2)
    btn_del = FluentPillButton(acts, text=t("settings.model_delete", "حذف" if rtl else "Delete"), variant="danger", palette=pal, rtl=rtl, parent_bg=pal.bg_surface, height=26, width=64, command=_delete_model)
    btn_del.pack(side="right" if rtl else "left", padx=2)

    cb_m.bind("<<ComboboxSelected>>", lambda _e=None: _refresh_status())
    _refresh_status()
    return r + 2

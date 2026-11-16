"""Comprehensive tests for Phase 3 (AI 2.0 streaming, Spotlight popup, Diff & Settings tab)."""

from __future__ import annotations

import io
import json
import logging
import threading
import tkinter as tk
import urllib.request
from pathlib import Path
from unittest.mock import patch

import pytest

from ravan.core.ai import (
    AI_PRESET_SPECS,
    AI_PROVIDER_PRESETS,
    PROMPTS,
    AIAssistantEngine,
    OllamaProvider,
    OpenAICompatibleProvider,
    list_ollama_models,
    probe_provider_connection,
)
from ravan.core.config import Config
from ravan.core.i18n import set_locale
from ravan.ui.ai_diff import compute_word_diff, summarize_source_preview
from ravan.ui.ai_popup import AIAssistantPopup
from ravan.ui.settings import SettingsWindow
from ravan.ui.theme import create_managed_toplevel, destroy_managed_toplevel


def test_ollama_stream_and_cancellation() -> None:
    ndjson = (
        json.dumps({"response": "سلام ", "done": False}) + "\n"
        + json.dumps({"response": "دنیا", "done": False}) + "\n"
        + json.dumps({"response": "", "done": True}) + "\n"
    ).encode("utf-8")
    provider = OllamaProvider(endpoint_url="http://localhost:11434", model="qwen2.5:7b")

    with patch.object(urllib.request, "urlopen", return_value=io.BytesIO(ndjson)):
        chunks = list(provider.generate_stream("سلام"))
        assert chunks == ["سلام ", "دنیا"]

    cancel = threading.Event()
    collected: list[str] = []
    with patch.object(urllib.request, "urlopen", return_value=io.BytesIO(ndjson)):
        for ch in provider.generate_stream("سلام", cancel_event=cancel):
            collected.append(ch)
            cancel.set()
    assert collected == ["سلام "]


def test_openai_sse_stream_and_presets() -> None:
    sse = (
        b"data: {\"choices\": [{\"delta\": {\"content\": \"Dear \"}}]}\n\n"
        b"data: {\"choices\": [{\"delta\": {\"content\": \"team.\"}}]}\n\n"
        b"data: [DONE]\n\n"
    )
    provider = OpenAICompatibleProvider(
        endpoint_url=AI_PROVIDER_PRESETS["groq"].endpoint_url,
        api_key_encrypted="mock_plain_or_dpapi_key",
        model="llama-3.3-70b-versatile",
    )
    with (
        patch("ravan.core.ai.decrypt_secret", return_value="gsk-test-token"),
        patch.object(urllib.request, "urlopen", return_value=io.BytesIO(sse)) as mock_open,
    ):
        chunks = list(provider.generate_stream("hi"))
        assert "".join(chunks) == "Dear team."
        req = mock_open.call_args[0][0]
        assert req.full_url == "https://api.groq.com/openai/v1/chat/completions"
        assert req.get_header("Accept") == "text/event-stream"


def test_bilingual_presets_and_zero_log_stream(caplog) -> None:
    expected_actions = {"rewrite", "formal_fa", "pro_en", "fix_grammar", "pinglish_to_fa", "translate", "summarize"}
    assert {spec[0] for spec in AI_PRESET_SPECS} == expected_actions
    assert expected_actions <= set(PROMPTS.keys())

    provider = OllamaProvider()
    engine = AIAssistantEngine(provider)
    secret = "CONFIDENTIAL_MEDICAL_987654"
    ndjson = (json.dumps({"response": "خروجی امن", "done": True}) + "\n").encode("utf-8")

    with (
        patch.object(urllib.request, "urlopen", side_effect=lambda *_a, **_kw: io.BytesIO(ndjson)),
        caplog.at_level(logging.DEBUG),
    ):
        for act in expected_actions:
            out = "".join(engine.process_stream(act, secret))
            assert out == "خروجی امن"

    for rec in caplog.records:
        assert secret not in rec.message
        assert "987654" not in rec.message


def test_list_ollama_models_and_connection_probe() -> None:
    tags_json = json.dumps({"models": [{"name": "qwen2.5:7b"}, {"name": "llama3.2:3b"}]}).encode("utf-8")
    with patch.object(urllib.request, "urlopen", side_effect=lambda *_a, **_kw: io.BytesIO(tags_json)):
        models = list_ollama_models("http://localhost:11434")
        assert models == ["qwen2.5:7b", "llama3.2:3b"]
        ok, msg = probe_provider_connection("ollama", "http://localhost:11434")
        assert ok is True
        assert "qwen2.5:7b" in msg

    ok_no_key, msg_no_key = probe_provider_connection("openai", "https://api.openai.com/v1", api_key="")
    assert ok_no_key is False
    assert "key" in msg_no_key.lower()


def test_ai_word_diff_and_preview() -> None:
    spans = compute_word_diff("سلام خوبی من میرم", "سلام خوبید من می‌روم")
    ops = [op for op, _ in spans]
    assert "del" in ops and "ins" in ops
    assert "خوبی" in "".join(txt for op, txt in spans if op == "del")
    assert "خوبید" in "".join(txt for op, txt in spans if op == "ins")

    excerpt, ch_n, wd_n = summarize_source_preview("این یک متن آزمایشی بسیار طولانی برای تست خلاصه‌سازی پیش‌نمایش است", max_chars=24)
    assert excerpt.endswith("…")
    assert ch_n > 24
    assert wd_n == 11


def test_ai_popup_streaming_diff_and_replace() -> None:
    try:
        top, owned_root = create_managed_toplevel(None)
    except tk.TclError as exc:
        pytest.skip(f"Tkinter display unavailable: {exc}")

    set_locale("fa")
    replaced: list[str] = []
    copied: list[str] = []

    def _stream(action: str, text: str, custom: str, cancel: threading.Event | None):
        yield "متن "
        yield "بازنویسی‌شده"

    popup = AIAssistantPopup(
        parent=top,
        on_replace=replaced.append,
        on_copy=copied.append,
        process_callback=lambda a, t, c: "متن بازنویسی‌شده",
        theme_mode="dark",
        stream_callback=_stream,
    )
    try:
        popup.show("متن خام من", 120, 120)
        assert popup._top is not None
        assert len(popup._chip_buttons) == 7
        assert popup._ent_custom is not None
        # Empty placeholder must return "" cleanly, never placeholder text
        assert popup._ent_custom.get() == ""

        popup._finish_stream("متن بازنویسی‌شده", ok=True, cancelled=False)
        assert popup._current_clean_output() == "متن بازنویسی‌شده"

        # Toggle diff mode ON and verify Replace still sends clean output (not merged del/ins text!)
        popup._toggle_diff()
        assert popup._diff_mode is True
        assert popup._txt_output is not None
        diff_rendered = popup._txt_output.get("1.0", tk.END)
        assert "خام" in diff_rendered and "بازنویسی‌شده" in diff_rendered
        popup._do_replace()
        assert replaced == ["متن بازنویسی‌شده"]
    finally:
        popup.hide()
        destroy_managed_toplevel(top, owned_root)


def test_settings_ai_voice_tab_save_and_reset(tmp_path) -> None:
    try:
        top, owned_root = create_managed_toplevel(None)
    except tk.TclError as exc:
        pytest.skip(f"Tkinter display unavailable: {exc}")

    set_locale("en")
    cfg = Config()
    cfg.ai_assistant_enabled = False
    cfg.voice_dictation_enabled = False
    saved_cfgs: list[Config] = []

    win = SettingsWindow(cfg, on_saved=saved_cfgs.append, parent=top)
    try:
        with patch("ravan.ui.settings_voice_panel.list_input_devices", return_value=[(0, "USB Mic")]):
            win.show()
            win.tick()
            assert hasattr(win, "_ai_enabled_var")
            assert hasattr(win, "_voice_enabled_var")
            assert hasattr(win, "_voice_mode_var")

            win._ai_enabled_var.set(True)
            win._ai_provider_var.set("gemini")
            win._ai_endpoint_var.set(AI_PROVIDER_PRESETS["gemini"].endpoint_url)
            win._ai_model_var.set("gemini-2.5-flash")
            win._ai_api_key_var.set("AIzaTestKey123")
            win._voice_enabled_var.set(True)
            win._voice_mode_var.set("hybrid")
            win._voice_lang_var.set("en")

            with (
                patch("ravan.ui.settings_save.save_config"),
                patch("ravan.ui.settings_save.save_user_words", create=True),
                patch("ravan.core.user_dict.save_user_words"),
                patch("ravan.ui.settings_save.is_startup_enabled", return_value=False),
            ):
                win._save()

            assert cfg.ai_assistant_enabled is True
            assert cfg.ai_provider == "gemini"
            assert cfg.ai_model == "gemini-2.5-flash"
            assert cfg.ai_api_key == "AIzaTestKey123"
            assert cfg.voice_dictation_enabled is True
            assert cfg.voice_mode == "hybrid"
            assert cfg.voice_language == "en"
            assert saved_cfgs

            with patch("ravan.ui.settings_reset.messagebox.askyesno", return_value=True):
                win._reset_tab_defaults("ai_voice")
            assert win._ai_enabled_var.get() is False
            assert win._ai_provider_var.get() == "ollama"
            assert win._voice_mode_var.get() == "offline"
    finally:
        win._close()
        destroy_managed_toplevel(top, owned_root)


def test_phase3_modules_respect_line_ceiling() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    for rel in (
        "ravan/core/ai.py",
        "ravan/ui/ai_diff.py",
        "ravan/ui/ai_popup.py",
        "ravan/ui/selection_toolbar.py",
        "ravan/ui/app_ai.py",
        "ravan/ui/settings_ai_voice.py",
        "ravan/ui/settings_voice_panel.py",
    ):
        lines = len((repo_root / rel).read_text(encoding="utf-8").splitlines())
        assert lines <= 400, f"{rel} has {lines} lines (exceeds 400-line ceiling)"

"""Tests for Phase 8: AI Text Assistant (Target H) with zero-log privacy guarantee."""

from __future__ import annotations

import io
import json
import logging
import urllib.request
from unittest.mock import MagicMock, patch

from ravan.core.ai import (
    AIAssistantEngine,
    OllamaProvider,
    OpenAICompatibleProvider,
)
from ravan.core.config import Config
from ravan.ui.app import RavanApp


class DummyOverlay:
    def __init__(self) -> None:
        self.predicting = False
        self.clipboard_open = False
        self.visible = False
    def hide(self) -> None: pass
    def destroy(self) -> None: pass
    def tick(self) -> None: pass


def test_ollama_request_structure_and_response():
    provider = OllamaProvider(endpoint_url="http://localhost:11434", model="qwen2.5:7b")

    mock_response = io.BytesIO(json.dumps({"response": "متن بازنویسی شده"}).encode("utf-8"))

    with patch.object(urllib.request, "urlopen", return_value=mock_response) as mock_urlopen:
        res = provider.generate("تست پرامپت")
        assert res == "متن بازنویسی شده"

        # Verify request structure
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert req.get_method() == "POST"
        assert req.full_url == "http://localhost:11434/api/generate"
        body = json.loads(req.data.decode("utf-8"))
        assert body["model"] == "qwen2.5:7b"
        assert body["prompt"] == "تست پرامپت"
        assert body["stream"] is False


def test_openai_request_structure_and_auth():
    provider = OpenAICompatibleProvider(
        endpoint_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
    )
    with patch("ravan.core.ai.decrypt_secret", return_value="sk-test-secret-key"):
        provider.api_key_encrypted = "dummy_encrypted"
        mock_response = io.BytesIO(
            json.dumps({"choices": [{"message": {"content": "Translated text"}}]}).encode("utf-8")
        )
        with patch.object(urllib.request, "urlopen", return_value=mock_response) as mock_urlopen:
            res = provider.generate("Translate this")
            assert res == "Translated text"

            req = mock_urlopen.call_args[0][0]
            assert req.full_url == "https://api.openai.com/v1/chat/completions"
            assert req.get_header("Authorization") == "Bearer sk-test-secret-key"
            body = json.loads(req.data.decode("utf-8"))
            assert body["model"] == "gpt-4o-mini"
            assert body["messages"][-1]["content"] == "Translate this"


def test_dpapi_secret_encryption_roundtrip():
    provider = OpenAICompatibleProvider()
    with patch("ravan.core.ai.encrypt_secret", return_value="enc_token_123") as mock_enc, \
         patch("ravan.core.ai.decrypt_secret", return_value="sk-my-api-key") as mock_dec:
        provider.set_api_key("sk-my-api-key")
        assert provider.api_key_encrypted == "enc_token_123"
        assert mock_enc.called

        decrypted = provider.get_api_key()
        assert decrypted == "sk-my-api-key"
        assert mock_dec.called


def test_ai_prompt_builders():
    engine = AIAssistantEngine(provider=MagicMock())

    p_rewrite = engine.build_prompt("rewrite", "یک متن تستی")
    assert "یک متن تستی" in p_rewrite
    assert "بازنویسی" in p_rewrite

    p_grammar = engine.build_prompt("fix_grammar", "متن پر غلط")
    assert "متن پر غلط" in p_grammar
    assert "رسم‌الخط" in p_grammar

    p_trans = engine.build_prompt("translate", "hello world")
    assert "hello world" in p_trans
    assert "Translate" in p_trans

    p_custom = engine.build_prompt("custom", "ورودی", custom_instruction="به شعر تبدیل کن")
    assert "ورودی" in p_custom
    assert "به شعر تبدیل کن" in p_custom


def test_privacy_zero_log_guarantee(caplog):
    """Rigorous privacy test: Ensure confidential user text is NEVER written to logs."""
    mock_provider = MagicMock()
    mock_provider.generate.return_value = "پاسخ امن"
    engine = AIAssistantEngine(provider=mock_provider)

    secret_input = "SUPER_CONFIDENTIAL_USER_PASSWORD_OR_MEDICAL_RECORD_999888"

    with caplog.at_level(logging.DEBUG):
        out = engine.process("rewrite", secret_input)
        assert out == "پاسخ امن"

    # Verify that secret_input DOES NOT appear anywhere in the log records
    for record in caplog.records:
        assert secret_input not in record.message, f"Privacy violation! Secret found in log: {record.message}"
        assert "999888" not in record.message


def test_app_ai_trigger_integration():
    cfg = Config()
    cfg.ai_assistant_enabled = True

    with patch("ravan.ui.app.KeyboardHook"), patch("ravan.ui.ai_popup.AIAssistantPopup.show") as mock_popup_show:
        app = RavanApp(cfg, overlay=DummyOverlay())
        try:
            assert app.ai_engine is not None

            # Simulate selected text in clipboard
            with patch("ravan.ui.app_ai.get_clipboard_text", side_effect=["old_clip", "Selected text to rephrase"]):
                with patch("ravan.ui.app_ai.send_shortcut"):
                    app._trigger_ai_assistant()
                    assert mock_popup_show.called
                    args = mock_popup_show.call_args[0]
                    assert args[0] == "Selected text to rephrase"
        finally:
            app.stop()

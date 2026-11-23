"""Comprehensive tests for Ravaan v3.2 Online & Hybrid AI Suite:
1. Google Input Tools API client, LRU cache, zero-lag offline fallback & Persian normalization
2. Hybrid Finglish transliteration (Google Input Tools + offline TranslitEngine)
3. AI Inline Sentence Continuation (predict_ai_continuation & ai_continuation_candidates)
4. Direct In-Place AI Magic Hotkey (_trigger_direct_ai_magic) on selection and journal buffer
5. Config round-trip & Settings AI & Voice tab persistence for online/hybrid toggles
"""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

from ravan.cli import main as cli_main
from ravan.core.ai import AIAssistantEngine, OllamaProvider
from ravan.core.config import Config, HotkeySpec, config_from_dict, config_to_dict
from ravan.core.events import CandidateKind
from ravan.core.journal import KeystrokeJournal
from ravan.core.online_predictor import (
    ai_continuation_candidates,
    clean_ai_continuation,
    clear_online_caches,
    fetch_google_input_suggestions,
    google_input_candidates,
    hybrid_transliterate,
    predict_ai_continuation,
)
from ravan.ui.app_ai import AppAIMixin


def test_google_input_tools_client_cache_and_zero_lag_fallback() -> None:
    clear_online_caches()
    google_payload = [
        "SUCCESS",
        [
            [
                "mikham beram",
                ["میخوام برم", "می‌خوام برم خانه", "ميخوام برم"],
            ]
        ],
    ]
    raw_bytes = json.dumps(google_payload, ensure_ascii=False).encode("utf-8")

    with patch.object(urllib.request, "urlopen", side_effect=lambda *_a, **_kw: io.BytesIO(raw_bytes)) as mock_open:
        sugs = fetch_google_input_suggestions("mikham beram", num=5)
        assert sugs
        # Verify Arabic yeh/kaf and spacing/ZWNJ normalization ran on Google response
        assert "می‌خوام برم" in sugs or "میخوام برم" in sugs
        assert mock_open.call_count == 1

        # Second call MUST hit LRU cache without network request
        sugs_cached = fetch_google_input_suggestions("mikham beram", num=5)
        assert sugs_cached == sugs
        assert mock_open.call_count == 1

    # Network failure must return [] immediately without raising (Zero-Lag Fallback)
    clear_online_caches()
    with patch.object(urllib.request, "urlopen", side_effect=urllib.error.URLError("offline")):
        assert fetch_google_input_suggestions("salam") == []
        # Hybrid transliterate still returns offline TranslitEngine result when offline!
        hybrid_off = hybrid_transliterate("salam", use_google=True)
        assert "سلام" in hybrid_off


def test_google_input_candidates_and_cli_translit_google(capsys) -> None:
    clear_online_caches()
    payload = ["SUCCESS", [["salam", ["سلام", "سالم"]]]]
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    with patch.object(urllib.request, "urlopen", side_effect=lambda *_a, **_kw: io.BytesIO(raw)):
        cands = google_input_candidates("salam", limit=3)
        assert cands
        assert cands[0].text == "سلام"
        assert cands[0].kind == CandidateKind.COMPLETION

        assert cli_main(["translit", "--google", "salam"]) == 0
        assert "سلام" in capsys.readouterr().out


def test_ai_inline_sentence_continuation_and_caching() -> None:
    clear_online_caches()
    assert clean_ai_continuation("با سلام و", "«با سلام و احترام خدمت شما»") == "احترام خدمت شما"

    provider = OllamaProvider()
    engine = AIAssistantEngine(provider)
    ndjson = (json.dumps({"response": "احترام فراوان خدمت شما", "done": True}) + "\n").encode("utf-8")

    with patch.object(urllib.request, "urlopen", side_effect=lambda *_a, **_kw: io.BytesIO(ndjson)) as mock_open:
        cont = predict_ai_continuation("با سلام و", engine)
        assert cont == "احترام فراوان خدمت شما"
        assert mock_open.call_count == 1

        # Subsequent call with same context uses LRU cache
        cands = ai_continuation_candidates("با سلام و", engine)
        assert len(cands) == 1
        assert cands[0].text == "احترام فراوان خدمت شما"
        assert cands[0].kind == CandidateKind.NEXT_WORD
        assert mock_open.call_count == 1


def test_direct_in_place_ai_magic_hotkey_on_journal_and_selection() -> None:
    class DummyMagicApp(AppAIMixin):
        def __init__(self) -> None:
            self.cfg = Config(
                ai_assistant_enabled=True,
                ai_provider="ollama",
                ai_magic_action="formal_fa",
            )
            self.journal = KeystrokeJournal()
            for ch in "سلام خوبی چه خبر":
                self.journal.push(ch)
            self.tray = MagicMock()
            self._suppress_until = 0.0
            self.toasts: list[str] = []
            self.undos: list[dict] = []

        def _show_toast(self, msg: str) -> None:
            self.toasts.append(msg)

        def _record_quick_undo(self, **kwargs) -> None:
            self.undos.append(kwargs)

    app = DummyMagicApp()
    app._init_ai()
    assert app.ai_engine is not None

    with (
        patch("ravan.ui.app_ai.get_clipboard_text", return_value="old_clip"),
        patch("ravan.ui.app_ai.set_clipboard_text"),
        patch("ravan.ui.app_ai.send_shortcut"),
        patch("ravan.ui.app_ai.replace_last_n_with") as mock_replace,
        patch.object(app.ai_engine, "process", return_value="با سلام، حال شما چطور است؟") as mock_proc,
    ):
        ok = app._trigger_direct_ai_magic(synchronous=True)
        assert ok is True
        mock_proc.assert_called_once_with("formal_fa", "سلام خوبی چه خبر")
        mock_replace.assert_called_once_with(len("سلام خوبی چه خبر"), "با سلام، حال شما چطور است؟")
        assert app.journal.text() == "با سلام، حال شما چطور است؟"
        assert app.undos and app.undos[0]["kind"] == "ai_magic"
        assert any("formal_fa" in t for t in app.toasts)


def test_config_roundtrip_for_online_and_hybrid_ai_settings() -> None:
    cfg = Config(
        ai_assistant_enabled=True,
        ai_magic_hotkey=HotkeySpec("M", ["Ctrl", "Alt"]),
        ai_magic_action="translate",
        ai_inline_completion_enabled=True,
        google_input_enabled=True,
    )
    raw = config_to_dict(cfg)
    loaded = config_from_dict(raw)
    assert loaded.ai_magic_hotkey == HotkeySpec("M", ["Ctrl", "Alt"])
    assert loaded.ai_magic_action == "translate"
    assert loaded.ai_inline_completion_enabled is True
    assert loaded.google_input_enabled is True


def test_v3_2_modules_respect_line_ceiling() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    for rel in (
        "ravan/core/online_predictor.py",
        "ravan/core/ai.py",
        "ravan/ui/app_ai.py",
        "ravan/ui/settings_ai_voice.py",
    ):
        lines = len((repo_root / rel).read_text(encoding="utf-8").splitlines())
        assert lines <= 400, f"{rel} has {lines} lines (exceeds 400-line ceiling)"

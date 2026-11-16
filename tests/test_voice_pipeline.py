"""Integration tests for Phase 2 Voice 2.0 (ModelManager, RAM WAV, Cloud/Hybrid ASR, Pill)."""

from __future__ import annotations

import hashlib
import io
import json
import threading
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ravan.core.config import Config, config_from_dict, config_to_dict
from ravan.core.crypto import protect_secret
from ravan.core.model_manager import VOICE_MODELS, ModelManager, verify_file_sha256
from ravan.core.voice import (
    VoiceEngine,
    VoiceState,
    pcm16_to_wav_bytes,
    postprocess_dictation,
)
from ravan.ui.waveform_pill import WaveformPillWindow


def test_pcm16_to_wav_bytes_valid_in_memory() -> None:
    assert pcm16_to_wav_bytes(b"") == b""
    pcm = b"\x01\x00\xff\xff" * 400
    wav_bytes = pcm16_to_wav_bytes(pcm, sample_rate=16000, channels=1)
    assert wav_bytes[:4] == b"RIFF"
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
        assert wf.readframes(wf.getnframes()) == pcm


def test_postprocess_dictation_applies_persian_grammar_and_zwnj() -> None:
    raw = "سلام ، كتاب ها را بنام ما حتما آماده كنيد ."
    cleaned = postprocess_dictation(raw)
    assert "کتاب‌ها" in cleaned
    assert "به نام" in cleaned
    assert "حتماً" in cleaned
    assert "کنید." in cleaned


def test_model_manager_catalog_download_sha256_and_delete(tmp_path: Path) -> None:
    mgr = ModelManager(base_dir=tmp_path)
    items = mgr.list_models()
    assert len(items) == len(VOICE_MODELS)
    assert all(not m["installed"] for m in items)

    payload = b"fake-whisper-weights-payload" * 8
    real_sha = hashlib.sha256(payload).hexdigest()

    fake_resp = MagicMock()
    fake_resp.headers = {"Content-Length": str(len(payload))}
    fake_resp.read.side_effect = [payload[:100], payload[100:], b""]
    fake_resp.__enter__.return_value = fake_resp
    fake_resp.__exit__.return_value = False

    events: list[tuple[int, int, str]] = []
    with patch("ravan.core.model_manager.urllib.request.urlopen", return_value=fake_resp):
        downloaded = mgr.download_model(
            "whisper-tiny",
            on_progress=lambda dl, tot, st: events.append((dl, tot, st)),
            verify_checksum=False,
        )

    assert downloaded.is_file()
    assert downloaded.read_bytes() == payload
    assert verify_file_sha256(downloaded, real_sha) is True
    assert verify_file_sha256(downloaded, "0" * 64) is False
    assert mgr.is_installed("whisper-tiny") is True
    assert events[-1][2] == "ready"
    assert mgr.delete_model("whisper-tiny") is True
    assert mgr.is_installed("whisper-tiny") is False


def test_model_manager_download_sha256_mismatch_cleans_part(tmp_path: Path) -> None:
    mgr = ModelManager(base_dir=tmp_path)
    fake_resp = MagicMock()
    fake_resp.headers = {"Content-Length": "16"}
    fake_resp.read.side_effect = [b"corrupted-bytes!", b""]
    fake_resp.__enter__.return_value = fake_resp
    fake_resp.__exit__.return_value = False

    with (
        patch("ravan.core.model_manager.urllib.request.urlopen", return_value=fake_resp),
        pytest.raises(ValueError, match="SHA-256 verification failed"),
    ):
        mgr.download_model("whisper-tiny", verify_checksum=True)

    assert list(tmp_path.iterdir()) == []


def test_model_manager_download_cancellation(tmp_path: Path) -> None:
    mgr = ModelManager(base_dir=tmp_path)
    cancel = threading.Event()
    cancel.set()

    fake_resp = MagicMock()
    fake_resp.headers = {"Content-Length": "100"}
    fake_resp.__enter__.return_value = fake_resp
    fake_resp.__exit__.return_value = False

    with (
        patch("ravan.core.model_manager.urllib.request.urlopen", return_value=fake_resp),
        pytest.raises(InterruptedError),
    ):
        mgr.download_model("whisper-tiny", cancel_event=cancel)
    assert list(tmp_path.iterdir()) == []


def test_voice_engine_cloud_and_hybrid_multipart_with_dpapi() -> None:
    enc_key = protect_secret("sk-voice-test-12345")
    engine = VoiceEngine(
        model_name="whisper-base",
        language="fa",
        mode="hybrid",
        cloud_endpoint="https://api.groq.com/openai/v1",
        cloud_model="whisper-large-v3-turbo",
        api_key_encrypted=enc_key,
    )
    assert engine.start_recording() is True
    engine.record_chunk(b"\x00\x10\xff\xef" * 200)
    assert engine.latest_rms > 0.0

    fake_http_resp = MagicMock()
    fake_http_resp.read.return_value = json.dumps({"text": "مي روم و كتاب ها را بنام تو ثبت كنم"}).encode("utf-8")
    fake_http_resp.__enter__.return_value = fake_http_resp
    fake_http_resp.__exit__.return_value = False

    with patch("ravan.core.voice.urllib.request.urlopen", return_value=fake_http_resp) as mock_open:
        text = engine.stop_recording_and_transcribe()

    req = mock_open.call_args[0][0]
    assert req.full_url == "https://api.groq.com/openai/v1/audio/transcriptions"
    assert req.get_header("Authorization") == "Bearer sk-voice-test-12345"
    assert b"RIFF" in req.data
    assert "می‌روم" in text
    assert "کتاب‌ها" in text
    assert "به نام" in text
    assert engine.state == VoiceState.IDLE


def test_config_roundtrip_voice2_and_credential_storage() -> None:
    cfg = Config(
        voice_dictation_enabled=True,
        voice_mode="hybrid",
        voice_model_id="whisper-small",
        voice_language="auto",
        voice_device_id=1,
        voice_cloud_endpoint="https://api.groq.com/openai/v1",
        voice_cloud_model="whisper-large-v3-turbo",
        voice_api_key="gsk_secret_voice",
    )
    d = config_to_dict(cfg)
    assert str(d["voice_api_key"]).startswith("wincred:")

    loaded = config_from_dict(d)
    assert loaded.voice_mode == "hybrid"
    assert loaded.voice_model_id == "whisper-small"
    assert loaded.voice_language == "auto"
    assert loaded.voice_device_id == 1
    assert loaded.voice_cloud_endpoint == "https://api.groq.com/openai/v1"
    assert loaded.voice_cloud_model == "whisper-large-v3-turbo"
    assert loaded.voice_api_key == "gsk_secret_voice"

    # Cleanup test credential
    cfg.voice_api_key = ""
    config_to_dict(cfg)


def test_waveform_pill_window_recording_and_transcribing() -> None:
    import tkinter as tk

    from ravan.ui.theme import create_managed_toplevel, destroy_managed_toplevel

    try:
        top, owned_root = create_managed_toplevel(None)
    except tk.TclError as exc:
        pytest.skip(f"Tkinter display unavailable: {exc}")

    cancelled = False

    def _on_cancel() -> None:
        nonlocal cancelled
        cancelled = True

    from ravan.platform.caret import CaretRect

    pill = WaveformPillWindow(parent=top, theme_mode="dark", on_cancel=_on_cancel)
    try:
        # Exercise real non-zero CaretRect anchoring (width/height fields) and near-top flip
        with patch("ravan.ui.waveform_pill.get_caret_rect", return_value=CaretRect(320, 400, 8, 20)):
            pill.show_recording(language="fa")
            assert pill.visible is True
            assert pill.state == "recording"
            pill.push_rms(0.65)
            pill._tick_anim()
            assert pill.bounds() is not None

        with patch("ravan.ui.waveform_pill.get_caret_rect", return_value=CaretRect(320, 10, 4, 20)):
            pill.show_transcribing(language="en")
            assert pill.visible is True
            assert pill.state == "transcribing"

        # Exercise zero-caret bottom-center fallback
        with patch("ravan.ui.waveform_pill.get_caret_rect", return_value=CaretRect(0, 0, 0, 0)):
            pill.show_recording(language="fa")
            assert pill.bounds() is not None

        # Simulate clicking the cancel chip bounds
        x1, y1, x2, y2 = pill._close_zone()
        ev = tk.Event()
        ev.x = int((x1 + x2) / 2)
        ev.y = int((y1 + y2) / 2)
        pill._on_canvas_click(ev)
        assert cancelled is True

        pill.hide()
        assert pill.visible is False
        assert pill.state == "hidden"
    finally:
        pill.destroy()
        destroy_managed_toplevel(top, owned_root)


def test_phase2_modules_respect_line_ceiling() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    for rel in (
        "ravan/platform/audio.py",
        "ravan/core/model_manager.py",
        "ravan/core/voice.py",
        "ravan/ui/waveform_pill.py",
        "ravan/ui/app_voice.py",
    ):
        line_count = len((repo_root / rel).read_text(encoding="utf-8").splitlines())
        assert line_count <= 425, f"{rel} has {line_count} lines (exceeds Phase 2 modular ceiling)"

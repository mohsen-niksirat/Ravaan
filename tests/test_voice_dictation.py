"""Tests for Phase 9: Voice Dictation Feasibility & Integration (Target I)."""

from __future__ import annotations

from unittest.mock import patch

from ravan.core.config import Config
from ravan.core.voice import VoiceEngine, VoiceState
from ravan.ui.app import RavanApp


class DummyOverlay:
    def __init__(self) -> None:
        self.predicting = False
        self.clipboard_open = False
        self.visible = False
    def hide(self) -> None: pass
    def destroy(self) -> None: pass
    def tick(self) -> None: pass


def test_voice_backend_probe():
    engine = VoiceEngine()
    # Backend should probe without crashing
    assert engine.backend_name in ("faster_whisper", "whisper", "vosk", "builtin_mock")


def test_in_memory_buffer_zero_disk_leak():
    engine = VoiceEngine()
    assert engine.state == VoiceState.IDLE

    # Start recording
    assert engine.start_recording()
    assert engine.state == VoiceState.RECORDING

    # Record dummy audio chunks
    dummy_chunk = b"\x00\x01\x02\x03" * 100
    engine.record_chunk(dummy_chunk)
    assert engine._audio_buffer.tell() == 400

    # Stop recording and transcribe with mock result
    res = engine.stop_recording_and_transcribe(mock_result="سلام خسته نباشید")
    assert res == "سلام خسته نباشید"
    assert engine.state == VoiceState.IDLE
    # Verify buffer is wiped/closed
    assert engine._audio_buffer.getvalue() == b""


def test_transcription_persian_normalization():
    engine = VoiceEngine()
    engine.start_recording()

    # Audio text with unnormalized Arabic characters and space-separated suffix
    raw_text = "كتاب ها و خانه هاي ما"
    normalized = engine.stop_recording_and_transcribe(mock_result=raw_text)

    # Expected: Arabic kaf/yeh normalized, ZWNJ attached to ها and های
    assert "کتاب‌ها" in normalized
    assert "خانه‌های" in normalized


def test_recording_cancellation():
    engine = VoiceEngine()
    engine.start_recording()
    engine.record_chunk(b"some_audio")
    assert engine.state == VoiceState.RECORDING

    engine.cancel()
    assert engine.state == VoiceState.IDLE
    assert engine._audio_buffer.getvalue() == b""


def test_app_voice_toggle_and_paste():
    cfg = Config()
    cfg.voice_dictation_enabled = True

    with patch("ravan.ui.app.KeyboardHook"):
        app = RavanApp(cfg, overlay=DummyOverlay())
        try:
            assert app.voice is not None
            assert app.voice.state == VoiceState.IDLE

            # First toggle -> starts recording
            with patch.object(app.tray, "notify") as mock_notify:
                app._toggle_voice_dictation()
                assert app.voice.state == VoiceState.RECORDING
                assert mock_notify.called

            # Second toggle -> stops recording and transcribes in thread
            with patch.object(app.voice, "stop_recording_and_transcribe", return_value="متن گفتاری"):
                with patch("ravan.ui.app_voice.set_clipboard_text") as mock_set_clip, \
                     patch("ravan.ui.app_voice.send_shortcut") as mock_shortcut:
                    app._toggle_voice_dictation()

                    # Wait briefly for worker thread
                    import time
                    time.sleep(0.1)

                    assert mock_set_clip.called
                    assert mock_set_clip.call_args[0][0] == "متن گفتاری"
                    assert mock_shortcut.called
        finally:
            app.stop()

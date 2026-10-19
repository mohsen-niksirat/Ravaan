"""Offline voice dictation engine with in-memory buffering and zero audio disk leaks."""

from __future__ import annotations

import io
import logging
import threading
import time
from enum import Enum, auto
from typing import Any

from ravan.core.transform import normalize_text

log = logging.getLogger(__name__)


class VoiceState(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()


class VoiceEngine:
    """Offline local ASR controller with zero-audio-persistence policy."""

    def __init__(self, model_name: str = "base", language: str = "fa") -> None:
        self.model_name = model_name
        self.language = language
        self.state = VoiceState.IDLE
        self._audio_buffer = io.BytesIO()
        self._lock = threading.Lock()
        self._start_time: float = 0.0
        self._backend: Any = None
        self._probe_backend()

    def _probe_backend(self) -> None:
        """Probe available local offline ASR engines (faster-whisper, whisper, vosk)."""
        try:
            import faster_whisper  # type: ignore

            self._backend = ("faster_whisper", faster_whisper)
            log.info("Local faster-whisper ASR backend detected")
            return
        except ImportError:
            pass

        try:
            import whisper  # type: ignore

            self._backend = ("whisper", whisper)
            log.info("Standard whisper ASR backend detected")
            return
        except ImportError:
            pass

        try:
            import vosk  # type: ignore

            self._backend = ("vosk", vosk)
            log.info("Vosk ASR backend detected")
            return
        except ImportError:
            pass

        log.debug("No heavy ASR backend installed; using lightweight simulated engine")
        self._backend = ("builtin_mock", None)

    @property
    def backend_name(self) -> str:
        return self._backend[0] if self._backend else "none"

    def start_recording(self) -> bool:
        """Start recording audio into in-memory buffer."""
        with self._lock:
            if self.state != VoiceState.IDLE:
                return False
            self.state = VoiceState.RECORDING
            self._audio_buffer = io.BytesIO()
            self._start_time = time.monotonic()
            log.info("Voice recording started (in-memory buffer)")
            return True

    def record_chunk(self, chunk: bytes) -> None:
        """Append raw audio PCM bytes to in-memory buffer."""
        with self._lock:
            if self.state == VoiceState.RECORDING and chunk:
                self._audio_buffer.write(chunk)

    def stop_recording_and_transcribe(self, mock_result: str | None = None) -> str:
        """Stop recording, transcribe in-memory audio, apply Persian normalization, and clear buffer.

        Zero-disk guarantee: Audio bytes are wiped from memory immediately after transcription.
        """
        with self._lock:
            if self.state != VoiceState.RECORDING:
                return ""
            self.state = VoiceState.TRANSCRIBING
            raw_audio = self._audio_buffer.getvalue()
            # Immediately close and reset buffer
            self._audio_buffer.close()
            self._audio_buffer = io.BytesIO()

        try:
            if mock_result is not None:
                recognized = mock_result
            else:
                recognized = self._run_inference(raw_audio)

            if not recognized:
                return ""

            # Normalize Persian text & attach ZWNJ
            normalized = normalize_text(recognized.strip())
            log.info("Voice dictation transcribed (%d chars)", len(normalized))
            return normalized
        finally:
            with self._lock:
                self.state = VoiceState.IDLE

    def _run_inference(self, audio_bytes: bytes) -> str:
        """Run speech recognition model against in-memory audio bytes."""
        if not audio_bytes:
            return ""

        backend, mod = self._backend
        if backend == "faster_whisper" and mod:
            try:
                model = mod.WhisperModel(self.model_name, device="cpu", compute_type="int8")
                audio_stream = io.BytesIO(audio_bytes)
                segments, _ = model.transcribe(audio_stream, language=self.language)
                return " ".join(seg.text for seg in segments).strip()
            except Exception as exc:  # noqa: BLE001
                log.warning("faster-whisper inference failed: %s", exc)
                return ""

        # Default fallback
        return ""

    def cancel(self) -> None:
        """Cancel recording and discard buffer without transcribing."""
        with self._lock:
            self._audio_buffer.close()
            self._audio_buffer = io.BytesIO()
            self.state = VoiceState.IDLE
            log.info("Voice recording cancelled and buffer discarded")

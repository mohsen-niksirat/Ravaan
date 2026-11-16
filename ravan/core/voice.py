"""Offline + Hybrid Voice Dictation engine (zero audio disk persistence)."""

from __future__ import annotations

import io
import json
import logging
import threading
import time
import urllib.error
import urllib.request
import uuid
import wave
from collections import deque
from enum import Enum, auto
from pathlib import Path
from typing import Any

from ravan.core.crypto import decrypt_secret
from ravan.core.model_manager import ModelManager
from ravan.core.normalizer import normalize_persian
from ravan.core.transform import normalize_text

log = logging.getLogger(__name__)


class VoiceState(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()


def pcm16_to_wav_bytes(pcm_bytes: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    """Wrap raw 16-bit signed LE PCM bytes into an in-memory RIFF/WAV container."""
    if not pcm_bytes:
        return b""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def compute_pcm16_level(pcm_bytes: bytes) -> float:
    """Cross-platform normalized RMS calculation for 16-bit signed LE PCM bytes."""
    import array
    import math
    import sys

    if len(pcm_bytes) < 2:
        return 0.0
    usable = len(pcm_bytes) - (len(pcm_bytes) % 2)
    samples = array.array("h")
    samples.frombytes(pcm_bytes[:usable])
    if sys.byteorder != "little":
        samples.byteswap()
    n = len(samples)
    if n == 0:
        return 0.0
    raw = math.sqrt(sum(s * s for s in samples) / n) / 32768.0
    return 0.0 if raw <= 0.0 else max(0.0, min(1.0, math.pow(raw, 0.55) * 1.35))


def postprocess_dictation(text: str, digit_mode: str = "keep") -> str:
    """Clean recognized speech with Persian normalization, ZWNJ cohesion, and grammar rules."""
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    mode = digit_mode if digit_mode in ("auto", "fa", "en", "keep") else "keep"
    result = normalize_persian(
        cleaned,
        digits=mode,  # type: ignore[arg-type]
        fix_zwnj=True,
        fix_spacing=True,
        fix_punctuation=True,
        fix_grammar=True,
    )
    return normalize_text(result).strip()


def _build_multipart_audio_payload(
    wav_bytes: bytes,
    model: str,
    language: str,
) -> tuple[bytes, str]:
    """Build multipart/form-data payload in memory for OpenAI/Groq Whisper transcription."""
    boundary = f"----RavaanVoiceBoundary{uuid.uuid4().hex}"
    parts: list[bytes] = []

    def _add_field(name: str, value: str) -> None:
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode()
        )

    _add_field("model", model or "whisper-1")
    if language and language != "auto":
        _add_field("language", language)
    _add_field("response_format", "json")

    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="dictation.wav"\r\n'
            f"Content-Type: audio/wav\r\n\r\n"
        ).encode()
    )
    parts.append(wav_bytes)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


class VoiceEngine:
    """Offline + hybrid ASR controller with strict zero-audio-disk-persistence policy."""

    def __init__(
        self,
        model_name: str = "base",
        language: str = "fa",
        mode: str = "offline",
        cloud_endpoint: str = "https://api.openai.com/v1",
        cloud_model: str = "whisper-1",
        api_key_encrypted: str = "",
        digit_mode: str = "keep",
        model_manager: ModelManager | None = None,
    ) -> None:
        self.model_name = model_name
        self.language = language
        self.mode = mode if mode in ("offline", "cloud", "hybrid") else "offline"
        self.cloud_endpoint = (cloud_endpoint or "https://api.openai.com/v1").rstrip("/")
        self.cloud_model = cloud_model or "whisper-1"
        self.api_key_encrypted = api_key_encrypted
        self.digit_mode = digit_mode
        self.model_manager = model_manager or ModelManager()

        self.state = VoiceState.IDLE
        self._audio_buffer = io.BytesIO()
        self._lock = threading.Lock()
        self._start_time: float = 0.0
        self._latest_rms: float = 0.0
        self._rms_history: deque[float] = deque([0.0] * 18, maxlen=18)
        self._last_error: str = ""
        self._backend: Any = None
        self._loaded_fw_model: tuple[str, Any] | None = None
        self._probe_backend()

    def _probe_backend(self) -> None:
        """Probe available local offline ASR engines or Cloud API fallback."""
        for name in ("faster_whisper", "whisper", "vosk"):
            try:
                mod = __import__(name)
                self._backend = (name, mod)
                log.info("Local %s ASR backend detected", name)
                return
            except ImportError:
                pass
        if self.mode in ("cloud", "hybrid") and self._resolve_api_key():
            self._backend = ("cloud_whisper", None)
            return
        log.debug("No heavy local ASR library installed; using lightweight simulated/cloud fallback")
        self._backend = ("builtin_mock", None)

    @property
    def backend_name(self) -> str:
        return self._backend[0] if self._backend else "none"

    @property
    def latest_rms(self) -> float:
        return self._latest_rms

    @property
    def rms_history(self) -> list[float]:
        return list(self._rms_history)

    @property
    def last_error(self) -> str:
        return self._last_error

    @property
    def elapsed_seconds(self) -> float:
        if self.state == VoiceState.IDLE or self._start_time <= 0.0:
            return 0.0
        return max(0.0, time.monotonic() - self._start_time)

    def _resolve_api_key(self) -> str:
        if not self.api_key_encrypted:
            return ""
        try:
            return decrypt_secret(self.api_key_encrypted).strip()
        except Exception:  # noqa: BLE001
            return self.api_key_encrypted.strip()

    def start_recording(self) -> bool:
        """Start recording audio into in-memory buffer."""
        with self._lock:
            if self.state != VoiceState.IDLE:
                return False
            self.state = VoiceState.RECORDING
            self._audio_buffer = io.BytesIO()
            self._start_time = time.monotonic()
            self._latest_rms = 0.0
            self._last_error = ""
            self._rms_history = deque([0.0] * 18, maxlen=18)
            log.info("Voice recording started (in-memory buffer, mode=%s)", self.mode)
            return True

    def record_chunk(self, chunk: bytes, rms: float | None = None) -> None:
        """Append raw audio PCM bytes to in-memory buffer and update real-time level."""
        with self._lock:
            if self.state == VoiceState.RECORDING and chunk:
                self._audio_buffer.write(chunk)
                level = float(rms) if rms is not None else compute_pcm16_level(chunk)
                self._latest_rms = max(0.0, min(1.0, level))
                self._rms_history.append(self._latest_rms)

    def stop_recording_and_transcribe(self, mock_result: str | None = None) -> str:
        """Stop recording, transcribe in-memory audio, normalize Persian, and wipe RAM buffer."""
        with self._lock:
            if self.state != VoiceState.RECORDING:
                return ""
            self.state = VoiceState.TRANSCRIBING
            raw_audio = self._audio_buffer.getvalue()
            self._audio_buffer.close()
            self._audio_buffer = io.BytesIO()
            self._latest_rms = 0.0

        try:
            if mock_result is not None:
                recognized = mock_result
            else:
                recognized = self._run_inference(raw_audio)

            if not recognized:
                return ""

            normalized = postprocess_dictation(recognized, digit_mode=self.digit_mode)
            log.info("Voice dictation transcribed (%d chars)", len(normalized))
            return normalized
        finally:
            raw_audio = b""
            with self._lock:
                self.state = VoiceState.IDLE

    def _run_local_asr(self, pcm_bytes: bytes) -> str:
        """Run local ASR strictly in-memory without writing temp .wav files."""
        backend, mod = self._backend
        wav_bytes = pcm16_to_wav_bytes(pcm_bytes) if not pcm_bytes.startswith(b"RIFF") else pcm_bytes
        lang_arg = None if self.language == "auto" else self.language
        size_hint = self.model_name.replace("whisper-", "")

        if backend == "faster_whisper" and mod is not None:
            try:
                if self._loaded_fw_model is None or self._loaded_fw_model[0] != size_hint:
                    fw_model = mod.WhisperModel(size_hint, device="cpu", compute_type="int8")
                    self._loaded_fw_model = (size_hint, fw_model)
                _, fw_model = self._loaded_fw_model
                segments, _ = fw_model.transcribe(io.BytesIO(wav_bytes), language=lang_arg)
                return " ".join(seg.text for seg in segments).strip()
            except Exception as exc:  # noqa: BLE001
                self._last_error = f"faster-whisper failed: {exc}"
                log.warning("faster-whisper inference failed: %s", exc)
                return ""

        if backend == "whisper" and mod is not None:
            try:
                import numpy as np  # type: ignore

                samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                w_model = mod.load_model(size_hint)
                res = w_model.transcribe(samples, language=lang_arg)
                return str(res.get("text", "")).strip()
            except Exception as exc:  # noqa: BLE001
                self._last_error = f"whisper failed: {exc}"
                log.warning("openai-whisper inference failed: %s", exc)
                return ""

        if backend == "vosk" and mod is not None:
            try:
                model_dir: Path | None = self.model_manager.base_dir / "vosk-fa"
                if not model_dir.is_dir():
                    return ""
                v_model = mod.Model(str(model_dir))
                rec = mod.KaldiRecognizer(v_model, 16000)
                rec.AcceptWaveform(pcm_bytes)
                final = json.loads(rec.FinalResult())
                return str(final.get("text", "")).strip()
            except Exception as exc:  # noqa: BLE001
                self._last_error = f"vosk failed: {exc}"
                log.warning("vosk inference failed: %s", exc)
                return ""

        return ""

    def _run_cloud_asr(self, pcm_bytes: bytes, timeout: float = 30.0) -> str:
        """Send in-memory WAV audio to OpenAI/Groq compatible /audio/transcriptions."""
        api_key = self._resolve_api_key()
        if not api_key:
            self._last_error = "Cloud Whisper API key is missing"
            return ""
        wav_bytes = pcm16_to_wav_bytes(pcm_bytes) if not pcm_bytes.startswith(b"RIFF") else pcm_bytes
        body, content_type = _build_multipart_audio_payload(
            wav_bytes=wav_bytes,
            model=self.cloud_model,
            language=self.language,
        )
        url = f"{self.cloud_endpoint}/audio/transcriptions"
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": content_type,
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return str(data.get("text", "")).strip()
        except urllib.error.HTTPError as exc:
            self._last_error = f"Cloud ASR HTTP {exc.code}"
            log.warning("Cloud ASR HTTP error: %s", exc)
            return ""
        except urllib.error.URLError as exc:
            self._last_error = f"Cloud ASR unavailable: {exc.reason}"
            log.warning("Cloud ASR network error: %s", exc)
            return ""

    def _run_inference(self, audio_bytes: bytes) -> str:
        """Dispatch offline, cloud, or hybrid inference against RAM audio bytes."""
        if not audio_bytes:
            return ""

        if self.mode == "cloud":
            return self._run_cloud_asr(audio_bytes)

        text = self._run_local_asr(audio_bytes)
        if text:
            return text

        if self.mode == "hybrid" and self._resolve_api_key():
            return self._run_cloud_asr(audio_bytes)

        return ""

    def cancel(self) -> None:
        """Cancel recording and immediately discard RAM audio buffer."""
        with self._lock:
            self._audio_buffer.close()
            self._audio_buffer = io.BytesIO()
            self.state = VoiceState.IDLE
            self._latest_rms = 0.0
            self._rms_history = deque([0.0] * 18, maxlen=18)
            log.info("Voice recording cancelled and buffer discarded")

"""Voice Dictation (Voice 2.0 Push-to-Talk & Real Mic Capture) mixin for RavanApp."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from ravan.core.i18n import t
from ravan.core.voice import VoiceEngine, VoiceState
from ravan.platform import winapi as w
from ravan.platform.audio import MicrophoneCapture
from ravan.platform.clipboard import set_clipboard_text
from ravan.platform.inject import send_shortcut
from ravan.ui.waveform_pill import WaveformPillWindow

log = logging.getLogger(__name__)


class AppVoiceMixin:
    """Mixin managing live WinMM microphone capture, Waveform pill UI, and text injection."""

    def _build_voice_engine(self: Any) -> VoiceEngine:
        return VoiceEngine(
            model_name=str(getattr(self.cfg, "voice_model_id", "whisper-base") or "whisper-base"),
            language=str(getattr(self.cfg, "voice_language", "fa") or "fa"),
            mode=str(getattr(self.cfg, "voice_mode", "offline") or "offline"),
            cloud_endpoint=str(
                getattr(self.cfg, "voice_cloud_endpoint", "https://api.openai.com/v1")
                or "https://api.openai.com/v1"
            ),
            cloud_model=str(getattr(self.cfg, "voice_cloud_model", "whisper-1") or "whisper-1"),
            api_key_encrypted=str(getattr(self.cfg, "voice_api_key", "") or ""),
            digit_mode=str(getattr(self.cfg, "digit_mode", "keep") or "keep"),
        )

    def _init_voice(self: Any) -> None:
        self._mic: MicrophoneCapture | None = None
        self.voice_pill: WaveformPillWindow | None = None
        if getattr(self.cfg, "voice_dictation_enabled", False):
            self.voice = self._build_voice_engine()
        else:
            self.voice = None

    def _ensure_voice_pill(self: Any) -> WaveformPillWindow | None:
        if getattr(self, "voice_pill", None) is None:
            parent = getattr(getattr(self, "overlay", None), "_root", None)
            if not getattr(self, "_running", False) and parent is None:
                return None
            self.voice_pill = WaveformPillWindow(
                parent=parent,
                theme_mode=str(getattr(self.cfg, "theme_mode", "auto")),
                on_cancel=self._cancel_voice_dictation,
            )
        else:
            self.voice_pill.theme_mode = str(getattr(self.cfg, "theme_mode", "auto"))
        return self.voice_pill

    def _dispatch_voice_pill(self: Any, action: str, arg: Any = None) -> None:
        if getattr(self, "_running", False) and hasattr(self, "_ui_queue"):
            self._ui_queue.put((action, arg))
            return
        self._apply_voice_pill_action(action, arg)

    def _apply_voice_pill_action(self: Any, action: str, arg: Any = None) -> None:
        pill = self._ensure_voice_pill() if action != "voice_pill_hide" else getattr(self, "voice_pill", None)
        if pill is None:
            return
        if action == "voice_pill_recording":
            voice = getattr(self, "voice", None)
            pill.show_recording(
                language=str(arg or getattr(self.cfg, "voice_language", "fa")),
                rms_provider=(lambda: float(voice.latest_rms)) if voice is not None else None,
                elapsed_provider=(lambda: float(voice.elapsed_seconds)) if voice is not None else None,
            )
        elif action == "voice_pill_transcribing":
            pill.show_transcribing(language=str(arg or getattr(self.cfg, "voice_language", "fa")))
        elif action == "voice_pill_hide":
            pill.hide()

    def _on_voice_mic_chunk(self: Any, chunk: bytes, rms: float) -> None:
        voice = getattr(self, "voice", None)
        if voice is not None and voice.state == VoiceState.RECORDING:
            voice.record_chunk(chunk, rms=rms)

    def _cancel_voice_dictation(self: Any) -> None:
        """Abort active voice recording or discard pending capture immediately."""
        mic = getattr(self, "_mic", None)
        if mic is not None:
            try:
                mic.stop()
            except Exception:  # noqa: BLE001
                pass
        voice = getattr(self, "voice", None)
        if voice is not None:
            voice.cancel()
        self._dispatch_voice_pill("voice_pill_hide")
        if hasattr(self, "_show_toast"):
            self._show_toast(t("voice.cancelled", "Voice dictation cancelled."))

    def _toggle_voice_dictation(self: Any) -> None:
        """Toggle Push-to-Talk voice dictation on or off."""
        if not getattr(self.cfg, "voice_dictation_enabled", False):
            self.tray.notify(
                t(
                    "voice.disabled_hint",
                    "Voice Dictation is disabled. Enable it in Ravan Settings.",
                ),
                title="Ravaan Voice",
            )
            return

        if getattr(self, "voice", None) is None:
            self.voice = self._build_voice_engine()
        assert self.voice is not None

        if self.voice.state == VoiceState.IDLE:
            # Refresh settings on engine before starting a new session
            self.voice.model_name = str(getattr(self.cfg, "voice_model_id", "whisper-base") or "whisper-base")
            self.voice.language = str(getattr(self.cfg, "voice_language", "fa") or "fa")
            self.voice.mode = str(getattr(self.cfg, "voice_mode", "offline") or "offline")
            self.voice.cloud_endpoint = str(
                getattr(self.cfg, "voice_cloud_endpoint", "https://api.openai.com/v1")
                or "https://api.openai.com/v1"
            ).rstrip("/")
            self.voice.cloud_model = str(getattr(self.cfg, "voice_cloud_model", "whisper-1") or "whisper-1")
            self.voice.api_key_encrypted = str(getattr(self.cfg, "voice_api_key", "") or "")
            self.voice.digit_mode = str(getattr(self.cfg, "digit_mode", "keep") or "keep")

            if self.voice.start_recording():
                device_id = int(getattr(self.cfg, "voice_device_id", -1))
                self._mic = MicrophoneCapture(
                    device_id=device_id,
                    on_chunk=self._on_voice_mic_chunk,
                )
                mic_started = self._mic.start()
                if not mic_started and self._mic.last_error:
                    log.info("Microphone stream inactive (%s); keeping VoiceEngine armed", self._mic.last_error)

                self.tray.notify(
                    t("voice.listening", "Listening... Press hotkey again to transcribe or Esc to cancel."),
                    title="Ravaan Voice",
                )
                self._dispatch_voice_pill("voice_pill_recording", self.voice.language)
                if hasattr(self, "_show_toast"):
                    self._show_toast(t("voice.listening_short", "Listening for speech..."))

        elif self.voice.state == VoiceState.RECORDING:
            mic = getattr(self, "_mic", None)
            if mic is not None:
                try:
                    mic.stop()
                except Exception:  # noqa: BLE001
                    pass

            self._dispatch_voice_pill("voice_pill_transcribing", self.voice.language)
            if hasattr(self, "_show_toast"):
                self._show_toast(t("voice.transcribing", "Transcribing speech..."))

            def _bg_transcribe() -> None:
                assert self.voice is not None
                try:
                    text = self.voice.stop_recording_and_transcribe()
                finally:
                    self._dispatch_voice_pill("voice_pill_hide")

                if text:
                    self._suppress_until = time.monotonic() + 0.1
                    set_clipboard_text(text)
                    time.sleep(0.02)
                    send_shortcut([w.VK_CONTROL], ord("V"))
                    for ch in text:
                        self.journal.push(ch)
                    if hasattr(self, "_show_toast"):
                        self._show_toast(
                            t("voice.inserted", "Inserted: {preview}...", preview=text[:24])
                        )
                else:
                    msg = (
                        self.voice.last_error
                        or t("voice.no_text", "No speech detected.")
                    )
                    if hasattr(self, "_show_toast"):
                        self._show_toast(msg)

            threading.Thread(target=_bg_transcribe, daemon=True).start()

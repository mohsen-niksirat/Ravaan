"""Voice Dictation (Push-to-Talk) mixin for RavanApp."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from ravan.core.voice import VoiceEngine, VoiceState
from ravan.platform import winapi as w
from ravan.platform.clipboard import set_clipboard_text
from ravan.platform.inject import send_shortcut

log = logging.getLogger(__name__)


class AppVoiceMixin:
    """Mixin managing voice dictation recording state and direct text injection."""

    def _init_voice(self: Any) -> None:
        if getattr(self.cfg, "voice_dictation_enabled", False):
            self.voice = VoiceEngine()
        else:
            self.voice = None

    def _toggle_voice_dictation(self: Any) -> None:
        """Toggle Push-to-Talk voice dictation on or off."""
        if not getattr(self.cfg, "voice_dictation_enabled", False):
            from ravan.core.i18n import t

            self.tray.notify(
                t(
                    "voice.disabled_hint",
                    "Voice Dictation is disabled. Enable it in Ravan Settings.",
                ),
                title="Ravaan Voice",
            )
            return

        if not hasattr(self, "voice") or self.voice is None:
            self.voice = VoiceEngine()

        if self.voice.state == VoiceState.IDLE:
            if self.voice.start_recording():
                self.tray.notify(
                    "🔴 در حال ضبط صوتی... دوباره میانبر را بزنید تا تبدیل شود.",
                    title="Ravaan تایپ صوتی",
                )
                if hasattr(self, "_show_toast"):
                    self._show_toast("🔴 در حال ضبط صوتی...")
        elif self.voice.state == VoiceState.RECORDING:
            if hasattr(self, "_show_toast"):
                self._show_toast("⏳ در حال تبدیل گفتار به متن...")

            def _bg_transcribe() -> None:
                assert self.voice is not None
                text = self.voice.stop_recording_and_transcribe()
                if text:
                    self._suppress_until = time.monotonic() + 0.1
                    # Paste recognized text into target window
                    set_clipboard_text(text)
                    time.sleep(0.02)
                    send_shortcut([w.VK_CONTROL], ord("V"))
                    for ch in text:
                        self.journal.push(ch)
                    if hasattr(self, "_show_toast"):
                        self._show_toast(f"✍ درج شد: {text[:24]}...")
                else:
                    if hasattr(self, "_show_toast"):
                        self._show_toast("صدایی تشخیص داده نشد.")

            threading.Thread(target=_bg_transcribe, daemon=True).start()

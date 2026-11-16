"""AI Text Assistant mixin for RavanApp."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Iterator
from typing import Any

from ravan.core.ai import (
    AI_PROVIDER_PRESETS,
    AIAssistantEngine,
    OllamaProvider,
    OpenAICompatibleProvider,
)
from ravan.platform import winapi as w
from ravan.platform.caret import get_caret_rect
from ravan.platform.clipboard import get_clipboard_text, set_clipboard_text
from ravan.platform.inject import replace_last_n_with, send_shortcut

log = logging.getLogger(__name__)


class AppAIMixin:
    """Mixin providing AI assistant hotkey invocation, streaming popup, and injection."""

    def _init_ai(self: Any) -> None:
        if not getattr(self.cfg, "ai_assistant_enabled", False):
            self.ai_engine = None
            self.ai_popup = None
            return

        provider_name = str(getattr(self.cfg, "ai_provider", "ollama") or "ollama").strip().lower()
        preset = AI_PROVIDER_PRESETS.get(provider_name, AI_PROVIDER_PRESETS["ollama"])
        endpoint = str(getattr(self.cfg, "ai_endpoint_url", "") or preset.endpoint_url).strip()
        model = str(getattr(self.cfg, "ai_model", "") or preset.default_model).strip()

        if provider_name == "ollama":
            provider = OllamaProvider(endpoint_url=endpoint, model=model)
        else:
            provider = OpenAICompatibleProvider(
                endpoint_url=endpoint,
                api_key_encrypted=getattr(self.cfg, "ai_api_key", ""),
                model=model,
            )

        self.ai_engine = AIAssistantEngine(provider=provider)
        self.ai_popup = None

    def _trigger_ai_assistant(self: Any) -> None:
        """Trigger AI Assistant on current selected text or recent journal input."""
        from ravan.core.i18n import t

        if not getattr(self.cfg, "ai_assistant_enabled", False):
            self.tray.notify(
                t("ai.disabled_hint", "AI Assistant is disabled. Enable it in Ravan Settings."),
                title="Ravaan AI",
            )
            return

        if not hasattr(self, "ai_engine") or self.ai_engine is None:
            self._init_ai()

        old_clip = get_clipboard_text()
        self._suppress_until = time.monotonic() + 0.15
        send_shortcut([w.VK_CONTROL], ord("C"))
        time.sleep(0.06)

        new_clip = get_clipboard_text()
        if old_clip is not None:
            set_clipboard_text(old_clip)

        target_text = ""
        has_selection = False
        if new_clip and new_clip.strip() and new_clip != old_clip:
            target_text = new_clip
            has_selection = True
        else:
            target_text = self.journal.text().strip()

        if not target_text:
            self.tray.notify(
                t("ai.select_text_hint", "Please select text to rewrite, fix, or translate with AI."),
                title="Ravaan AI",
            )
            return

        from ravan.ui.ai_popup import AIAssistantPopup

        def _on_replace(replacement: str) -> None:
            self._suppress_until = time.monotonic() + 0.1
            if has_selection:
                set_clipboard_text(replacement)
                time.sleep(0.02)
                send_shortcut([w.VK_CONTROL], ord("V"))
            else:
                span_len = len(target_text)
                replace_last_n_with(span_len, replacement)
                self.journal.pop_last_n_chars(span_len)
                for ch in replacement:
                    self.journal.push(ch)

        def _on_copy(res: str) -> None:
            set_clipboard_text(res)
            self.tray.notify(
                t("ai.copied_notice", "پاسخ هوش مصنوعی در کلیپ‌بورد کپی شد."),
                title="Ravaan AI",
            )

        def _process(action: str, text: str, custom_inst: str) -> str:
            assert self.ai_engine is not None
            return self.ai_engine.process(action, text, custom_instruction=custom_inst)

        def _process_stream(
            action: str, text: str, custom_inst: str, cancel_event: threading.Event | None
        ) -> Iterator[str]:
            assert self.ai_engine is not None
            return self.ai_engine.process_stream(
                action, text, custom_instruction=custom_inst, cancel_event=cancel_event
            )

        caret = get_caret_rect()
        popup = AIAssistantPopup(
            parent=getattr(self.overlay, "_root", None),
            on_replace=_on_replace,
            on_copy=_on_copy,
            process_callback=_process,
            theme_mode=getattr(self.cfg, "theme_mode", "auto"),
            stream_callback=_process_stream,
        )
        self.ai_popup = popup
        px = caret.x if caret else 400
        py = caret.y if caret else 300
        popup.show(target_text, px, py)

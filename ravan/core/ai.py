"""AI Text Assistant engine supporting Local Ollama and OpenAI-compatible providers."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from abc import ABC, abstractmethod

from ravan.core.crypto import decrypt_secret, encrypt_secret

log = logging.getLogger(__name__)

PROMPTS = {
    "rewrite": (
        "متن زیر را به صورت روان، شیوا و طبیعی به زبان فارسی بازنویسی کن. "
        "تنها متن بازنویسی شده را برگردان بدون هیچ‌گونه توضیح یا مقدمه اضافه:\n\n{text}"
    ),
    "fix_grammar": (
        "رسم‌الخط، دستور زبان، نقطه‌گذاری و نیم‌فاصله‌های متن زیر را تصحیح کن. "
        "تنها نسخه اصلاح‌شده را برگردان:\n\n{text}"
    ),
    "translate": (
        "Translate the following text between Persian and English. "
        "If the input is Persian, translate to English. "
        "If the input is English, translate to Persian. "
        "Provide only the translation without commentary:\n\n{text}"
    ),
    "summarize": (
        "متن زیر را به شکل خلاصه و موجز در چند جمله یا نکته کلیدی جمع‌بندی کن:\n\n{text}"
    ),
}


class AIProvider(ABC):
    """Abstract provider interface for LLM text generation."""

    @abstractmethod
    def generate(self, prompt: str, timeout: float = 30.0) -> str:
        raise NotImplementedError


class OllamaProvider(AIProvider):
    """Local-first offline LLM inference via Ollama (http://localhost:11434)."""

    def __init__(
        self,
        endpoint_url: str = "http://localhost:11434",
        model: str = "qwen2.5:7b",
    ) -> None:
        self.endpoint_url = endpoint_url.rstrip("/")
        self.model = model or "qwen2.5:7b"

    def generate(self, prompt: str, timeout: float = 30.0) -> str:
        url = f"{self.endpoint_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return str(result.get("response", "")).strip()
        except urllib.error.URLError as exc:
            log.warning("Ollama connection failed: %s", exc)
            raise ConnectionError(f"Ollama server unavailable at {self.endpoint_url}") from exc


class OpenAICompatibleProvider(AIProvider):
    """BYO-Key cloud/local OpenAI-compatible LLM endpoint."""

    def __init__(
        self,
        endpoint_url: str = "https://api.openai.com/v1",
        api_key_encrypted: str = "",
        model: str = "gpt-4o-mini",
    ) -> None:
        self.endpoint_url = endpoint_url.rstrip("/")
        self.api_key_encrypted = api_key_encrypted
        self.model = model or "gpt-4o-mini"

    def get_api_key(self) -> str:
        if not self.api_key_encrypted:
            return ""
        try:
            return decrypt_secret(self.api_key_encrypted)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to decrypt API key: %s", exc)
            return ""

    def set_api_key(self, plain_key: str) -> None:
        if plain_key:
            self.api_key_encrypted = encrypt_secret(plain_key)
        else:
            self.api_key_encrypted = ""

    def generate(self, prompt: str, timeout: float = 30.0) -> str:
        api_key = self.get_api_key()
        if not api_key:
            raise ValueError("API Key is missing or invalid")

        url = f"{self.endpoint_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise, privacy-conscious Persian and English writing assistant.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    return str(choices[0].get("message", {}).get("content", "")).strip()
                return ""
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:200]
            log.warning("OpenAI API error HTTP %d: %s", exc.code, body)
            raise RuntimeError(f"AI API request failed: HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            log.warning("OpenAI endpoint connection failed: %s", exc)
            raise ConnectionError(f"Could not connect to {self.endpoint_url}") from exc


class AIAssistantEngine:
    """Orchestrates AI text processing tasks with zero user-text logging."""

    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    def build_prompt(self, action: str, text: str, custom_instruction: str = "") -> str:
        if action == "custom":
            return f"{custom_instruction}\n\nمتن ورودی:\n{text}"
        template = PROMPTS.get(action, PROMPTS["rewrite"])
        return template.format(text=text)

    def process(
        self,
        action: str,
        text: str,
        custom_instruction: str = "",
        timeout: float = 30.0,
    ) -> str:
        """Execute selected AI action on input text.

        Zero-log guarantee: Neither the input text nor the response is logged.
        """
        clean_text = text.strip()
        if not clean_text:
            return ""

        prompt = self.build_prompt(action, clean_text, custom_instruction)
        # Log action name only — NEVER log user text or prompt
        log.info("Executing AI action: %s", action)
        return self.provider.generate(prompt, timeout=timeout)

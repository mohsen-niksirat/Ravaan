"""AI Text Assistant engine with streaming SSE/NDJSON and zero-log privacy guarantee."""

from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass

from ravan.core.crypto import decrypt_secret, encrypt_secret

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AIProviderPreset:
    """Built-in configuration defaults for supported local & cloud LLM providers."""

    provider_id: str
    label_en: str
    label_fa: str
    endpoint_url: str
    default_model: str
    requires_api_key: bool = True


AI_PROVIDER_PRESETS: dict[str, AIProviderPreset] = {
    "ollama": AIProviderPreset(
        provider_id="ollama",
        label_en="Ollama (Local)",
        label_fa="Ollama (محلی و آفلاین)",
        endpoint_url="http://localhost:11434",
        default_model="qwen2.5:7b",
        requires_api_key=False,
    ),
    "openai": AIProviderPreset(
        provider_id="openai",
        label_en="OpenAI",
        label_fa="OpenAI",
        endpoint_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    ),
    "gemini": AIProviderPreset(
        provider_id="gemini",
        label_en="Gemini (OpenAI-Compat)",
        label_fa="Gemini (سازگار با OpenAI)",
        endpoint_url="https://generativelanguage.googleapis.com/v1beta/openai",
        default_model="gemini-2.5-flash",
    ),
    "groq": AIProviderPreset(
        provider_id="groq",
        label_en="Groq",
        label_fa="Groq (سرعت بالا)",
        endpoint_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
    ),
    "openrouter": AIProviderPreset(
        provider_id="openrouter",
        label_en="OpenRouter",
        label_fa="OpenRouter",
        endpoint_url="https://openrouter.ai/api/v1",
        default_model="openai/gpt-4o-mini",
    ),
    "custom": AIProviderPreset(
        provider_id="custom",
        label_en="Custom Endpoint",
        label_fa="آدرس سفارشی",
        endpoint_url="http://localhost:8000/v1",
        default_model="default",
    ),
}

AI_PRESET_SPECS: tuple[tuple[str, str, str], ...] = (
    ("rewrite", "بازنویسی روان", "Rewrite"),
    ("formal_fa", "رسمی اداری", "Formal FA"),
    ("pro_en", "ایمیل حرفه‌ای", "Pro Email"),
    ("fix_grammar", "رسم‌الخط و نیم‌فاصله", "Fix Grammar"),
    ("pinglish_to_fa", "فینگلیش به فارسی", "Pinglish → FA"),
    ("translate", "ترجمه دوطرفه", "Translate"),
    ("summarize", "خلاصه‌سازی", "Summarize"),
)

PROMPTS: dict[str, str] = {
    "rewrite": (
        "متن زیر را به صورت روان، شیوا و طبیعی به زبان فارسی بازنویسی کن. "
        "تنها متن بازنویسی شده را برگردان بدون هیچ‌گونه توضیح یا مقدمه اضافه:\n\n{text}"
    ),
    "formal_fa": (
        "متن زیر را به زبان فارسی رسمی، اداری و محترمانه با رعایت نیم‌فاصله و علائم نگارشی بازنویسی کن. "
        "تنها متن نهایی را بدون توضیح اضافه برگردان:\n\n{text}"
    ),
    "pro_en": (
        "Rewrite the following text into clear, polished, professional English suitable for business "
        "communication or email. Preserve intent and return only the rewritten text:\n\n{text}"
    ),
    "fix_grammar": (
        "رسم‌الخط، دستور زبان، نقطه‌گذاری و نیم‌فاصله‌های متن زیر را تصحیح کن. "
        "تنها نسخه اصلاح‌شده را برگردان:\n\n{text}"
    ),
    "pinglish_to_fa": (
        "متن فینگلیش یا محاوره‌ای زیر را به فارسی روان، استاندارد و خوش‌خوان با نیم‌فاصله‌های صحیح تبدیل کن. "
        "تنها متن فارسی نهایی را برگردان:\n\n{text}"
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
    "complete": (
        "ادامه طبیعی جمله زیر را تنها در ۳ تا ۷ کلمه به همان زبان بنویس (بدون تکرار متن ورودی و بدون توضیح):\n\n{text}"
    ),
    "quick_reply": (
        "یک پاسخ مؤدبانه، حرفه‌ای و کوتاه به پیام زیر بنویس. تنها متن پاسخ را برگردان:\n\n{text}"
    ),
}


class AIProvider(ABC):
    """Abstract provider interface for LLM text generation."""

    @abstractmethod
    def generate(self, prompt: str, timeout: float = 30.0) -> str:
        raise NotImplementedError

    def generate_stream(
        self,
        prompt: str,
        timeout: float = 30.0,
        cancel_event: threading.Event | None = None,
    ) -> Iterator[str]:
        """Yield generated text chunks progressively; falls back to `generate`."""
        if cancel_event is not None and cancel_event.is_set():
            return
        result = self.generate(prompt, timeout=timeout)
        if cancel_event is not None and cancel_event.is_set():
            return
        if result:
            yield result


class OllamaProvider(AIProvider):
    """Local-first offline LLM inference via Ollama (http://localhost:11434)."""

    def __init__(
        self,
        endpoint_url: str = "http://localhost:11434",
        model: str = "qwen2.5:7b",
    ) -> None:
        self.endpoint_url = (endpoint_url or "http://localhost:11434").rstrip("/")
        self.model = model or "qwen2.5:7b"

    def _build_request(self, prompt: str, *, stream: bool) -> urllib.request.Request:
        url = f"{self.endpoint_url}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "stream": stream}
        return urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

    def generate(self, prompt: str, timeout: float = 30.0) -> str:
        req = self._build_request(prompt, stream=False)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return str(result.get("response", "")).strip()
        except urllib.error.URLError as exc:
            log.warning("Ollama connection failed: %s", exc)
            raise ConnectionError(f"Ollama server unavailable at {self.endpoint_url}") from exc

    def generate_stream(
        self,
        prompt: str,
        timeout: float = 30.0,
        cancel_event: threading.Event | None = None,
    ) -> Iterator[str]:
        req = self._build_request(prompt, stream=True)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                for raw_line in resp:
                    if cancel_event is not None and cancel_event.is_set():
                        break
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = str(chunk.get("response", ""))
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
        except urllib.error.URLError as exc:
            log.warning("Ollama stream connection failed: %s", exc)
            raise ConnectionError(f"Ollama server unavailable at {self.endpoint_url}") from exc


class OpenAICompatibleProvider(AIProvider):
    """BYO-Key cloud/local OpenAI-compatible LLM endpoint with SSE streaming."""

    def __init__(
        self,
        endpoint_url: str = "https://api.openai.com/v1",
        api_key_encrypted: str = "",
        model: str = "gpt-4o-mini",
    ) -> None:
        self.endpoint_url = (endpoint_url or "https://api.openai.com/v1").rstrip("/")
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
        self.api_key_encrypted = encrypt_secret(plain_key) if plain_key else ""

    def _build_chat_request(self, prompt: str, *, stream: bool) -> urllib.request.Request:
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
            "stream": stream,
        }
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        if stream:
            headers["Accept"] = "text/event-stream"
        return urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )

    def generate(self, prompt: str, timeout: float = 30.0) -> str:
        req = self._build_chat_request(prompt, stream=False)
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

    def generate_stream(
        self,
        prompt: str,
        timeout: float = 30.0,
        cancel_event: threading.Event | None = None,
    ) -> Iterator[str]:
        req = self._build_chat_request(prompt, stream=True)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                for raw_line in resp:
                    if cancel_event is not None and cancel_event.is_set():
                        break
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content") if isinstance(delta, dict) else None
                    if content is None:
                        msg = choices[0].get("message", {})
                        content = msg.get("content") if isinstance(msg, dict) else None
                    if content:
                        yield str(content)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:200]
            log.warning("OpenAI stream HTTP %d: %s", exc.code, body)
            raise RuntimeError(f"AI API request failed: HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            log.warning("OpenAI stream connection failed: %s", exc)
            raise ConnectionError(f"Could not connect to {self.endpoint_url}") from exc


def list_ollama_models(endpoint_url: str = "http://localhost:11434", timeout: float = 3.0) -> list[str]:
    """Query local Ollama `/api/tags` endpoint and return installed model names."""
    base = (endpoint_url or "http://localhost:11434").rstrip("/")
    req = urllib.request.Request(f"{base}/api/tags", method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    models = data.get("models", [])
    return [str(m.get("name", "")).strip() for m in models if isinstance(m, dict) and m.get("name")]


def probe_provider_connection(
    provider_id: str,
    endpoint_url: str,
    api_key: str = "",
    timeout: float = 5.0,
) -> tuple[bool, str]:
    """Verify reachability and auth of an AI provider without logging credentials."""
    pid = (provider_id or "ollama").strip().lower()
    base = (endpoint_url or AI_PROVIDER_PRESETS.get(pid, AI_PROVIDER_PRESETS["ollama"]).endpoint_url).rstrip("/")
    try:
        if pid == "ollama":
            models = list_ollama_models(base, timeout=timeout)
            if models:
                return True, f"Ollama OK ({len(models)} models: {', '.join(models[:3])})"
            return True, "Ollama connected (no local models pulled yet)"
        if not api_key:
            return False, "Missing API key"
        req = urllib.request.Request(
            f"{base}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if 200 <= getattr(resp, "status", 200) < 300:
                return True, f"Connected ({pid})"
            return False, f"HTTP {getattr(resp, 'status', '?')}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:90]


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
        """Execute selected AI action synchronously with zero user-text logging."""
        clean_text = text.strip()
        if not clean_text:
            return ""
        prompt = self.build_prompt(action, clean_text, custom_instruction)
        log.info("Executing AI action: %s", action)
        return self.provider.generate(prompt, timeout=timeout)

    def process_stream(
        self,
        action: str,
        text: str,
        custom_instruction: str = "",
        timeout: float = 30.0,
        cancel_event: threading.Event | None = None,
    ) -> Iterator[str]:
        """Stream AI output chunks with zero user-text logging."""
        clean_text = text.strip()
        if not clean_text:
            return
        prompt = self.build_prompt(action, clean_text, custom_instruction)
        log.info("Streaming AI action: %s", action)
        yield from self.provider.generate_stream(prompt, timeout=timeout, cancel_event=cancel_event)

"""Opt-in Online & Hybrid Prediction Helpers: Google Input Tools API + AI Inline Sentence Completion."""

from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from typing import Any

from ravan.core.events import Candidate, CandidateKind
from ravan.core.normalizer import normalize_persian
from ravan.core.translit import TranslitEngine

log = logging.getLogger(__name__)

GOOGLE_INPUT_ENDPOINT = "https://inputtools.google.com/request"
_CACHE_LOCK = threading.Lock()
_GOOGLE_CACHE: OrderedDict[tuple[str, str, int], list[str]] = OrderedDict()
_AI_CONT_CACHE: OrderedDict[str, str] = OrderedDict()
_MAX_CACHE_SIZE = 256


def clear_online_caches() -> None:
    """Clear in-memory LRU caches for Google Input Tools and AI sentence continuations."""
    with _CACHE_LOCK:
        _GOOGLE_CACHE.clear()
        _AI_CONT_CACHE.clear()


def fetch_google_input_suggestions(
    text: str,
    *,
    itc: str = "fa-t-i0-und",
    num: int = 5,
    timeout: float = 1.5,
) -> list[str]:
    """Query Google Input Tools endpoint for phonetic transliteration / word suggestions.

    Returns normalized Persian suggestions, or `[]` immediately on any network/parse error
    so offline typing is never blocked.
    """
    query = (text or "").strip()
    if not query or len(query) < 2:
        return []

    cache_key = (query.lower(), itc, int(num))
    with _CACHE_LOCK:
        if cache_key in _GOOGLE_CACHE:
            _GOOGLE_CACHE.move_to_end(cache_key)
            return list(_GOOGLE_CACHE[cache_key])

    params = urllib.parse.urlencode(
        {
            "text": query,
            "itc": itc,
            "num": max(1, min(10, int(num))),
            "cp": 0,
            "cs": 1,
            "ie": "utf-8",
            "oe": "utf-8",
            "app": "ravaan",
        }
    )
    url = f"{GOOGLE_INPUT_ENDPOINT}?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Ravaan/3.1",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        log.debug("Google Input Tools request skipped/fell back offline: %s", exc)
        return []

    # Expected structure: ["SUCCESS", [[query, [cand1, cand2, ...], ...]]]
    if not isinstance(payload, list) or len(payload) < 2 or payload[0] != "SUCCESS":
        return []
    blocks = payload[1]
    if not isinstance(blocks, list) or not blocks:
        return []
    first_block = blocks[0]
    if not isinstance(first_block, list) or len(first_block) < 2 or not isinstance(first_block[1], list):
        return []

    results: list[str] = []
    for raw_cand in first_block[1]:
        if isinstance(raw_cand, str) and raw_cand.strip():
            norm = normalize_persian(raw_cand.strip(), digits="keep", fix_zwnj=True, fix_spacing=True)
            if norm and norm not in results:
                results.append(norm)

    if results:
        with _CACHE_LOCK:
            _GOOGLE_CACHE[cache_key] = results
            if len(_GOOGLE_CACHE) > _MAX_CACHE_SIZE:
                _GOOGLE_CACHE.popitem(last=False)
    return results


def hybrid_transliterate(
    text: str,
    *,
    use_google: bool = True,
    offline_engine: TranslitEngine | None = None,
    limit: int = 5,
    timeout: float = 1.5,
) -> list[str]:
    """Return merged Finglish-to-Persian candidates from Google Input Tools + offline TranslitEngine."""
    query = (text or "").strip()
    if not query:
        return []

    eng = offline_engine or TranslitEngine()
    merged: list[str] = []

    if use_google:
        for g_cand in fetch_google_input_suggestions(query, num=limit, timeout=timeout):
            if g_cand not in merged:
                merged.append(g_cand)

    # Always include offline candidates for zero-lag reliability
    if " " in query:
        off_phrase = eng.transliterate_text(query)
        if off_phrase and off_phrase != query and off_phrase not in merged:
            merged.append(off_phrase)
    else:
        for off_cand in eng.transliterate_word(query)[:limit]:
            if off_cand not in merged:
                merged.append(off_cand)

    return merged[: max(1, limit)]


def google_input_candidates(
    prefix: str,
    *,
    limit: int = 5,
    timeout: float = 1.5,
) -> list[Candidate]:
    """Return `Candidate` objects from Google Input Tools for an ASCII Finglish prefix."""
    q = (prefix or "").strip()
    if len(q) < 2 or not q.isascii() or not any(c.isalpha() for c in q):
        return []
    suggestions = fetch_google_input_suggestions(q, num=limit, timeout=timeout)
    return [
        Candidate(
            text=sug,
            score=1950.0 - idx * 15.0,
            kind=CandidateKind.COMPLETION,
        )
        for idx, sug in enumerate(suggestions[:limit])
    ]


def clean_ai_continuation(context_text: str, raw_completion: str) -> str:
    """Sanitize raw LLM continuation into a concise inline phrase without repeating context."""
    cleaned = (raw_completion or "").strip().strip("\"'«»`")
    if not cleaned:
        return ""
    # Take only the first line
    cleaned = cleaned.splitlines()[0].strip()
    ctx = (context_text or "").strip()
    if ctx and cleaned.lower().startswith(ctx.lower()):
        cleaned = cleaned[len(ctx) :].strip()
    # Avoid returning long multi-sentence paragraphs for inline ghost/popup completion
    words = cleaned.split()
    if len(words) > 8:
        cleaned = " ".join(words[:8])
    if any("\u0600" <= c <= "\u06ff" for c in cleaned):
        cleaned = normalize_persian(cleaned, digits="keep", fix_zwnj=True, fix_spacing=True)
    return cleaned.strip()


def predict_ai_continuation(
    context_text: str,
    ai_engine: Any,
) -> str:
    """Generate a concise 2–8 word inline sentence continuation using `ai_engine`."""
    ctx = (context_text or "").strip()
    if not ctx or len(ctx) < 4 or ai_engine is None:
        return ""

    with _CACHE_LOCK:
        if ctx in _AI_CONT_CACHE:
            _AI_CONT_CACHE.move_to_end(ctx)
            return _AI_CONT_CACHE[ctx]

    try:
        raw = ai_engine.process("complete", ctx)
    except Exception as exc:  # noqa: BLE001
        log.debug("AI inline continuation skipped: %s", exc)
        return ""

    if not raw or raw.startswith("❌"):
        return ""
    continuation = clean_ai_continuation(ctx, raw)
    if continuation:
        with _CACHE_LOCK:
            _AI_CONT_CACHE[ctx] = continuation
            if len(_AI_CONT_CACHE) > _MAX_CACHE_SIZE:
                _AI_CONT_CACHE.popitem(last=False)
    return continuation


def ai_continuation_candidates(context_text: str, ai_engine: Any) -> list[Candidate]:
    """Return a `CandidateKind.NEXT_WORD` suggestion from the AI engine for `context_text`."""
    cont = predict_ai_continuation(context_text, ai_engine)
    if not cont:
        return []
    return [
        Candidate(
            text=cont,
            score=180.0,
            kind=CandidateKind.NEXT_WORD,
        )
    ]

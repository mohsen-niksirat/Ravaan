"""Real-time Persian Orthography Guard and exception blacklist helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from ravan.core.grammar import (
    COMPOUND_CORRECTIONS,
    PREPOSITION_DETACHMENTS,
    TANWEEN_ADVERBS,
)
from ravan.core.normalizer import normalize_arabic_chars

_PERSIAN_WORD_RE = re.compile(r"^[\u0621-\u06FF\u200c]+$")
_PERSIAN_ONLY_DIGITS_RE = re.compile(r"^[\u0660-\u0669\u06F0-\u06F9]+$")

# Unambiguous everyday orthography fixes beyond grammar.py's core tables.
_EXTRA_SAFE_FIXES: dict[str, str] = {
    "انشاالله": "ان‌شاءالله",
    "انشالله": "ان‌شاءالله",
    "انشااله": "ان‌شاءالله",
    "ان شاء الله": "ان‌شاءالله",
    "انشاءالله": "ان‌شاءالله",
    "ماشاالله": "ماشاءالله",
    "ماشالله": "ماشاءالله",
    "بهرحال": "به‌هرحال",
    "علیرغم": "علی‌رغم",
    "هیچوقت": "هیچ‌وقت",
    "هیچکس": "هیچ‌کس",
    "هیچکدام": "هیچ‌کدام",
    "هیچگاه": "هیچ‌گاه",
    "همینطور": "همین‌طور",
    "همانطور": "همان‌طور",
    "اینطور": "این‌طور",
    "آنطور": "آن‌طور",
    "یکدفعه": "یک‌دفعه",
    "بتازگی": "به‌تازگی",
    "بخوبی": "به‌خوبی",
    "درحالیکه": "درحالی‌که",
    "درصورتیکه": "درصورتی‌که",
    "چنانکه": "چنان‌که",
    "علاقمند": "علاقه‌مند",
    "علاقمندی": "علاقه‌مندی",
    "ارزشمند": "ارزشمند",
    "میتوان": "می‌توان",
    "میتواند": "می‌تواند",
    "نمی‌شود": "نمی‌شود",
    "میشود": "می‌شود",
    "نمیشود": "نمی‌شود",
    "میباشد": "می‌باشد",
    "نمیباشد": "نمی‌باشد",
    "میگردد": "می‌گردد",
    "نمیگردد": "نمی‌گردد",
}

# Homographs or strict-only preferences separated from "safe" mode.
_HOMOGRAPH_PREPOSITIONS: frozenset[str] = frozenset({"بنام"})
_STRICT_ONLY_FIXES: dict[str, str] = {
    "لطفا": "لطفاً",
    "احیانا": "احیاناً",
    "ضمنا": "ضمناً",
    "تلفنا": "تلفناً",
    "بنام": "به نام",
}

# Build single-token and multi-token orthography maps without duplicating grammar.py tables.
_SAFE_SINGLE_MAP: dict[str, str] = {}
for _src, _dst in (
    list(PREPOSITION_DETACHMENTS.items())
    + list(TANWEEN_ADVERBS.items())
    + list(COMPOUND_CORRECTIONS.items())
    + list(_EXTRA_SAFE_FIXES.items())
):
    if " " not in _src and _src not in _HOMOGRAPH_PREPOSITIONS and _src != _dst:
        _SAFE_SINGLE_MAP[_src] = _dst

_STRICT_SINGLE_MAP: dict[str, str] = {**_SAFE_SINGLE_MAP, **_STRICT_ONLY_FIXES}

_SAFE_MULTI_MAP: dict[str, str] = {
    src: dst
    for src, dst in list(COMPOUND_CORRECTIONS.items()) + list(_EXTRA_SAFE_FIXES.items())
    if " " in src and src != dst
}


@dataclass(frozen=True)
class OrthographySuggestion:
    """Represents a live orthographic replacement span and reason."""

    original: str
    replacement: str
    reason: str  # "orthography" | "arabic_chars" | "compound" | "tanween" | "preposition"


def normalize_blacklist_token(token: str) -> str:
    """Normalize a word/phrase for blacklist comparisons."""
    cleaned = normalize_arabic_chars(token or "").strip().lower()
    return re.sub(r"\s+", " ", cleaned)


def is_token_blacklisted(token: str, blacklist: Iterable[str] | None) -> bool:
    """Return True if token matches an excluded word/phrase in blacklist."""
    if not token or not blacklist:
        return False
    norm = normalize_blacklist_token(token)
    if not norm:
        return False
    for entry in blacklist:
        if normalize_blacklist_token(str(entry)) == norm:
            return True
    return False


def add_blacklist_token(blacklist: list[str], token: str) -> list[str]:
    """Return updated blacklist including token if not already present."""
    clean = token.strip()
    if not clean:
        return list(blacklist)
    if is_token_blacklisted(clean, blacklist):
        return list(blacklist)
    return [*blacklist, clean]


def is_eligible_persian_token(token: str) -> bool:
    """Return True if token is a pure Persian/Arabic word safe for orthographic checking."""
    if not token or len(token) < 2:
        return False
    if _PERSIAN_ONLY_DIGITS_RE.fullmatch(token):
        return False
    return bool(_PERSIAN_WORD_RE.fullmatch(token))


def check_live_orthography(
    word: str,
    recent_words: list[str] | None = None,
    *,
    mode: str = "safe",
    blacklist: Iterable[str] | None = None,
) -> OrthographySuggestion | None:
    """Evaluate a newly completed Persian word (+ trailing context) for real-time fixes.

    Returns an ``OrthographySuggestion`` whose ``original`` equals the exact trailing
    span to replace (either ``word`` alone or space-joined recent words ending with ``word``).
    """
    m = (mode or "safe").strip().lower()
    if m == "off" or not is_eligible_persian_token(word):
        return None
    if is_token_blacklisted(word, blacklist):
        return None

    # 1. Multi-word phrase check (longest first: 3 words then 2 words on contiguous tokens)
    if recent_words and recent_words[-1] == word:
        for n in (3, 2):
            if len(recent_words) < n:
                continue
            window = recent_words[-n:]
            if not all(
                bool(tok)
                and _PERSIAN_WORD_RE.fullmatch(tok) is not None
                and _PERSIAN_ONLY_DIGITS_RE.fullmatch(tok) is None
                for tok in window
            ):
                continue
            phrase_raw = " ".join(window)
            if is_token_blacklisted(phrase_raw, blacklist):
                continue
            phrase_norm = normalize_arabic_chars(phrase_raw)
            repl = _SAFE_MULTI_MAP.get(phrase_norm)
            if repl and repl != phrase_raw:
                return OrthographySuggestion(
                    original=phrase_raw,
                    replacement=repl,
                    reason="compound",
                )

    # 2. Single-token normalization + rule lookup
    table = _STRICT_SINGLE_MAP if m == "strict" else _SAFE_SINGLE_MAP
    arabic_fixed = normalize_arabic_chars(word)

    # Lookup rule on Arabic-normalized form first so 'حتما' with ك/ي is still fixed in one shot
    rule_repl = table.get(arabic_fixed)
    if rule_repl and rule_repl != word:
        reason = "orthography"
        if arabic_fixed in TANWEEN_ADVERBS:
            reason = "tanween"
        elif arabic_fixed in PREPOSITION_DETACHMENTS:
            reason = "preposition"
        elif arabic_fixed in COMPOUND_CORRECTIONS:
            reason = "compound"
        return OrthographySuggestion(original=word, replacement=rule_repl, reason=reason)

    # 3. Standalone Arabic character cleanup (ي -> ی, ك -> ک, ى -> ی, tatweel removal)
    if arabic_fixed != word and is_eligible_persian_token(arabic_fixed):
        return OrthographySuggestion(
            original=word,
            replacement=arabic_fixed,
            reason="arabic_chars",
        )

    return None

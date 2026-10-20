"""Persian text normalizer, typography engine, & contextual digit handler.

استانداردسازی متون فارسی، تصحیح علائم نگارشی، گیومه هوشمند، نیم‌فاصله، و تبدیل ارقام بر اساس بافت متن.
"""

from __future__ import annotations

import re
from typing import Literal

from ravan.core.zwnj import normalize_zwnj

# Digit translation tables
EN_TO_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
FA_TO_EN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

# Character standardization map (Arabic -> Persian)
ARABIC_TO_PERSIAN_CHARS = str.maketrans(
    {
        "ك": "ک",
        "ي": "ی",
        "ى": "ی",
        "ئ": "ی",
        "ھ": "ه",
        "ہ": "ه",
        "ة": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "ء": "",
        "ـ": "",  # Tatweel / Kashida
    }
)

PERSIAN_TYPO_MAP = str.maketrans(
    {
        "ك": "ک",
        "ي": "ی",
        "ى": "ی",
        "ة": "ه",
        "ھ": "ه",
        "ہ": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "ء": "",
        "ـ": "",
    }
)

_CONSECUTIVE_SPACES = re.compile(r"[ \t]+")
_PUNCT_BEFORE_SPACE = re.compile(r"\s+([،؛!?:.؟…])")
_PERSIAN_PUNCT_AFTER = re.compile(r"([،؛؟])([^\s،؛!?:.؟…»\)])")
_EXCLAMATION_AFTER = re.compile(r"(!+)([^\s،؛!?:.؟…»\)])")
_COLON_DOT_AFTER = re.compile(
    r"(?<![0-9۰-۹])([.:])(?![0-9۰-۹\s،؛!?:.؟…»\)])([^\s،؛!?:.؟…»\)])"
)


def en_to_fa_digits(text: str) -> str:
    """Convert English digits (0-9) to Persian digits (۰-۹)."""
    return text.translate(EN_TO_FA_DIGITS)


def fa_to_en_digits(text: str) -> str:
    """Convert Persian and Arabic-Indic digits to English digits (0-9)."""
    return text.translate(FA_TO_EN_DIGITS)


def toggle_digits(text: str) -> str:
    """Auto-detect and toggle digits: Persian->English if Persian digits exist, else English->Persian."""
    if any(c in "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩" for c in text):
        return fa_to_en_digits(text)
    return en_to_fa_digits(text)


def format_persian_currency(amount: int | float | str) -> str:
    """Format a number with thousands separators using Persian digits (e.g. ۱,۰۰۰,۰۰۰)."""
    try:
        val = int(amount)
        formatted = f"{val:,}"
    except (ValueError, TypeError):
        formatted = str(amount)
    return en_to_fa_digits(formatted)


def normalize_arabic_chars(text: str) -> str:
    """Standardize Arabic characters (ك, ي, ...) to standard Persian letters."""
    return (
        text.replace("ك", "ک")
        .replace("ي", "ی")
        .replace("ى", "ی")
        .replace("ـ", "")  # Remove kashida
    )


def normalize_persian_typos(word: str) -> list[str]:
    """Return list of candidate corrections for common Persian typing and confusable letter errors."""
    if not word:
        return []
    variants: list[str] = []
    cand1 = word.translate(PERSIAN_TYPO_MAP)
    if cand1 != word:
        variants.append(cand1)
    if "ة" in word:
        cand2 = word.replace("ة", "ت").translate(PERSIAN_TYPO_MAP)
        if cand2 != word and cand2 not in variants:
            variants.append(cand2)
    return variants


def normalize_persian_punctuation(text: str) -> str:
    """Apply Persian typographic punctuation, smart quotes, ellipsis, and spacing rules."""
    if not text:
        return ""

    result = text

    # Protect URLs, emails, and web domains from punctuation modifications
    protected_urls: list[str] = []

    def _protect_url(match: re.Match) -> str:
        idx = len(protected_urls)
        protected_urls.append(match.group(0))
        return f"\x00PUNCT_URL_{idx}\x00"

    url_regex = re.compile(
        r"(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+|\b[a-zA-Z0-9-]+\.(?:com|org|net|ir|dev|io|gov|edu)(?:/[^\s]*)?)"
    )
    result = url_regex.sub(_protect_url, result)

    # 1. Ellipsis: replace 3 consecutive dots with horizontal ellipsis (…)
    result = re.sub(r"(?<!\.)\.{3}(?!\.)", "…", result)

    # 2. Smart quotes: replace straight quotes ("..." or “...”) with Persian guillemets («...»)
    # only when the enclosed text contains Persian letters
    result = re.sub(r'["“]([^"”\n]*[آ-ی][^"”\n]*)["”]', r"«\1»", result)

    # 3. Contextual Persian question mark: '?' preceded by Persian letters/numbers or ZWNJ
    result = re.sub(r"(?<=[آ-ی۰-۹\u200c])\s*\?", "؟", result)

    # 4. Contextual Persian comma: ',' preceded by Persian letters/ZWNJ (not numbers like 1,000)
    result = re.sub(r"(?<=[آ-ی\u200c])\s*,(?!\d)", "،", result)

    # 5. Contextual Persian semicolon: ';' preceded by Persian letters/ZWNJ (not HTML entity)
    result = re.sub(r"(?<=[آ-ی\u200c])\s*;(?![a-zA-Z0-9#]+;)", "؛", result)

    # 6. Spacing inside brackets and quotes: remove spaces immediately inside opening and closing
    result = re.sub(r"([(\[«])\s+", r"\1", result)
    result = re.sub(r"\s+([)\]»])", r"\1", result)

    # 7. Spacing outside brackets: ensure space before opening and space after closing
    result = re.sub(r"(?<=[^(\[«\s\n/\\-])([(\[«])", r" \1", result)
    result = re.sub(r"([)\]»])(?=[^\s)\]»\n،؛!?:.؟…/\\-])", r"\1 ", result)

    # 8. Spacing around punctuation: remove space before
    result = _PUNCT_BEFORE_SPACE.sub(r"\1", result)

    # 9. Spacing around punctuation: ensure space after (protecting decimals and times)
    result = _PERSIAN_PUNCT_AFTER.sub(r"\1 \2", result)
    result = _EXCLAMATION_AFTER.sub(r"\1 \2", result)
    result = _COLON_DOT_AFTER.sub(r"\1 \2", result)

    # 10. Collapse consecutive spaces
    result = _CONSECUTIVE_SPACES.sub(" ", result)

    # Restore protected URLs and domains
    for idx, orig in enumerate(protected_urls):
        result = result.replace(f"\x00PUNCT_URL_{idx}\x00", orig)

    return result.strip()


def normalize_contextual_digits(
    text: str, mode: Literal["auto", "fa", "en", "keep"] = "auto"
) -> str:
    """Convert digits based on linguistic and technical context.

    - "auto": Persian digits in Persian text; Latin digits in URLs, code, and English prose.
    - "fa": All digits converted to Persian digits (۰-۹).
    - "en": All digits converted to English digits (0-9).
    - "keep": Digits preserved as-is.
    """
    if not text or mode == "keep":
        return text

    if mode == "fa":
        return en_to_fa_digits(text)
    if mode == "en":
        return fa_to_en_digits(text)

    # In "auto" mode:
    # Protect URLs, emails, file paths, versions, and technical tokens
    protected_tokens: list[str] = []

    def _protect(match: re.Match) -> str:
        token = match.group(0)
        idx = len(protected_tokens)
        protected_tokens.append(token)
        return f"\x00PROTECTED_{idx}\x00"

    # Regex for technical tokens that MUST keep English digits
    technical_regex = re.compile(
        r"(https?://[^\s]+|[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+|"
        r"[a-zA-Z]:\\[^\s]+|/[a-zA-Z0-9_./-]+|\b0x[0-9a-fA-F]+\b|\b\d{1,3}(?:\.\d{1,3}){3}\b|"
        r"\b[vV]\d+(?:\.\d+)*\b|\b[a-zA-Z]+-?\d+[a-zA-Z0-9_-]*\b|\b\d+[a-zA-Z]+[a-zA-Z0-9_-]*\b)"
    )

    masked_text = technical_regex.sub(_protect, text)

    # Now convert numbers that appear in Persian linguistic context
    def _digit_repl(match: re.Match) -> str:
        num = match.group(0)
        start = match.start()
        end = match.end()

        # Look around 25 chars before and after to determine linguistic context
        ctx_before = masked_text[max(0, start - 25) : start]
        ctx_after = masked_text[end : min(len(masked_text), end + 25)]
        surrounding = ctx_before + ctx_after

        fa_count = sum(1 for c in surrounding if "آ" <= c <= "ی" or c in "،؛؟\u200c")
        en_count = sum(1 for c in surrounding if "a" <= c.lower() <= "z")

        if fa_count >= en_count and fa_count > 0:
            return en_to_fa_digits(num)
        return num

    # Match sequences of ASCII digits (with optional decimal point/colon in Persian numbers)
    digit_pattern = re.compile(r"\b\d+(?:[.:]\d+)*\b")
    processed = digit_pattern.sub(_digit_repl, masked_text)

    # Restore protected technical tokens
    for idx, orig in enumerate(protected_tokens):
        processed = processed.replace(f"\x00PROTECTED_{idx}\x00", orig)

    return processed


def normalize_punctuation_spacing(text: str) -> str:
    """Backward-compatible helper: fix spacing around Persian punctuation marks."""
    return normalize_persian_punctuation(text)


def normalize_persian(
    text: str,
    digits: Literal["auto", "fa", "en", "keep"] = "keep",
    fix_zwnj: bool = True,
    fix_spacing: bool = True,
    fix_punctuation: bool = True,
) -> str:
    """Comprehensive Persian text normalizer."""
    if not text:
        return ""

    result = normalize_arabic_chars(text)
    if fix_zwnj:
        result = normalize_zwnj(result)
    if fix_punctuation:
        result = normalize_persian_punctuation(result)
    elif fix_spacing:
        # Fallback to spacing only if punctuation conversion is disabled
        result = _PUNCT_BEFORE_SPACE.sub(r"\1", result)
        result = _PERSIAN_PUNCT_AFTER.sub(r"\1 \2", result)
        result = _CONSECUTIVE_SPACES.sub(" ", result)

    if digits in ("auto", "fa", "en"):
        result = normalize_contextual_digits(result, mode=digits)

    return result


def clean_pasted_text(
    text: str,
    digit_mode: Literal["auto", "fa", "en", "keep"] = "auto",
) -> str:
    """Safely clean pasted text: normalize typography while preserving code blocks."""
    if not text:
        return ""

    # Split by fenced code blocks (```...```) or inline code (`...`)
    code_split = re.compile(r"(```[\s\S]*?```|`[^`\n]+`)")
    parts = code_split.split(text)

    cleaned_parts: list[str] = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            # Code block - preserve verbatim
            cleaned_parts.append(part)
        else:
            # Prose text - normalize thoroughly while preserving leading/trailing newlines/spaces
            stripped = part.strip()
            if not stripped:
                cleaned_parts.append(part)
                continue
            leading = part[: len(part) - len(part.lstrip())]
            trailing = part[len(part.rstrip()) :]
            clean_chunk = normalize_persian(
                stripped,
                digits=digit_mode,
                fix_zwnj=True,
                fix_spacing=True,
                fix_punctuation=True,
            )
            cleaned_parts.append(f"{leading}{clean_chunk}{trailing}")

    return "".join(cleaned_parts)

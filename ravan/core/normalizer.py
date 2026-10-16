"""Persian text normalizer & number converter (تبدیل ارقام و استانداردسازی متون)."""

from __future__ import annotations

import re
from typing import Literal

from ravan.core.zwnj import normalize_zwnj

# Digit maps
EN_TO_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
FA_TO_EN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

# Character standardization map (Arabic -> Persian)
ARABIC_TO_PERSIAN_CHARS = str.maketrans(
    {
        "ك": "ک",
        "ي": "ی",
        "ى": "ی",
        "ئ": "ی",  # context-dependent, but standardizing medial/final Arabic forms
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

_CONSECUTIVE_SPACES = re.compile(r"[ \t]+")
# Punctuation spacing: no space before punctuation, 1 space after if followed by a word
_PUNCT_BEFORE_SPACE = re.compile(r"\s+([،؛!?:.؟])")
_PERSIAN_PUNCT_AFTER = re.compile(r"([،؛؟])([^\s،؛!?:.؟»\)])")
_EXCLAMATION_AFTER = re.compile(r"(!+)([^\s،؛!?:.؟»\)])")
_COLON_DOT_AFTER = re.compile(
    r"(?<![0-9۰-۹])([.:])(?![0-9۰-۹\s،؛!?:.؟»\)])([^\s،؛!?:.؟»\)])"
)


def en_to_fa_digits(text: str) -> str:
    """Convert English digits (0-9) to Persian digits (۰-۹)."""
    return text.translate(EN_TO_FA_DIGITS)


def fa_to_en_digits(text: str) -> str:
    """Convert Persian and Arabic-Indic digits to English digits (0-9)."""
    return text.translate(FA_TO_EN_DIGITS)


def toggle_digits(text: str) -> str:
    """Auto-detect and convert digits: Persian->English if Persian digits exist, else English->Persian."""
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
    # Specific targeted replaces to maintain standard Persian orthography
    return (
        text.replace("ك", "ک")
        .replace("ي", "ی")
        .replace("ى", "ی")
        .replace("ـ", "")  # Remove kashida
    )


def normalize_punctuation_spacing(text: str) -> str:
    """Fix spacing around Persian punctuation marks."""
    # Remove spaces before punctuation: "سلام !" -> "سلام!"
    cleaned = _PUNCT_BEFORE_SPACE.sub(r"\1", text)
    # Ensure space after punctuation: "سلام!خوبی" -> "سلام! خوبی"
    cleaned = _PERSIAN_PUNCT_AFTER.sub(r"\1 \2", cleaned)
    cleaned = _EXCLAMATION_AFTER.sub(r"\1 \2", cleaned)
    cleaned = _COLON_DOT_AFTER.sub(r"\1 \2", cleaned)
    # Collapse multiple spaces into single space
    cleaned = _CONSECUTIVE_SPACES.sub(" ", cleaned)
    return cleaned


def normalize_persian(
    text: str,
    digits: Literal["fa", "en", "keep"] = "keep",
    fix_zwnj: bool = True,
    fix_spacing: bool = True,
) -> str:
    """Comprehensive Persian text normalizer."""
    if not text:
        return ""
    result = normalize_arabic_chars(text)
    if fix_zwnj:
        result = normalize_zwnj(result)
    if fix_spacing:
        result = normalize_punctuation_spacing(result)
    if digits == "fa":
        result = en_to_fa_digits(result)
    elif digits == "en":
        result = fa_to_en_digits(result)
    return result

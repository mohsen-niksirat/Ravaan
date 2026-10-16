"""Zero-Width Non-Joiner (ZWNJ / نیم‌فاصله) typography engine."""

from __future__ import annotations

import re

ZWNJ = "\u200c"

_PREFIXES = {"می", "نمی", "بی"}
_GENERAL_SUFFIXES = {
    "ها",
    "های",
    "هایی",
    "هایم",
    "هایت",
    "هایش",
    "هایمان",
    "هایتان",
    "هایشان",
    "تر",
    "ترین",
}
_HEH_SUFFIXES = {"ام", "ات", "اش", "مان", "تان", "شان", "ای", "ی"}

# Regex patterns for batch text normalization
_PREFIX_PATTERN = re.compile(r"\b(ن?می|بی)\s+([آ-ی])")
_SUFFIX_PATTERN = re.compile(
    r"([آ-ی]+)\s+(ها|های|هایی|هایم|هایت|هایش|هایمان|هایتان|هایشان|تر|ترین)\b"
)
_HEH_SUFFIX_PATTERN = re.compile(r"([آ-ی]+[هة])\s+(ام|ات|اش|مان|تان|شان|ای|ی)\b")


def is_zwnj_prefix(word: str) -> bool:
    """Return True if word is a Persian prefix that must connect with ZWNJ."""
    return word in _PREFIXES


def should_attach_suffix(prev_word: str, suffix: str) -> bool:
    """Check if suffix should be attached to prev_word using ZWNJ."""
    if not prev_word:
        return False
    if suffix in _GENERAL_SUFFIXES:
        return True
    if prev_word.endswith(("ه", "ة")) and suffix in _HEH_SUFFIXES:
        return True
    return False


def normalize_zwnj(text: str) -> str:
    """Normalize Persian text by replacing inappropriate spaces with ZWNJ."""
    if not text:
        return ""
    # Prefixes: "می روم" -> "می‌روم"
    result = _PREFIX_PATTERN.sub(rf"\1{ZWNJ}\2", text)
    # General suffixes: "کتاب ها" -> "کتاب‌ها"
    result = _SUFFIX_PATTERN.sub(rf"\1{ZWNJ}\2", result)
    # Silent Heh suffixes: "خانه ام" -> "خانه‌ام"
    result = _HEH_SUFFIX_PATTERN.sub(rf"\1{ZWNJ}\2", result)
    return result

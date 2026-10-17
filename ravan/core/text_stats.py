"""Quick text statistics calculator (word/char count, reading time, language ratio)."""

from __future__ import annotations

import re
from typing import Any

from ravan.core.normalizer import en_to_fa_digits

_FA_PATTERN = re.compile(r"[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]")
_EN_PATTERN = re.compile(r"[A-Za-z]")
_WORD_SPLIT = re.compile(r"[\s\u200c,;.!?:؟،؛\(\)\[\]\{\}\"'\-_/\\+=<>*&^%$#@~`|\n\r\t]+")


def calculate_text_stats(text: str) -> dict[str, Any]:
    """Calculate comprehensive statistics for selected text."""
    if not text:
        return {
            "word_count": 0,
            "char_count": 0,
            "char_no_spaces": 0,
            "reading_time_sec": 0,
            "persian_pct": 0,
            "english_pct": 0,
            "ratio_str": "—",
        }

    char_count = len(text)
    non_space_chars = "".join(c for c in text if not c.isspace() and c != "\u200c")
    char_no_spaces = len(non_space_chars)

    tokens = [t for t in _WORD_SPLIT.split(text) if t]
    word_count = len(tokens)

    # Average adult reading speed: ~200 words per minute
    reading_time_sec = max(1, round(word_count / (200.0 / 60.0))) if word_count > 0 else 0

    fa_chars = len(_FA_PATTERN.findall(text))
    en_chars = len(_EN_PATTERN.findall(text))
    total_letters = fa_chars + en_chars

    if total_letters > 0:
        persian_pct = round(100.0 * fa_chars / total_letters)
        english_pct = round(100.0 * en_chars / total_letters)
    else:
        persian_pct = 0
        english_pct = 0

    ratio_str = f"{persian_pct}% فارسی / {english_pct}% English"

    return {
        "word_count": word_count,
        "char_count": char_count,
        "char_no_spaces": char_no_spaces,
        "reading_time_sec": reading_time_sec,
        "persian_pct": persian_pct,
        "english_pct": english_pct,
        "ratio_str": ratio_str,
    }


def format_stats_summary(stats: dict[str, Any]) -> str:
    """Format statistics into a concise bilingual card for popup display."""
    words = stats["word_count"]
    chars = stats["char_count"]
    no_space = stats["char_no_spaces"]
    sec = stats["reading_time_sec"]
    time_str = f"~{sec}s" if sec < 60 else f"~{sec // 60}m {sec % 60}s"
    time_fa = en_to_fa_digits(time_str)

    return (
        f"📊 Text Statistics (آمار متن)\n"
        f"• Words / کلمات: {words} ({en_to_fa_digits(str(words))})\n"
        f"• Chars / نویسه‌ها: {chars} (No spaces: {no_space})\n"
        f"• Reading time / زمان مطالعه: {time_str} ({time_fa})\n"
        f"• Ratio / نسبت زبان: {stats['ratio_str']}"
    )

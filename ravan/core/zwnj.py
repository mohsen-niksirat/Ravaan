"""Zero-Width Non-Joiner (ZWNJ / نیم‌فاصله) typography engine."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

ZWNJ = "\u200c"

_DATA_RULES_FILE = Path(__file__).resolve().parent.parent / "data" / "zwnj_rules.json"


def _load_rules() -> dict:
    fallback = {
        "prefixes": ["می", "نمی", "بی"],
        "prefix_exceptions": [
            "مینا", "بیمار", "بیست", "بیدار", "میان", "میانه", "میدان", "میهن",
            "میلاد", "میوه", "میراث", "بیم", "بیمه", "میکروب", "میکروفون",
            "میلیارد", "میلیون", "میزبان", "بیزار", "بیسکویت", "میسور", "بیت",
            "میکسر", "میزان",
        ],
        "suffixes": [
            "ها", "های", "هایی", "هایم", "هایت", "هایش", "هایمان", "هایتان",
            "هایشان", "تر", "ترین", "ترش", "ترند", "ترینش",
        ],
        "heh_suffixes": [
            "ام", "ای", "ایم", "اید", "اند", "ات", "اش", "مان", "تان", "شان", "ی",
        ],
        "suffix_exceptions": [
            "شاهنامه", "ماهنامه", "روزنامه", "بارنامه", "پایان‌نامه",
        ],
        "compounds": {
            "گفت و گو": "گفت‌وگو",
            "گفت وگو": "گفت‌وگو",
            "جست و جو": "جست‌وجو",
            "جست وجو": "جست‌وجو",
            "دست کم": "دست‌کم",
            "به ویژه": "به‌ویژه",
            "این که": "این‌که",
            "آن که": "آن‌که",
            "چنان که": "چنان‌که",
            "یک دیگر": "یک‌دیگر",
            "هم دیگر": "هم‌دیگر",
            "دانش آموز": "دانش‌آموز",
            "دانش آموزان": "دانش‌آموزان",
            "دانش پژوه": "دانش‌پژوه",
            "دانش پژوهان": "دانش‌پژوهان",
            "پیش فرض": "پیش‌فرض",
            "سیستم عامل": "سیستم‌عامل",
            "بین المللی": "بین‌المللی",
            "فوق العاده": "فوق‌العاده",
            "علاقه مند": "علاقه‌مند",
            "علاقه مندان": "علاقه‌مندان",
            "روان شناس": "روان‌شناس",
            "روان شناسی": "روان‌شناسی",
            "برنامه نویس": "برنامه‌نویس",
            "برنامه نویسی": "برنامه‌نویسی",
            "شگفت انگیز": "شگفت‌انگیز",
            "هم زمان": "هم‌زمان",
            "هم چنان": "هم‌چنان",
            "هم چنین": "هم‌چنین",
        },
    }

    if _DATA_RULES_FILE.exists():
        try:
            data = json.loads(_DATA_RULES_FILE.read_text(encoding="utf-8"))
            return data
        except Exception as e:
            log.warning("Failed to load zwnj_rules.json (%s), using fallbacks", e)
    return fallback


_RULES = _load_rules()
_PREFIXES = set(_RULES.get("prefixes", []))
_PREFIX_EXCEPTIONS = set(_RULES.get("prefix_exceptions", []))
_GENERAL_SUFFIXES = set(_RULES.get("suffixes", []))
_HEH_SUFFIXES = set(_RULES.get("heh_suffixes", []))
_SUFFIX_EXCEPTIONS = set(_RULES.get("suffix_exceptions", []))
_COMPOUNDS = dict(_RULES.get("compounds", {}))

# Precompiled regex patterns
_PREFIX_REGEX = re.compile(r"\b(ن?می|بی)\s+([آ-ی]+)\b")
_SUFFIX_REGEX = re.compile(
    rf"([آ-ی]+)\s+({'|'.join(sorted(_GENERAL_SUFFIXES, key=len, reverse=True))})\b"
)
_HEH_SUFFIX_REGEX = re.compile(
    rf"([آ-ی]+[هة])\s+({'|'.join(sorted(_HEH_SUFFIXES, key=len, reverse=True))})\b"
)
_VOWEL_SUFFIX_REGEX = re.compile(
    rf"([آ-ی]+[او])\s+({'|'.join(sorted(_HEH_SUFFIXES, key=len, reverse=True))})\b"
)
_MULTIPLE_ZWNJ = re.compile(rf"{ZWNJ}+")
_MISPLACED_ZWNJ_SPACE = re.compile(rf"(\s+{ZWNJ}|{ZWNJ}\s+)")
_ZWNJ_BEFORE_PUNCT = re.compile(rf"{ZWNJ}+([،؛!?:.؟»\)])")
_ZWNJ_AFTER_PUNCT = re.compile(rf"([«\(]){ZWNJ}+")


def is_zwnj_prefix(word: str) -> bool:
    """Return True if word is a Persian prefix that must connect with ZWNJ."""
    return word in _PREFIXES


def is_prefix_exception(word: str) -> bool:
    """Return True if joined word is an exception that should not take ZWNJ."""
    return word in _PREFIX_EXCEPTIONS


def should_attach_suffix(prev_word: str, suffix: str) -> bool:
    """Check if suffix should be attached to prev_word using ZWNJ."""
    if not prev_word or not suffix:
        return False

    clean_prev = prev_word.strip()
    clean_suf = suffix.strip()

    # Suffix exceptions (e.g. روز + نامه -> روزنامه, not روز‌نامه)
    if clean_prev + clean_suf in _SUFFIX_EXCEPTIONS:
        return False
    if f"{clean_prev}{ZWNJ}{clean_suf}" in _SUFFIX_EXCEPTIONS:
        return False

    if clean_suf in _GENERAL_SUFFIXES:
        return True
    if clean_prev.endswith(("ه", "ة")) and clean_suf in _HEH_SUFFIXES:
        return True
    if clean_prev.endswith(("ا", "و")) and clean_suf in _HEH_SUFFIXES:
        return True

    return False


def normalize_zwnj(text: str) -> str:
    """Normalize Persian text by replacing inappropriate spaces with ZWNJ."""
    if not text:
        return ""

    result = text

    # 0. Clean multiple ZWNJs and spaces around ZWNJ
    result = _MULTIPLE_ZWNJ.sub(ZWNJ, result)
    result = re.sub(rf"[ \t]*{ZWNJ}[ \t]*", ZWNJ, result)

    # 1. Normalize compound words
    for compound_phrase, replacement in _COMPOUNDS.items():
        pattern = rf"(?<![آ-ی]){re.escape(compound_phrase)}(?![آ-ی])"
        result = re.sub(pattern, replacement, result)

    # 2. Normalize prefixes (with exception check)
    def _prefix_sub(match: re.Match) -> str:
        prefix = match.group(1)
        root = match.group(2)
        joined = prefix + root
        if joined in _PREFIX_EXCEPTIONS:
            return match.group(0)  # Preserve original
        return f"{prefix}{ZWNJ}{root}"

    result = _PREFIX_REGEX.sub(_prefix_sub, result)

    # 3. Normalize general suffixes (plural, comparative)
    result = _SUFFIX_REGEX.sub(rf"\1{ZWNJ}\2", result)

    # 4. Normalize silent Heh suffixes (personal / possessive)
    result = _HEH_SUFFIX_REGEX.sub(rf"\1{ZWNJ}\2", result)

    # 5. Normalize vowel endings with personal suffixes
    result = _VOWEL_SUFFIX_REGEX.sub(rf"\1{ZWNJ}\2", result)

    # 6. Clean any remaining ZWNJ adjacent to punctuation
    result = _ZWNJ_BEFORE_PUNCT.sub(r"\1", result)
    result = _ZWNJ_AFTER_PUNCT.sub(r"\1", result)

    return result

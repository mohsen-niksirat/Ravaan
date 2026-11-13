"""Zero-Width Non-Joiner (ZWNJ / نیم‌فاصله) typography engine."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from pathlib import Path

log = logging.getLogger(__name__)

ZWNJ = "\u200c"

_DATA_RULES_FILE = Path(__file__).resolve().parent.parent / "data" / "zwnj_rules.json"
_PERSIAN_WORD_RE = re.compile(r"^[آ-ی]+$")
_PERSIAN_CHAR_RE = re.compile(r"[آ-ی\u200c]")

_COLLOQUIAL_HEH_ONLY = {"مون", "تون", "شون"}

_JOINED_MI_SKIP_PREFIXES: tuple[str, ...] = (
    "میان",
    "میدان",
    "میلیون",
    "میلیارد",
    "میلیمت",
    "میکروب",
    "میکروف",
    "میکرو",
    "میکان",
    "مینیم",
    "میزبان",
    "میخانه",
    "میکده",
    "میهمان",
    "میلاد",
    "میراث",
    "میهن",
    "میزان",
    "میوه",
)

_COMMON_TWO_CHAR_VERB_STEMS = {
    "شه", "رم", "ره", "ری", "دی", "شم", "گم", "گه", "دم", "ده",
}

_HA_SUFFIXES: tuple[str, ...] = (
    "هایشان",
    "هایمان",
    "هایتان",
    "هاشون",
    "هامون",
    "هاتون",
    "هایی",
    "هایم",
    "هایت",
    "هایش",
    "هاست",
    "های",
    "هام",
    "هات",
    "هاش",
    "ها",
)

_JOINED_COMPARATIVE_BASES = {
    "بزرگ", "کوچک", "قشنگ", "زیبا", "سریع", "قدیمی", "جدید", "مهم", "سخت",
    "راحت", "آسان", "نزدیک", "طولانی", "زیاد", "ارزان", "گران", "شیرین",
    "سبک", "سنگین", "قوی", "ضعیف", "باهوش", "خوشگل", "بدگل", "زشت",
    "باریک", "پهن", "بلند", "کوتاه", "تمیز", "کثیف", "صاف", "تند",
    "آهسته", "شلوغ", "خلوت", "جالب", "عجیب", "حیاتی", "مفید", "مضر",
    "دقیق", "سالم", "خراب", "عالی", "مناسب", "پایدار", "فوری",
}

_NON_ZWNJ_JOINED_SKIP = {
    "اینجا", "آنجا", "اینطور", "آنطور", "همینطور", "همانطور",
    "اینگونه", "آنگونه", "همچنان", "همچنین", "کمکم", "تکتک",
    "بیاورد", "روبهرو", "روبرو",
}


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

_HEH_SUFFIXES_NO_COLLOQUIAL = sorted(
    (_HEH_SUFFIXES - _COLLOQUIAL_HEH_ONLY), key=len, reverse=True
)
_HEH_SUFFIXES_ALL_SORTED = sorted(_HEH_SUFFIXES, key=len, reverse=True)
_GENERAL_SUFFIXES_SORTED = sorted(_GENERAL_SUFFIXES, key=len, reverse=True)
_COMPOUNDS_BY_LEN: list[tuple[str, str]] = sorted(
    _COMPOUNDS.items(), key=lambda kv: len(kv[0]), reverse=True
)
_JOINED_COMPOUNDS: dict[str, str] = {
    phrase.replace(" ", ""): repl
    for phrase, repl in _COMPOUNDS.items()
    if ZWNJ in repl and repl.replace(ZWNJ, "") not in _NON_ZWNJ_JOINED_SKIP
}

# Precompiled regex patterns
_PREFIX_REGEX = re.compile(r"\b(ن?می|بی)\s+([آ-ی]+)\b")
_SUFFIX_REGEX = re.compile(
    rf"([آ-ی]+)\s+({'|'.join(_GENERAL_SUFFIXES_SORTED)})\b"
)
_HEH_SUFFIX_REGEX = re.compile(
    rf"([آ-ی]+[هة])\s+({'|'.join(_HEH_SUFFIXES_ALL_SORTED)})\b"
)
_VOWEL_SUFFIX_REGEX = re.compile(
    rf"([آ-ی]+[او])\s+({'|'.join(_HEH_SUFFIXES_NO_COLLOQUIAL)})\b"
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

    # Do not attach suffixes onto numbers/punctuation tokens
    if not _PERSIAN_CHAR_RE.search(clean_prev):
        return False

    # Suffix exceptions (e.g. روز + نامه -> روزنامه, not روز‌نامه)
    if clean_prev + clean_suf in _SUFFIX_EXCEPTIONS:
        return False
    if f"{clean_prev}{ZWNJ}{clean_suf}" in _SUFFIX_EXCEPTIONS:
        return False

    if clean_suf in _GENERAL_SUFFIXES:
        return True
    if clean_prev.endswith(("ه", "ة")) and clean_suf in _HEH_SUFFIXES:
        return True
    if (
        clean_prev.endswith(("ا", "و"))
        and clean_suf in _HEH_SUFFIXES
        and clean_suf not in _COLLOQUIAL_HEH_ONLY
    ):
        return True

    return False


def match_trailing_compound(text_before_delim: str) -> tuple[str, str] | None:
    """Match a spaced compound phrase right at the end of text_before_delim."""
    if not text_before_delim:
        return None
    for phrase, replacement in _COMPOUNDS_BY_LEN:
        if text_before_delim.endswith(phrase):
            start_idx = len(text_before_delim) - len(phrase)
            if start_idx == 0 or not _PERSIAN_CHAR_RE.match(text_before_delim[start_idx - 1]):
                return phrase, replacement
    return None


def fix_joined_zwnj(
    word: str,
    dict_contains: Callable[[str], bool] | None = None,
) -> str | None:
    """Insert missing ZWNJ into a joined Persian word typed without spaces, or return None."""
    if not word or ZWNJ in word or len(word) < 4:
        return None
    if not _PERSIAN_WORD_RE.match(word):
        return None

    # 1. Explicit joined compound spellings (e.g. برنامهنویس -> برنامه‌نویس)
    if word in _JOINED_COMPOUNDS:
        return _JOINED_COMPOUNDS[word]

    # 2. Verbal/privative prefixes typed joined without ZWNJ (نمیدانم -> نمی‌دانم, میروم -> می‌روم)
    if word not in _PREFIX_EXCEPTIONS:
        if word.startswith("نمی") and len(word) >= 5:
            stem = word[3:]
            stem_valid = (
                stem in _COMMON_TWO_CHAR_VERB_STEMS
                or (dict_contains(stem) if dict_contains is not None else len(stem) >= 3)
            )
            if stem_valid:
                return f"نمی{ZWNJ}{stem}"

        if word.startswith("می") and not word.startswith(_JOINED_MI_SKIP_PREFIXES):
            stem = word[2:]
            if stem in _COMMON_TWO_CHAR_VERB_STEMS:
                return f"می{ZWNJ}{stem}"
            if len(stem) >= 3 and dict_contains is not None and dict_contains(stem):
                return f"می{ZWNJ}{stem}"

    # 3. Joined suffixes typed without ZWNJ (برنامهها -> برنامه‌ها, کتابها -> کتاب‌ها)
    if word not in _SUFFIX_EXCEPTIONS:
        for suf in _HA_SUFFIXES:
            if word.endswith(suf):
                base = word[: -len(suf)]
                if len(base) < 3:
                    continue
                if base.endswith("ه"):
                    if dict_contains is None or dict_contains(base):
                        return f"{base}{ZWNJ}{suf}"
                elif dict_contains is not None and dict_contains(base):
                    return f"{base}{ZWNJ}{suf}"

        for suf in ("ترین", "تر"):
            if word.endswith(suf):
                base = word[: -len(suf)]
                if len(base) < 3:
                    continue
                if base.endswith("ه") and (dict_contains is None or dict_contains(base)):
                    return f"{base}{ZWNJ}{suf}"
                if base in _JOINED_COMPARATIVE_BASES:
                    return f"{base}{ZWNJ}{suf}"

    return None


def normalize_zwnj(text: str) -> str:
    """Normalize Persian text by replacing inappropriate spaces with ZWNJ."""
    if not text:
        return ""

    result = text

    # 0. Clean multiple ZWNJs and spaces around ZWNJ
    result = _MULTIPLE_ZWNJ.sub(ZWNJ, result)
    result = re.sub(rf"[ \t]*{ZWNJ}[ \t]*", ZWNJ, result)

    # 1. Normalize compound words
    for compound_phrase, replacement in _COMPOUNDS_BY_LEN:
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

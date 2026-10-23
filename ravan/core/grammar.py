"""Persian Grammar, Preposition Detachment, Tanween, & Typography Assistant.

Enforces Academy of Persian Language and Literature (فرهنگستان زبان و ادب فارسی)
rules for preposition detachment («به نام» not «بنام»), adverbial tanween
(«حتماً» not «حتما»), compound word cohesion («گفت‌وگو»، «روبه‌رو»), and ezafe.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

# Preposition detachment mappings:
# Prefix 'ب' incorrectly attached to nouns/adverbs -> 'به ' + noun
# Note: 'بیاد' is deliberately excluded because it is overwhelmingly used as
# the colloquial form of 'بیاید' (third-person subjunctive of آمدن).
PREPOSITION_DETACHMENTS: dict[str, str] = {
    "بنام": "به نام",
    "بسوی": "به سوی",
    "بعنوان": "به عنوان",
    "بصورت": "به صورت",
    "بطور": "به طور",
    "بخاطر": "به خاطر",
    "بدلیل": "به دلیل",
    "بویژه": "به ویژه",
    "بهمراه": "به همراه",
    "بعلاوه": "به علاوه",
    "بموقع": "به موقع",
    "بجای": "به جای",
    "بمحض": "به محض",
    "بمرور": "به مرور",
    "بوضوح": "به وضوح",
    "بشدت": "به شدت",
    "بندرت": "به ندرت",
    "برغم": "به رغم",
    "بشکل": "به شکل",
    "بواسطه": "به واسطه",
    "بتدریج": "به تدریج",
    "بنظر": "به نظر",
    "بشرط": "به شرط",
    "بسرعت": "به سرعت",
    "بسختی": "به سختی",
    "بروشنی": "به روشنی",
    "بگرمی": "به گرمی",
    "بآسانی": "به آسانی",
    "بآرامی": "به آرامی",
    "بسهولت": "به سهولت",
    "بصراحت": "به صراحت",
    "بدقت": "به دقت",
    "بکندی": "به کندی",
}

# Arabic-origin Persian adverbs needing Tanween Fatha (ـاً):
# Note: 'عرفا' is excluded because it is the standard plural of 'عارف' (mystics).
TANWEEN_ADVERBS: dict[str, str] = {
    "اصلا": "اصلاً",
    "حتما": "حتماً",
    "واقعا": "واقعاً",
    "مثلا": "مثلاً",
    "عملا": "عملاً",
    "دایما": "دائماً",
    "دائما": "دائماً",
    "احتمالا": "احتمالاً",
    "کاملا": "کاملاً",
    "تقریبا": "تقریباً",
    "مجددا": "مجدداً",
    "موقتا": "موقتاً",
    "سریعا": "سریعاً",
    "شخصا": "شخصاً",
    "نسبتا": "نسبتاً",
    "قبلا": "قبلاً",
    "بعدا": "بعداً",
    "مستقیما": "مستقیماً",
    "خصوصا": "خصوصاً",
    "نهایتا": "نهایتاً",
    "صرفا": "صرفاً",
    "ظاهرا": "ظاهراً",
    "لزوما": "لزوماً",
    "فورا": "فوراً",
    "اولا": "اولاً",
    "ثانیا": "ثانياً",
    "ثالثا": "ثالثاً",
    "طبعا": "طبعاً",
    "قاعدتا": "قاعدتاً",
    "عمدتا": "عمدتاً",
    "متقابلا": "متقابلاً",
    "مطلقا": "مطلقاً",
    "دقیقا": "دقیقاً",
    "شرعا": "شرعاً",
    "قانونا": "قانوناً",
    "منحصرا": "منحصراً",
    "صراحتا": "صراحتاً",
    "عجالتا": "عجالتاً",
    "سهوا": "سهواً",
    "غالبا": "غالباً",
    "حقیقتا": "حقیقتاً",
    "رسما": "رسماً",
    "اخلاقا": "اخلاقاً",
    "تدریجا": "تدریجاً",
    "منطقا": "منطقاً",
    "عینا": "عیناً",
    "جزئا": "جزئاً",
    "کلا": "کلاً",
    "ابدا": "ابداً",
}

# Common Persian compound words and office idioms requiring cohesion or ZWNJ
COMPOUND_CORRECTIONS: dict[str, str] = {
    "گفت و گو": "گفت‌وگو",
    "گفتگو": "گفت‌وگو",
    "رو به رو": "روبه‌رو",
    "دست آورد": "دستاورد",
    "دست آورد ها": "دستاوردها",
    "دست آوردها": "دستاوردها",
    "پیش نهاد": "پیشنهاد",
    "پیش نهاد ها": "پیشنهادها",
    "پیش نهادها": "پیشنهادها",
    "باز گو": "بازگو",
    "جست و جو": "جست‌وجو",
    "جستجو": "جست‌وجو",
    "رفت و آمد": "رفت‌وآمد",
    "صرف نظر": "صرف‌نظر",
    "مد نظر": "مدنظر",
    "نقطه نظر": "نقطه‌نظر",
    "نقطه نظرات": "نقطه‌نظرات",
    "علی رغم": "علی‌رغم",
    "فوق العاده": "فوق‌العاده",
    "قابل توجه": "قابل‌توجه",
    "قابل قبول": "قابل‌قبول",
    "غیر قابل": "غیرقابل",
    "دست دوم": "دست‌دوم",
    "راه حل": "راه‌حل",
    "راه حل ها": "راه‌حل‌ها",
    "راه حلها": "راه‌حل‌ها",
    "راه کار": "راهکار",
    "پایان نامه": "پایان‌نامه",
    "شناس نامه": "شناسنامه",
}


@dataclass(frozen=True)
class GrammarIssue:
    start: int
    end: int
    original: str
    replacement: str
    category: Literal["preposition", "tanween", "compound", "heh_kasre", "ezafe"]
    description: str


def _word_boundary_regex(phrase: str) -> re.Pattern[str]:
    escaped = re.escape(phrase)
    return re.compile(rf"(?<![آ-یء\u200c]){escaped}(?![آ-یء\u200c])")


# Compiled patterns for rapid replacement (sorted longest-first to prevent prefix shadowing)
_PREPOSITION_PATTERNS = [
    (_word_boundary_regex(wrong), right)
    for wrong, right in sorted(PREPOSITION_DETACHMENTS.items(), key=lambda kv: len(kv[0]), reverse=True)
]

_TANWEEN_PATTERNS = [
    (_word_boundary_regex(wrong), right)
    for wrong, right in sorted(TANWEEN_ADVERBS.items(), key=lambda kv: len(kv[0]), reverse=True)
]

_COMPOUND_PATTERNS = [
    (_word_boundary_regex(wrong), right)
    for wrong, right in sorted(COMPOUND_CORRECTIONS.items(), key=lambda kv: len(kv[0]), reverse=True)
]

# Silent Heh + Ezafe: e.g. "خانه ی من" -> "خانه‌ی من", "پروژه ی Ravaan" -> "پروژه‌ی Ravaan"
_HEH_YE_PATTERN = re.compile(r"([آ-یء\u200c]+[هة])\s+[یي](?=\s+\S)")


def fix_prepositions(text: str) -> str:
    """Detach prepositions incorrectly fused to nouns (e.g. «بنام» -> «به نام»)."""
    if not text:
        return text
    result = text
    for pattern, repl in _PREPOSITION_PATTERNS:
        result = pattern.sub(repl, result)
    return result


def fix_tanween(text: str) -> str:
    """Add missing tanween fatha to Arabic-derived Persian adverbs (e.g. «حتما» -> «حتماً»)."""
    if not text:
        return text
    result = text
    for pattern, repl in _TANWEEN_PATTERNS:
        result = pattern.sub(repl, result)
    return result


def fix_compounds(text: str) -> str:
    """Standardize Persian compound words and idioms (e.g. «گفتگو» -> «گفت‌وگو»)."""
    if not text:
        return text
    result = text
    for pattern, repl in _COMPOUND_PATTERNS:
        result = pattern.sub(repl, result)
    return result


def fix_ezafe_heh(text: str) -> str:
    """Fix ezafe after silent heh (e.g. «خانه ی ما» -> «خانه‌ی ما»)."""
    if not text:
        return text
    return _HEH_YE_PATTERN.sub(lambda m: f"{m.group(1)}\u200cی", text)


def correct_persian_grammar(
    text: str,
    prepositions: bool = True,
    tanween: bool = True,
    compounds: bool = True,
    ezafe: bool = True,
) -> str:
    """Apply all Persian grammar, preposition, tanween, and compound cohesion rules."""
    if not text:
        return ""
    result = text
    if prepositions:
        result = fix_prepositions(result)
    if tanween:
        result = fix_tanween(result)
    if compounds:
        result = fix_compounds(result)
    if ezafe:
        result = fix_ezafe_heh(result)
    return result


def inspect_grammar(text: str) -> list[GrammarIssue]:
    """Find and return all grammar and preposition issues in the given text."""
    if not text:
        return []
    issues: list[GrammarIssue] = []

    # Check prepositions
    for pattern, repl in _PREPOSITION_PATTERNS:
        for m in pattern.finditer(text):
            issues.append(
                GrammarIssue(
                    start=m.start(),
                    end=m.end(),
                    original=m.group(0),
                    replacement=repl,
                    category="preposition",
                    description=f"جداسازی حرف اضافه «به»: {m.group(0)} ← {repl}",
                )
            )

    # Check tanween
    for pattern, repl in _TANWEEN_PATTERNS:
        for m in pattern.finditer(text):
            issues.append(
                GrammarIssue(
                    start=m.start(),
                    end=m.end(),
                    original=m.group(0),
                    replacement=repl,
                    category="tanween",
                    description=f"افزودن تنوین نصب: {m.group(0)} ← {repl}",
                )
            )

    # Check compounds
    for pattern, repl in _COMPOUND_PATTERNS:
        for m in pattern.finditer(text):
            issues.append(
                GrammarIssue(
                    start=m.start(),
                    end=m.end(),
                    original=m.group(0),
                    replacement=repl,
                    category="compound",
                    description=f"اصلاح واژه مرکب / نیم‌فاصله: {m.group(0)} ← {repl}",
                )
            )

    # Check ezafe
    for m in _HEH_YE_PATTERN.finditer(text):
        repl = f"{m.group(1)}\u200cی"
        issues.append(
            GrammarIssue(
                start=m.start(),
                end=m.end(),
                original=m.group(0),
                replacement=repl,
                category="ezafe",
                description=f"اصلاح نشانه اضافه «ی» بعد از های غیرملفوظ: {m.group(0)} ← {repl}",
            )
        )

    # Sort issues by position in text
    issues.sort(key=lambda x: x.start)
    return issues

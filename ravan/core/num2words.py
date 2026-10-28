"""Persian Number to Words and Formatting Engine.

Converts numeric values to Persian textual representation (عدد به حروف),
supports Rial/Toman currency suffixes, and thousands separators.
"""

from __future__ import annotations

from ravan.core.normalizer import en_to_fa_digits, fa_to_en_digits

ONES = ["", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه"]
TEENS = [
    "ده",
    "یازده",
    "دوازده",
    "سیزده",
    "چهارده",
    "پانزده",
    "شانزده",
    "هفده",
    "هجده",
    "نوزده",
]
TENS = ["", "", "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود"]
HUNDREDS = [
    "",
    "یکصد",
    "دویست",
    "سیصد",
    "چهارصد",
    "پانصد",
    "ششصد",
    "هفتصد",
    "هشتصد",
    "نهصد",
]
SCALES = ["", "هزار", "میلیون", "میلیارد", "تریلیون", "کوادریلیون"]

DECIMAL_PLACES = ["", "دهم", "صدم", "هزارم", "ده‌هزارم", "صد‌هزارم", "میلیونیم"]


def _three_digits_to_words(n: int) -> list[str]:
    parts: list[str] = []
    h = n // 100
    r = n % 100
    if h > 0:
        parts.append(HUNDREDS[h])
    if 10 <= r <= 19:
        parts.append(TEENS[r - 10])
    else:
        t = r // 10
        o = r % 10
        if t > 0:
            parts.append(TENS[t])
        if o > 0:
            parts.append(ONES[o])
    return parts


def num_to_persian_words(num: int | float | str) -> str:
    """Convert a number to its Persian words representation."""
    if isinstance(num, str):
        num_str = fa_to_en_digits(num).replace(",", "").strip()
        try:
            if "." in num_str:
                num = float(num_str)
            else:
                num = int(num_str)
        except ValueError:
            return ""

    if isinstance(num, float):
        int_part = int(num)
        frac_part = round(num - int_part, 6)
        if frac_part == 0:
            return num_to_persian_words(int_part)
        frac_str = f"{frac_part:.6f}".split(".")[1].rstrip("0")
        frac_len = len(frac_str)
        frac_val = int(frac_str)
        scale_name = DECIMAL_PLACES[frac_len] if frac_len < len(DECIMAL_PLACES) else ""
        int_words = num_to_persian_words(int_part)
        frac_words = num_to_persian_words(frac_val)
        suffix = f" {scale_name}" if scale_name else ""
        return f"{int_words} ممیز {frac_words}{suffix}"

    if num == 0:
        return "صفر"
    if num < 0:
        return "منفی " + num_to_persian_words(-num)

    parts: list[str] = []
    scale_idx = 0
    n = num
    while n > 0:
        chunk = n % 1000
        if chunk > 0:
            chunk_words = _three_digits_to_words(chunk)
            chunk_text = " و ".join(chunk_words)
            if scale_idx > 0 and scale_idx < len(SCALES) and SCALES[scale_idx]:
                if scale_idx == 1 and chunk == 1:
                    chunk_text = "یک هزار"
                else:
                    chunk_text = f"{chunk_text} {SCALES[scale_idx]}"
            parts.insert(0, chunk_text)
        n //= 1000
        scale_idx += 1

    return " و ".join(parts)


def format_thousands(num: int | float | str, persian_digits: bool = True) -> str:
    """Format a number with thousands separators (e.g. 1250000 -> ۱,۲۵۰,۰۰۰)."""
    if isinstance(num, str):
        num_str = fa_to_en_digits(num).replace(",", "").strip()
        try:
            if "." in num_str:
                num = float(num_str)
            else:
                num = int(num_str)
        except ValueError:
            return ""

    if isinstance(num, float):
        s = f"{num:,.6f}".rstrip("0").rstrip(".")
    else:
        s = f"{num:,}"

    return en_to_fa_digits(s) if persian_digits else s


def to_toman_words(rial_num: int | str) -> str:
    """Convert Rial amount to Toman words (divides by 10)."""
    if isinstance(rial_num, str):
        num_str = fa_to_en_digits(rial_num).replace(",", "").strip()
        try:
            val = int(num_str)
        except ValueError:
            return ""
    else:
        val = int(rial_num)

    toman = val // 10
    remainder = val % 10
    words = num_to_persian_words(toman)
    if remainder > 0:
        remainder_fa = en_to_fa_digits(str(remainder))
        return f"{words} تومان و {remainder_fa} ریال"
    return f"{words} تومان"


def to_rial_words(num: int | str) -> str:
    """Convert number to Persian words with 'ریال' suffix."""
    words = num_to_persian_words(num)
    if words:
        return f"{words} ریال"
    return ""

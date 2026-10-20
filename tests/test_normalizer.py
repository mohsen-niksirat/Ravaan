import json
from pathlib import Path

from ravan.core.normalizer import (
    clean_pasted_text,
    en_to_fa_digits,
    fa_to_en_digits,
    format_persian_currency,
    normalize_arabic_chars,
    normalize_contextual_digits,
    normalize_persian,
    normalize_persian_punctuation,
    normalize_punctuation_spacing,
    toggle_digits,
)


def test_digits_conversion():
    assert en_to_fa_digits("Phone: 09123456789") == "Phone: ۰۹۱۲۳۴۵۶۷۸۹"
    assert fa_to_en_digits("شماره: ۰۹۱۲۳۴۵۶۷۸۹") == "شماره: 09123456789"
    # Arabic-indic digits
    assert fa_to_en_digits("١٢٣٤٥") == "12345"


def test_toggle_digits():
    assert toggle_digits("123") == "۱۲۳"
    assert toggle_digits("۱۲۳") == "123"


def test_persian_currency_formatting():
    assert format_persian_currency(1000000) == "۱,۰۰۰,۰۰۰"
    assert format_persian_currency("25000000") == "۲۵,۰۰۰,۰۰۰"


def test_arabic_chars_normalization():
    assert normalize_arabic_chars("كتاب هاي زيبا") == "کتاب های زیبا"


def test_punctuation_spacing():
    raw = "سلام  ، حال شما چطور است ؟من خوبم !"
    fixed = normalize_punctuation_spacing(raw)
    assert fixed == "سلام، حال شما چطور است؟ من خوبم!"

    # Ensure times and decimal numbers are not broken into "10: 30" or "3. 14"
    time_raw = "ساعت 10:30 و عدد 3.14 و فارسی ۱۰:۳۰ و ۳.۱۴ است."
    assert normalize_punctuation_spacing(time_raw) == time_raw


def test_persian_smart_quotes_and_ellipsis():
    raw = 'او گفت : "دانش آموزان موفق می شوند" ...'
    res = normalize_persian_punctuation(raw)
    assert "«دانش آموزان موفق می شوند»" in res
    assert "…" in res
    assert "..." not in res


def test_contextual_digit_conversion():
    # Persian text converts digits
    fa_text = "در سال 1403 تعداد 50 شرکت جدید ثبت شد."
    assert normalize_contextual_digits(fa_text, mode="auto") == "در سال ۱۴۰۳ تعداد ۵۰ شرکت جدید ثبت شد."

    # URLs and technical tokens preserved in Latin digits
    mixed_text = "سایت https://example.com/api/v2/items?page=12 را ببینید."
    res = normalize_contextual_digits(mixed_text, mode="auto")
    assert "https://example.com/api/v2/items?page=12" in res

    # English text keeps English digits
    en_text = "There are 42 questions in 5 chapters."
    assert normalize_contextual_digits(en_text, mode="auto") == en_text


def test_clean_pasted_text_code_preservation():
    raw = (
        'متن قبل از کد با ارقام 1403 و علائم ? و "گیومه"\n'
        "```python\n"
        "# Code block preserved completely\n"
        "for i in range(10):\n"
        '    print("hello", i)\n'
        "```\n"
        "متن بعد از کد با پیش فرض ها و ..."
    )
    res = clean_pasted_text(raw, digit_mode="auto")
    # Verify code block is unchanged
    assert 'for i in range(10):\n    print("hello", i)' in res
    # Verify prose is normalized
    assert "۱۴۰۳" in res
    assert "«گیومه»" in res
    assert "…" in res
    assert "پیش‌فرض‌ها" in res


def test_full_normalize_persian():
    raw = "من مي روم ، كتاب ها را ببينم !"
    result = normalize_persian(raw, digits="fa")
    assert "می‌روم" in result
    assert "کتاب‌ها" in result
    assert "ببینم!" in result


def test_typography_golden_cases():
    """Verify golden cases from tests/data/typography_golden_cases.json."""
    golden_path = Path(__file__).resolve().parent / "data" / "typography_golden_cases.json"
    assert golden_path.exists(), "Golden cases fixture file missing"

    cases = json.loads(golden_path.read_text(encoding="utf-8"))
    for idx, case in enumerate(cases):
        inp = case["input"]
        expected = case["expected"]
        desc = case.get("description", f"Case {idx}")

        actual = clean_pasted_text(inp, digit_mode="auto")
        assert actual == expected, (
            f"\nGolden case failed: {desc}\n"
            f"Expected: {repr(expected)}\n"
            f"Actual:   {repr(actual)}"
        )

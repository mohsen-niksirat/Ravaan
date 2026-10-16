from ravan.core.normalizer import (
    en_to_fa_digits,
    fa_to_en_digits,
    format_persian_currency,
    normalize_arabic_chars,
    normalize_persian,
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


def test_full_normalize_persian():
    raw = "من مي روم ، كتاب ها را ببينم !"
    result = normalize_persian(raw, digits="fa")
    assert "می‌روم" in result
    assert "کتاب‌ها" in result
    assert "ببینم!" in result

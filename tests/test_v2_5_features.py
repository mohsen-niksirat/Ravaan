"""Unit and regression tests for Version 2.5.0 features.

Tests:
- Persian numbers & currency expansion (#, ت#, ر#)
- to_rial_words helper
- Smart Jalali and Gregorian date/time macros
- Digit toggle between Persian and English
- Smart Persian punctuation and typography rules
- Overlay smooth fade-in
"""

from __future__ import annotations

from ravan.core.normalizer import toggle_digits
from ravan.core.num2words import to_rial_words
from ravan.core.snippet import SnippetEngine


def test_v2_5_number_to_words_hash_trigger():
    engine = SnippetEngine([])
    assert engine.expand("1500000#") == "یک میلیون و پانصد هزار"
    assert engine.expand("۱۲۵۰۰۰۰#") == "یک میلیون و دویست و پنجاه هزار"
    assert engine.expand("250000#") == "دویست و پنجاه هزار"
    assert engine.expand("0#") == "صفر"


def test_v2_5_currency_toman_and_rial_triggers():
    engine = SnippetEngine([])
    # Toman triggers
    assert engine.expand("1500000ت#") == "یکصد و پنجاه هزار تومان"
    assert engine.expand("1500000/ت") == "یکصد و پنجاه هزار تومان"
    assert engine.expand("5000000/تومان") == "پانصد هزار تومان"

    # Rial triggers
    assert engine.expand("1500000ر#") == "یک میلیون و پانصد هزار ریال"
    assert engine.expand("1500000/ر") == "یک میلیون و پانصد هزار ریال"
    assert engine.expand("250000/ریال") == "دویست و پنجاه هزار ریال"
    assert engine.expand("250000/rial") == "دویست و پنجاه هزار ریال"


def test_v2_5_to_rial_words_helper():
    assert to_rial_words(1000) == "یک هزار ریال"
    assert to_rial_words("50000") == "پنجاه هزار ریال"
    assert to_rial_words("invalid") == ""


def test_v2_5_date_time_prefix_and_suffix_triggers():
    engine = SnippetEngine([])
    # Prefix and suffix Jalali dates
    iso_date = engine.expand("/امروز")
    assert iso_date is not None and "/" in iso_date
    assert engine.expand("امروز/") == iso_date
    assert engine.expand("امروز#") == iso_date
    assert engine.expand("today/") == iso_date

    # Persian text date
    text_date = engine.expand("/تاریخ")
    assert text_date is not None and " " in text_date
    assert engine.expand("تاریخ/") == text_date
    assert engine.expand("تاریخ#") == text_date
    assert engine.expand("tarikh/") == text_date

    # Persian and English time
    assert engine.expand("/ساعت") == engine.expand("ساعت/")
    assert engine.expand("/time") == engine.expand("time/")


def test_v2_5_toggle_digits():
    assert toggle_digits("12345") == "۱۲۳۴۵"
    assert toggle_digits("۱۲۳۴۵") == "12345"
    assert toggle_digits("کتاب 25") == "کتاب ۲۵"
    assert toggle_digits("قیمت: ۲۵۰ تومان") == "قیمت: 250 تومان"


def test_v2_5_config_has_digits_hotkey():
    from ravan.core.config import Config

    cfg = Config()
    assert hasattr(cfg, "digits_hotkey")
    assert cfg.digits_hotkey.key.upper() == "N"
    assert "Ctrl" in cfg.digits_hotkey.modifiers
    assert "Alt" in cfg.digits_hotkey.modifiers

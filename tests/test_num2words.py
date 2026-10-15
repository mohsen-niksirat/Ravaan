from ravan.core.num2words import (
    format_thousands,
    num_to_persian_words,
    to_toman_words,
)
from ravan.core.snippet import SnippetEngine


def test_num_to_persian_words_basic():
    assert num_to_persian_words(0) == "صفر"
    assert num_to_persian_words(5) == "پنج"
    assert num_to_persian_words(14) == "چهارده"
    assert num_to_persian_words(25) == "بیست و پنج"
    assert num_to_persian_words(100) == "یکصد"
    assert num_to_persian_words(315) == "سیصد و پانزده"
    assert num_to_persian_words(1000) == "یک هزار"


def test_num_to_persian_words_large_numbers():
    assert num_to_persian_words(1250000) == "یک میلیون و دویست و پنجاه هزار"
    assert num_to_persian_words(1000000001) == "یک میلیارد و یک"
    assert num_to_persian_words(-50) == "منفی پنجاه"


def test_num_to_persian_words_with_persian_digits():
    assert num_to_persian_words("۱۲۵۰۰۰۰") == "یک میلیون و دویست و پنجاه هزار"
    assert num_to_persian_words("۳۱۵") == "سیصد و پانزده"


def test_num_to_persian_words_decimals():
    res = num_to_persian_words(12.5)
    assert "دوازده" in res
    assert "ممیز" in res
    assert "پنج" in res


def test_format_thousands():
    assert format_thousands(1250000, persian_digits=True) == "۱,۲۵۰,۰۰۰"
    assert format_thousands(1250000, persian_digits=False) == "1,250,000"
    assert format_thousands("۱۲۵۰۰۰۰", persian_digits=True) == "۱,۲۵۰,۰۰۰"


def test_to_toman_words():
    assert to_toman_words(1250000) == "یکصد و بیست و پنج هزار تومان"
    assert to_toman_words("5000000") == "پانصد هزار تومان"


def test_snippet_number_suffix_expansion():
    engine = SnippetEngine([])
    assert engine.expand("1250000/w") == "یک میلیون و دویست و پنجاه هزار"
    assert engine.expand("1250000/s") == "۱,۲۵۰,۰۰۰"
    assert engine.expand("5000000/t") == "پانصد هزار تومان"
    assert engine.expand("۱۲۵۰۰۰۰/w") == "یک میلیون و دویست و پنجاه هزار"
    assert engine.expand("hello/w") is None

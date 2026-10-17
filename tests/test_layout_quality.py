"""Unit tests for layout conversion quality (mixed-direction, preserving digits/punct, and last N words)."""

from ravan.core.journal import KeystrokeJournal
from ravan.core.layout import LayoutMapper


def test_mixed_direction_selection():
    mapper = LayoutMapper()
    # Mixed Persian and English with numbers and punctuation
    text = "سلام world 123! خوبی؟"
    converted = mapper.convert_text(text, preserve_digits_punct=True)

    # "سلام" -> "sghl" on English keyboard layout
    assert "sghl" in converted
    # "world" -> "صخقمی"
    assert "صخقمی" in converted
    # Digits and punctuation stay untouched
    assert "123!" in converted
    assert "؟" in converted


def test_preserve_digits_and_punctuation():
    mapper = LayoutMapper()
    # Ensure digits and standard symbols are not corrupted
    raw = "test 123.45 + 67 = 89; /path/to"
    converted = mapper.convert_text(raw, preserve_digits_punct=True)
    assert "123.45" in converted
    assert "+ 67 = 89" in converted
    assert "فثسف" in converted  # 'test' -> 'فثسف'


def test_journal_last_n_words_span():
    journal = KeystrokeJournal()
    for ch in "این یک تست ساده است ":
        journal.push(ch)

    span1, len1 = journal.last_n_words_span(n=1)
    assert span1.strip() == "است"

    span2, len2 = journal.last_n_words_span(n=2)
    assert span2.strip() == "ساده است"

    span3, len3 = journal.last_n_words_span(n=3)
    assert span3.strip() == "تست ساده است"

    # Beyond total words returns all
    span_all, _ = journal.last_n_words_span(n=10)
    assert "این یک تست ساده است" in span_all


def test_journal_pop_last_n_chars():
    journal = KeystrokeJournal()
    for ch in "hello world":
        journal.push(ch)

    popped = journal.pop_last_n_chars(5)
    assert popped == "world"
    assert journal.text() == "hello "

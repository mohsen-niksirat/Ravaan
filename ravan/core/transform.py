"""Text transformation utilities (case cycling, code casing, normalization)."""

from __future__ import annotations

import re

from ravan.core.normalizer import normalize_persian, toggle_digits


def cycle_case(text: str) -> str:
    """Cycle string case through: UPPERCASE -> lowercase -> Title Case -> UPPERCASE.

    Preserves formatting where possible.
    """
    if not text:
        return text

    # Only consider alphabetic characters
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return text

    if text.isupper():
        return text.lower()
    elif text.islower():
        return text.title()
    elif text.istitle():
        return text.upper()
    else:
        # Default starting point for mixed case
        return text.upper()


def to_snake_case(text: str) -> str:
    """Convert string to snake_case (e.g. 'camelCase' or 'Some String' -> 'some_string')."""
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    s = re.sub(r"[\s\-_]+", "_", s)
    return s.strip("_").lower()


def to_camel_case(text: str) -> str:
    """Convert string to camelCase (e.g. 'some_string' -> 'someString')."""
    words = re.split(r"[\s\-_]+", text.strip())
    if not words or words == [""]:
        return text
    first = words[0].lower()
    rest = "".join(w.capitalize() for w in words[1:])
    return first + rest


def to_kebab_case(text: str) -> str:
    """Convert string to kebab-case (e.g. 'some_string' -> 'some-string')."""
    return to_snake_case(text).replace("_", "-")


def normalize_text(text: str, digits: str = "keep") -> str:
    """Normalize Persian text in-place (Arabic chars, ZWNJ, punctuation spacing)."""
    return normalize_persian(text, digits=digits)


def toggle_text_digits(text: str) -> str:
    """Toggle digits between Persian and English."""
    return toggle_digits(text)

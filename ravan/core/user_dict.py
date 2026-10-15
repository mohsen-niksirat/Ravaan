"""User custom dictionary management (%APPDATA%\\Ravan\\user_words.txt)."""

from __future__ import annotations

import logging
from pathlib import Path

from ravan.core.config import config_dir

log = logging.getLogger(__name__)


def user_dict_path() -> Path:
    return config_dir() / "user_words.txt"


def load_user_words(path: Path | None = None) -> list[str]:
    """Load user custom words from disk."""
    p = path or user_dict_path()
    if not p.is_file():
        return []
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
        words: list[str] = []
        for line in lines:
            w = line.strip()
            if w and not w.startswith("#") and w not in words:
                words.append(w)
        return words
    except Exception as e:
        log.warning("Failed to load user words from %s: %e", p, e)
        return []


def save_user_words(words: list[str], path: Path | None = None) -> bool:
    """Save user custom words to disk."""
    p = path or user_dict_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        # Deduplicate while preserving order
        deduped: list[str] = []
        for w in words:
            clean = w.strip()
            if clean and clean not in deduped:
                deduped.append(clean)
        content = "# Ravan User Custom Words (one per line)\n" + "\n".join(deduped) + "\n"
        p.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        log.error("Failed to save user words to %s: %e", p, e)
        return False


def add_user_word(word: str, path: Path | None = None) -> bool:
    """Add a new word to the user dictionary."""
    clean = word.strip()
    if not clean:
        return False
    words = load_user_words(path=path)
    if clean in words:
        return True
    words.append(clean)
    return save_user_words(words, path=path)


def remove_user_word(word: str, path: Path | None = None) -> bool:
    """Remove a word from the user dictionary."""
    clean = word.strip()
    words = load_user_words(path=path)
    if clean not in words:
        return False
    words = [w for w in words if w != clean]
    return save_user_words(words, path=path)

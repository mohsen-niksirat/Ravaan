"""Word-level Before/After diff utilities for the AI Command Palette."""

from __future__ import annotations

import difflib
import re

_TOKEN_RE = re.compile(r"\S+\s*")


def compute_word_diff(before: str, after: str) -> list[tuple[str, str]]:
    """Return compact `('equal' | 'del' | 'ins', text)` spans between `before` and `after`."""
    tokens_a = _TOKEN_RE.findall(before or "")
    tokens_b = _TOKEN_RE.findall(after or "")
    if not tokens_a and not tokens_b:
        return []
    if not tokens_a:
        return [("ins", after)]
    if not tokens_b:
        return [("del", before)]

    matcher = difflib.SequenceMatcher(a=tokens_a, b=tokens_b, autojunk=False)
    spans: list[tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            spans.append(("equal", "".join(tokens_a[i1:i2])))
        elif tag == "delete":
            spans.append(("del", "".join(tokens_a[i1:i2])))
        elif tag == "insert":
            spans.append(("ins", "".join(tokens_b[j1:j2])))
        elif tag == "replace":
            spans.append(("del", "".join(tokens_a[i1:i2])))
            spans.append(("ins", "".join(tokens_b[j1:j2])))

    merged: list[tuple[str, str]] = []
    for op, chunk in spans:
        if not chunk:
            continue
        if merged and merged[-1][0] == op:
            merged[-1] = (op, merged[-1][1] + chunk)
        else:
            merged.append((op, chunk))
    return merged


def summarize_source_preview(text: str, max_chars: int = 58) -> tuple[str, int, int]:
    """Return `(truncated_excerpt, char_count, word_count)` without mutating input."""
    clean = " ".join((text or "").split())
    char_count = len((text or "").strip())
    word_count = len(clean.split()) if clean else 0
    if len(clean) <= max_chars:
        return clean, char_count, word_count
    return clean[: max(8, max_chars - 1)].rstrip() + "…", char_count, word_count

"""Regex triggers, safety validation, and capture group expansion for Snippets 3.0."""

from __future__ import annotations

import logging
import re
import time

log = logging.getLogger(__name__)

# Battery of adversarial/repetitive input strings to detect catastrophic backtracking
_CATASTROPHIC_BATTERY = [
    "a" * 25 + "!",
    "a" * 30,
    "1" * 28 + "x",
    "0" * 30,
    "x" * 15 + "y" * 15 + "z",
    ";" + "d" * 25,
    "سلام " * 10,
    "a" * 20 + "b" * 20,
    "test_sample_word_12345",
]


def extract_regex_pattern(trigger: str) -> str:
    """Extract raw regex pattern from trigger string (stripping 're:' prefix if present)."""
    trig = trigger.strip()
    if trig.lower().startswith("re:"):
        return trig[3:].strip()
    return trig


def validate_regex_trigger(trigger: str, max_bench_ms: float = 1.0) -> tuple[bool, str]:
    """Validate regex trigger syntax, safety, and catastrophic backtracking resistance.

    Returns:
        (is_valid, error_message)
    """
    pattern = extract_regex_pattern(trigger)
    if not pattern:
        return False, "Regex pattern cannot be empty"

    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return False, f"Invalid regex syntax: {exc}"

    # Guard 1: Must not match empty string (prevents triggering on empty typing states)
    try:
        if regex.fullmatch("") or regex.match(""):
            return (
                False,
                "Regex must require at least 1 character and cannot match empty strings",
            )
    except Exception as exc:  # noqa: BLE001
        return False, f"Empty string validation failed: {exc}"

    # Guard 2: Catastrophic backtracking test battery (< max_bench_ms per input)
    max_sec = max_bench_ms / 1000.0
    for sample in _CATASTROPHIC_BATTERY:
        t0 = time.perf_counter()
        try:
            regex.search(sample)
            regex.fullmatch(sample)
        except Exception as exc:  # noqa: BLE001
            return False, f"Regex evaluation crashed on safety test battery: {exc}"
        dt = time.perf_counter() - t0
        if dt > max_sec:
            return (
                False,
                f"Catastrophic backtracking detected (> {max_bench_ms:.1f}ms on test input)",
            )

    return True, ""


def safe_regex_match(
    pattern: str, text: str, max_len: int = 100, timeout_sec: float = 0.005
) -> re.Match[str] | None:
    """Evaluate regex match with input length bound and timeout to prevent ReDoS."""
    if len(text) > max_len:
        return None
    try:
        clean_pat = extract_regex_pattern(pattern)
        regex = re.compile(clean_pat)
        t0 = time.perf_counter()
        m = regex.fullmatch(text)
        if (time.perf_counter() - t0) > timeout_sec:
            log.warning("Regex evaluation exceeded timeout (%s)", pattern)
            return None
        return m
    except Exception as exc:  # noqa: BLE001
        log.debug("Regex match failed for %r: %s", pattern, exc)
        return None


def expand_capture_groups(template: str, match: re.Match[str]) -> str:
    """Expand $1..$9 and \\1..\\9 using capture groups from regex match."""
    res = template
    # First protect double-dollars ($$ -> literal placeholder)
    dollar_guard = "\x00DOLLAR\x00"
    res = res.replace("$$", dollar_guard)

    groups = match.groups()
    for i in range(len(groups), 0, -1):
        val = match.group(i) or ""
        res = res.replace(f"${{{i}}}", val)
        res = res.replace(f"${i}", val)
        res = res.replace(f"\\{i}", val)

    # Restore literal dollars
    res = res.replace(dollar_guard, "$")
    return res


def preview_regex_expansion(
    trigger: str, replacement: str, sample_input: str
) -> tuple[bool, str]:
    """Test regex trigger against sample input and return expanded preview.

    Returns:
        (is_match, output_text_or_error)
    """
    is_valid, err = validate_regex_trigger(trigger)
    if not is_valid:
        return False, err

    clean_pat = extract_regex_pattern(trigger)
    m = safe_regex_match(clean_pat, sample_input)
    if m is None:
        return False, "No match"

    expanded = expand_capture_groups(replacement, m)
    return True, expanded

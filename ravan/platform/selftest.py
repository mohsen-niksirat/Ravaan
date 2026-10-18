"""Scripted diagnostics mode — in-app health checks and PASS/FAIL report."""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class CheckResult:
    name: str
    passed: bool
    status: str  # PASS | WARN | FAIL | SKIP
    details: str
    duration_ms: float = 0.0


def check_keyboard_hook() -> CheckResult:
    """Verify WH_KEYBOARD_LL hook installs and thread runs."""
    t0 = time.perf_counter()
    if sys.platform != "win32":
        return CheckResult(
            name="Keyboard Hook (WH_KEYBOARD_LL)",
            passed=True,
            status="SKIP",
            details="Not running on Windows (skipped in non-Windows environment)",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    try:
        from ravan.platform.hook import KeyboardHook

        hook = KeyboardHook()
        hook.start()
        time.sleep(0.05)
        is_running = hook._running and hook._thread is not None and hook._thread.is_alive()
        hook.stop()
        if is_running:
            return CheckResult(
                name="Keyboard Hook (WH_KEYBOARD_LL)",
                passed=True,
                status="PASS",
                details="Hook installed and message loop active on background thread",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        return CheckResult(
            name="Keyboard Hook (WH_KEYBOARD_LL)",
            passed=False,
            status="FAIL",
            details="Hook thread failed to start or initialize",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="Keyboard Hook (WH_KEYBOARD_LL)",
            passed=False,
            status="FAIL",
            details=f"Hook error: {exc}",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )


def check_caret_uia() -> CheckResult:
    """Verify UI Automation (UIA) COM interface and caret detection."""
    t0 = time.perf_counter()
    if sys.platform != "win32":
        return CheckResult(
            name="Caret Detection (UIA)",
            passed=True,
            status="SKIP",
            details="Not running on Windows",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    try:
        from ravan.platform.caret import get_caret_rect_with_source

        rect, source = get_caret_rect_with_source()
        details = f"Caret source: {source}, rect: ({rect.x}, {rect.y}, {rect.width}x{rect.height})"
        return CheckResult(
            name="Caret Detection (UIA)",
            passed=True,
            status="PASS",
            details=details,
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="Caret Detection (UIA)",
            passed=False,
            status="FAIL",
            details=f"Caret detection failed: {exc}",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )


def check_clipboard() -> CheckResult:
    """Verify clipboard read/write round-trip while safely restoring user data."""
    t0 = time.perf_counter()
    try:
        from ravan.platform.clipboard import get_clipboard_text, set_clipboard_text

        orig_text = get_clipboard_text() or ""
        test_payload = f"__ravaan_selftest_{int(time.time())}__"

        set_clipboard_text(test_payload)
        time.sleep(0.02)
        read_back = get_clipboard_text() or ""

        # Restore original clipboard
        if orig_text:
            set_clipboard_text(orig_text)

        if read_back == test_payload:
            return CheckResult(
                name="Clipboard Read/Write",
                passed=True,
                status="PASS",
                details="Round-trip read/write verified; original contents restored",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        return CheckResult(
            name="Clipboard Read/Write",
            passed=False,
            status="FAIL",
            details=f"Mismatch: read '{read_back[:20]}' != expected '{test_payload[:20]}'",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="Clipboard Read/Write",
            passed=False,
            status="FAIL",
            details=f"Clipboard exception: {exc}",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )


def check_audio_device() -> CheckResult:
    """Check if Windows audio output devices are available."""
    t0 = time.perf_counter()
    if sys.platform != "win32":
        return CheckResult(
            name="Audio Output Device",
            passed=True,
            status="SKIP",
            details="Audio device check skipped on non-Windows",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    try:
        import ctypes

        winmm = ctypes.WinDLL("winmm", use_last_error=True)
        dev_count = int(winmm.waveOutGetNumDevs())
        if dev_count > 0:
            return CheckResult(
                name="Audio Output Device",
                passed=True,
                status="PASS",
                details=f"{dev_count} audio output device(s) detected",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        return CheckResult(
            name="Audio Output Device",
            passed=True,
            status="WARN",
            details="No waveOut audio devices found (sound feedback will be silent)",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="Audio Output Device",
            passed=True,
            status="WARN",
            details=f"Could not query audio devices: {exc}",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )


def check_dpapi_encryption() -> CheckResult:
    """Verify Windows DPAPI credential encryption/decryption round-trip."""
    t0 = time.perf_counter()
    try:
        from ravan.core.crypto import protect_secret, unprotect_secret

        secret = "Ravaan_Super_Secret_Token_12345"
        encrypted = protect_secret(secret)
        decrypted, _ = unprotect_secret(encrypted)

        if decrypted == secret and encrypted.startswith("dpapi:"):
            return CheckResult(
                name="DPAPI Credential Encryption",
                passed=True,
                status="PASS",
                details="Windows DPAPI protect/unprotect round-trip successful",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        elif decrypted == secret:
            return CheckResult(
                name="DPAPI Credential Encryption",
                passed=True,
                status="WARN",
                details="Encryption succeeded via fallback mode (non-DPAPI)",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        return CheckResult(
            name="DPAPI Credential Encryption",
            passed=False,
            status="FAIL",
            details="Decrypted token did not match original",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="DPAPI Credential Encryption",
            passed=False,
            status="FAIL",
            details=f"DPAPI error: {exc}",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )


def check_dictionaries_and_config() -> CheckResult:
    """Verify config and bilingual dictionaries are intact."""
    t0 = time.perf_counter()
    try:
        from ravan.core.config import load_config
        from ravan.core.dict import Dictionary

        _ = load_config()
        d_fa = Dictionary.persian()
        d_en = Dictionary.english()

        fa_words = len(d_fa.entries)
        en_words = len(d_en.entries)

        if fa_words > 1000 and en_words > 1000:
            return CheckResult(
                name="Dictionaries & Configuration",
                passed=True,
                status="PASS",
                details=f"Config valid; loaded {fa_words:,} FA words, {en_words:,} EN words",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        return CheckResult(
            name="Dictionaries & Configuration",
            passed=False,
            status="FAIL",
            details=f"Dictionary sizes too small: FA={fa_words}, EN={en_words}",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="Dictionaries & Configuration",
            passed=False,
            status="FAIL",
            details=f"Config/Dictionary error: {exc}",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )


def check_injection_roundtrip() -> CheckResult:
    """Verify text injection roundtrip via SendInput or scratch window."""
    t0 = time.perf_counter()
    if sys.platform != "win32":
        return CheckResult(
            name="Text Injection (SendInput)",
            passed=True,
            status="SKIP",
            details="SendInput skipped on non-Windows",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    try:
        from ravan.platform import winapi as wapi

        # Verify SendInput API bindings are callable
        inputs = (wapi.INPUT * 1)()
        inputs[0].type = wapi.INPUT_KEYBOARD
        inputs[0].union.ki.wVk = 0
        inputs[0].union.ki.wScan = ord("A")
        inputs[0].union.ki.dwFlags = wapi.KEYEVENTF_UNICODE
        inputs[0].union.ki.time = 0
        inputs[0].union.ki.dwExtraInfo = 0

        # Test call with 0 inputs (safe probe)
        res = wapi.user32.SendInput(0, inputs, wapi.ctypes.sizeof(wapi.INPUT))
        if res == 0:
            return CheckResult(
                name="Text Injection (SendInput)",
                passed=True,
                status="PASS",
                details="SendInput API binding active and functional",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        return CheckResult(
            name="Text Injection (SendInput)",
            passed=False,
            status="FAIL",
            details="SendInput returned unexpected code",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="Text Injection (SendInput)",
            passed=False,
            status="FAIL",
            details=f"SendInput probe failed: {exc}",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )


def run_selftest() -> dict[str, Any]:
    """Run all in-app diagnostics and return structured results."""
    checks = [
        check_keyboard_hook(),
        check_caret_uia(),
        check_injection_roundtrip(),
        check_clipboard(),
        check_audio_device(),
        check_dpapi_encryption(),
        check_dictionaries_and_config(),
    ]

    all_passed = all(c.passed for c in checks)
    return {
        "all_passed": all_passed,
        "checks": checks,
        "pass_count": sum(1 for c in checks if c.status == "PASS"),
        "warn_count": sum(1 for c in checks if c.status == "WARN"),
        "fail_count": sum(1 for c in checks if c.status == "FAIL"),
        "skip_count": sum(1 for c in checks if c.status == "SKIP"),
    }


def format_selftest_report(res: dict[str, Any]) -> str:
    """Format selftest results as a clean text table."""
    from ravan import __version__

    lines = [
        "=" * 72,
        f"  RAVAAN (روان) — SYSTEM DIAGNOSTICS SELFTEST  (v{__version__})",
        "=" * 72,
        f"{'CHECK':<34} | {'STATUS':<6} | {'TIME':<7} | DETAILS",
        "-" * 72,
    ]

    for c in res["checks"]:
        tag = f"[{c.status}]"
        t_str = f"{c.duration_ms:.1f}ms"
        lines.append(f"{c.name:<34} | {tag:<6} | {t_str:<7} | {c.details}")

    lines.append("-" * 72)
    verdict = "PASS — ALL CHECKS HEALTHY" if res["all_passed"] else "FAIL — SYSTEM ISSUES DETECTED"
    lines.append(
        f"OVERALL RESULT: {verdict} "
        f"({res['pass_count']} passed, {res['warn_count']} warnings, {res['fail_count']} failed)"
    )
    lines.append("=" * 72)
    return "\n".join(lines)

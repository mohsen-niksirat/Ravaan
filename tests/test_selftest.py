"""Unit tests for the scripted diagnostics selftest module."""

from __future__ import annotations

import pytest

from ravan.platform.selftest import (
    check_audio_device,
    check_caret_uia,
    check_clipboard,
    check_dictionaries_and_config,
    check_dpapi_encryption,
    check_injection_roundtrip,
    check_keyboard_hook,
    format_selftest_report,
    run_selftest,
)

pytestmark = pytest.mark.windows


def test_individual_selftest_checks():
    """Verify each check returns a valid CheckResult with proper status."""
    c_hook = check_keyboard_hook()
    assert c_hook.status in ("PASS", "SKIP")

    c_caret = check_caret_uia()
    assert c_caret.status in ("PASS", "SKIP")

    c_inject = check_injection_roundtrip()
    assert c_inject.status in ("PASS", "SKIP")

    c_clip = check_clipboard()
    assert c_clip.status == "PASS"

    c_audio = check_audio_device()
    assert c_audio.status in ("PASS", "WARN", "SKIP")

    c_dpapi = check_dpapi_encryption()
    assert c_dpapi.status in ("PASS", "WARN")

    c_dict = check_dictionaries_and_config()
    assert c_dict.status == "PASS"


def test_run_selftest_overall():
    """Verify overall selftest runner produces report and succeeds."""
    res = run_selftest()
    assert isinstance(res, dict)
    assert "all_passed" in res
    assert "checks" in res
    assert len(res["checks"]) >= 7
    assert res["fail_count"] == 0
    assert res["all_passed"] is True

    report = format_selftest_report(res)
    assert "RAVAAN (روان) — SYSTEM DIAGNOSTICS SELFTEST" in report
    assert "PASS — ALL CHECKS HEALTHY" in report

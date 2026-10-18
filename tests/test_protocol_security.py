"""Security and fuzz tests for ravan:// deep link protocol parser."""

from __future__ import annotations

import string

from ravan.platform.protocol import parse_protocol_url


def test_protocol_valid_urls():
    r1 = parse_protocol_url("ravan://settings")
    assert r1["valid"] is True
    assert r1["action"] == "settings"

    r2 = parse_protocol_url("ravan://settings?tab=sync")
    assert r2["valid"] is True
    assert r2["action"] == "settings"
    assert r2["params"].get("tab") == "sync"

    r3 = parse_protocol_url("ravan://stats")
    assert r3["valid"] is True
    assert r3["action"] == "stats"

    r4 = parse_protocol_url("ravan://snippet?trigger=@@email")
    assert r4["valid"] is True
    assert r4["action"] == "snippet"
    assert r4["params"].get("trigger") == "@@email"


def test_protocol_malicious_actions_rejected():
    # Arbitrary code execution attempts
    assert parse_protocol_url("ravan://exec?cmd=calc.exe")["valid"] is False
    assert parse_protocol_url("ravan://run?bin=notepad")["valid"] is False
    assert parse_protocol_url("ravan://cmd?arg=whoami")["valid"] is False

    # Text injection attempts
    assert parse_protocol_url("ravan://inject?text=evil_keystrokes")["valid"] is False

    # Path traversal attempts
    assert parse_protocol_url("ravan://../../Windows/System32/cmd.exe")["valid"] is False
    assert parse_protocol_url(r"ravan://..\..\..\test")["valid"] is False


def test_protocol_parameter_sanitization():
    # Invalid tab name falls back to 'general'
    res = parse_protocol_url("ravan://settings?tab=malicious_fake_tab")
    assert res["valid"] is True
    assert res["params"]["tab"] == "general"

    # Shell injection characters in snippet trigger are stripped
    res2 = parse_protocol_url("ravan://snippet?trigger=@@mail;calc.exe|format")
    assert res2["valid"] is True
    assert ";" not in res2["params"]["trigger"]
    assert "|" not in res2["params"]["trigger"]


def test_protocol_fuzz_inputs():
    # Oversized URL (buffer overflow / ReDoS defense)
    oversized = "ravan://settings?" + ("a" * 5000)
    assert parse_protocol_url(oversized)["valid"] is False

    # Null bytes
    assert parse_protocol_url("ravan://settings\x00calc.exe")["valid"] is False

    # Invalid scheme
    assert parse_protocol_url("http://settings")["valid"] is False
    assert parse_protocol_url("file:///c:/Windows/calc.exe")["valid"] is False

    # Malformed strings and random fuzz bytes
    fuzz_samples = [
        "",
        "   ",
        "ravan:",
        "ravan://",
        "ravan:///",
        "ravan://?tab=",
        "ravan://settings?%zz=invalid_hex",
        "ravan://" + "\t" * 10,
        "ravan://" + "".join(string.punctuation * 5),
    ]
    for s in fuzz_samples:
        res = parse_protocol_url(s)
        assert isinstance(res, dict)
        assert "valid" in res
        assert "action" in res
        assert "params" in res

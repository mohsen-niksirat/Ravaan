"""Tests for clipboard history privacy, password pattern filtering, and expiration."""

from __future__ import annotations

import time

from ravan.core.cliphistory import ClipboardHistory, is_sensitive_pattern


def test_is_sensitive_pattern_detection():
    # Tokens and Keys (constructed dynamically to avoid GitHub push protection false positives)
    dummy_ghp = "gh" + "p_" + "1234567890abcdefghijklmnopqrstuvwxyz"
    dummy_stripe = "sk_" + "live_" + "1234567890abcdefghijklmnopqrst"
    dummy_aws = "AK" + "IAIOSFODNN7EXAMPLE"
    assert is_sensitive_pattern(dummy_ghp) is True
    assert is_sensitive_pattern(dummy_stripe) is True
    assert is_sensitive_pattern(dummy_aws) is True
    assert is_sensitive_pattern("-----BEGIN " + "RSA PRIVATE KEY-----\nMIIE...") is True

    # High-entropy passwords from password managers
    assert is_sensitive_pattern("p@$$w0rd!#123Aa") is True
    assert is_sensitive_pattern("K8#mQ!9vL$2wZ&5x") is True
    assert is_sensitive_pattern("aB3$eF7*hJ9!lM1#") is True

    # Normal text should NOT be flagged as sensitive
    assert is_sensitive_pattern("سلام این یک پیام تست است") is False
    assert is_sensitive_pattern("Hello world, this is a normal sentence.") is False
    assert is_sensitive_pattern("https://github.com/mohsen-niksirat/Ravaan") is False
    assert is_sensitive_pattern("short") is False
    assert is_sensitive_pattern("123456") is False
    assert is_sensitive_pattern("") is False


def test_clipboard_password_manager_exclusion(tmp_path):
    storage = tmp_path / "clip.json"
    ch = ClipboardHistory(storage_path=storage)

    # Password managers
    assert ch.add("secret_key_123", source_app="Bitwarden.exe") is False
    assert ch.add("secret_key_123", source_app="1password.exe") is False
    assert ch.add("secret_key_123", source_app="keepassxc.exe") is False
    assert len(ch.items()) == 0

    # User excluded apps
    assert ch.add("some_text", source_app="notepad.exe", excluded_apps=["notepad.exe"]) is False
    assert len(ch.items()) == 0

    # Normal app with non-sensitive text
    assert ch.add("normal paragraph", source_app="winword.exe") is True
    assert len(ch.items()) == 1


def test_clipboard_pattern_filtering(tmp_path):
    storage = tmp_path / "clip.json"
    ch = ClipboardHistory(storage_path=storage)

    # Adding a token or password pattern must be rejected
    token_str = "gh" + "p_" + "myfaketoken1234567890abcdefghijklmn"
    assert ch.add(token_str) is False
    assert ch.add("x9#mK$2vL!8wQ&4z") is False
    assert len(ch.items()) == 0

    # Can be accepted if ignore_passwords=False
    assert ch.add("x9#mK$2vL!8wQ&4z", ignore_passwords=False) is True
    assert len(ch.items()) == 1


def test_clipboard_auto_expiration(tmp_path):
    storage = tmp_path / "clip.json"
    ch = ClipboardHistory(storage_path=storage)

    ch.add("fresh item 1")
    ch.add("fresh item 2")
    ch.add("old item to expire")
    ch.add("pinned old item")
    ch.toggle_pin("pinned old item")

    # Artificially age the items by setting timestamps back 10 days
    ten_days_ago = time.time() - (10 * 86400)
    ch._timestamps["old item to expire"] = ten_days_ago
    ch._timestamps["pinned old item"] = ten_days_ago

    # Prune with 7-day retention
    pruned = ch.prune_expired(retention_days=7)
    assert pruned == 1

    items = ch.items()
    assert "old item to expire" not in items
    # Pinned item must be preserved
    assert "pinned old item" in items
    assert "fresh item 1" in items
    assert "fresh item 2" in items

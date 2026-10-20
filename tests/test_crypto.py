"""Tests for DPAPI credential encryption, decryption, and migration."""

from __future__ import annotations

import logging

from ravan.core.config import Config, config_from_dict, config_to_dict
from ravan.core.crypto import protect_secret, unprotect_secret


def test_crypto_round_trip():
    plain = "test_secure_sync_token_987654321"
    cipher = protect_secret(plain)

    assert cipher != plain
    assert cipher.startswith("dpapi:") or cipher.startswith("mock-dpapi:")

    decrypted, was_migrated = unprotect_secret(cipher)
    assert decrypted == plain
    assert was_migrated is False


def test_crypto_empty_and_idempotent():
    assert protect_secret("") == ""
    assert unprotect_secret("")[0] == ""

    # Protecting already encrypted string should be idempotent
    cipher = protect_secret("secret_token")
    assert protect_secret(cipher) == cipher


def test_crypto_plaintext_migration(caplog):
    caplog.set_level(logging.INFO)
    legacy_plain = "legacy_unencrypted_token_12345"

    decrypted, was_migrated = unprotect_secret(legacy_plain)
    assert decrypted == legacy_plain
    assert was_migrated is True


def test_config_dpapi_integration():
    cfg = Config()
    cfg.gist_token = "dummy_sync_token_12345"
    cfg.webdav_password = "my_strong_webdav_password"

    # Serializing to dict (what gets saved to config.json) must not expose plaintext tokens
    d = config_to_dict(cfg)
    assert d["gist_token"] != "dummy_sync_token_12345"
    assert d["gist_token"].startswith(("wincred:", "dpapi:", "mock-dpapi:"))
    assert d["webdav_password"] != "my_strong_webdav_password"
    assert d["webdav_password"].startswith(("wincred:", "dpapi:", "mock-dpapi:"))

    # Loading dict back must resolve tokens into memory
    loaded_cfg = config_from_dict(d)
    assert loaded_cfg.gist_token == "dummy_sync_token_12345"
    assert loaded_cfg.webdav_password == "my_strong_webdav_password"


def test_config_plaintext_token_auto_migration(caplog):
    caplog.set_level(logging.INFO)
    legacy_dict = {
        "gist_token": "old_plaintext_token_12345",
        "webdav_password": "old_plaintext_password",
    }
    cfg = config_from_dict(legacy_dict)
    assert cfg.gist_token == "old_plaintext_token_12345"
    assert cfg.webdav_password == "old_plaintext_password"
    assert any("Migrated credentials" in r.message for r in caplog.records)


def test_wincred_direct_roundtrip():
    from ravan.core.crypto import delete_credential, get_credential, save_credential

    target = "RavaanTest/DirectCredential"
    secret = "secret_token_val_456"

    # Save
    ok = save_credential(target, secret)
    assert ok is True

    # Read back
    retrieved = get_credential(target)
    assert retrieved == secret

    # Delete
    del_ok = delete_credential(target)
    assert del_ok is True
    assert get_credential(target) == ""

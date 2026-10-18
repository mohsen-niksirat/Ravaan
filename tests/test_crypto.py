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

    # Serializing to dict (what gets saved to config.json) must encrypt tokens
    d = config_to_dict(cfg)
    assert d["gist_token"] != "dummy_sync_token_12345"
    assert d["gist_token"].startswith("dpapi:") or d["gist_token"].startswith("mock-dpapi:")
    assert d["webdav_password"] != "my_strong_webdav_password"
    assert d["webdav_password"].startswith("dpapi:") or d["webdav_password"].startswith("mock-dpapi:")

    # Loading dict back must decrypt tokens into memory
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
    assert any("Migrated plaintext sync credentials" in r.message for r in caplog.records)

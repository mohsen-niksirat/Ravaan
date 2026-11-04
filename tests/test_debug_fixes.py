"""Regression tests for bugs found and fixed in the 2026-11-05 debug pass.

Areas covered here were green in the existing suite (550 tests passed) while the
bugs lived in integration gaps: keystroke-delivery accounting, config robustness,
credential-target allowlisting, and clipboard privacy filters.

Known seam gap (documented, not testable here): the off-by-one accounting between
the delivered key and replace_last_n_with() call sites in ravan/ui/key_handler.py
has no unit seam — it only manifests against a real Windows input queue
(WH_KEYBOARD_LL passes the physical key to the target app while RavanApp also
processes it). Verified experimentally during diagnosis; the call sites now
follow the same "+1 delivered char" convention as RavanApp._replace_word.
"""

from __future__ import annotations

import sys
import time
from types import SimpleNamespace

import pytest

from ravan.core.calc import calculate, extract_math_query, safe_eval
from ravan.core.cliphistory import is_sensitive_pattern
from ravan.core.config import config_from_dict
from ravan.core.normalizer import normalize_persian, normalize_persian_punctuation

# ── Inline calculator ────────────────────────────────────────────────────────


def test_calc_query_span_counts_internal_space():
    # '12000 =t' consumes 8 characters (space before '=' included) — previously 7,
    # which left a stray leading digit in the target buffer.
    assert extract_math_query("12000 =t")[3] == 8
    # No-space form keeps its original span.
    assert extract_math_query("15000=t")[3] == 7
    assert extract_math_query("12+3 =2")[3] == 7
    assert extract_math_query("12+3=2")[3] == 6


def test_calc_rejects_nonfinite_results():
    # Huge literals and overflow must not leak inf/nan into user text.
    assert calculate("1e999") is None
    assert calculate("1e999-1e999") is None
    assert safe_eval("1e999") is None
    # Sanity: normal arithmetic is unaffected.
    assert calculate("125*8") == "1000"


# ── Persian normalizer ───────────────────────────────────────────────────────


def test_smart_quotes_pair_per_segment():
    # Quote pairing must not leak across neighbouring segments: the closing quote
    # of a Latin segment must not pair with the opener of a Persian one.
    text = '"hello" و "سلام"'
    assert normalize_persian_punctuation(text) == '"hello" و «سلام»'
    # Plain Persian quoting is still converted.
    assert normalize_persian_punctuation('"سلام"') == "«سلام»"


def test_dot_spacing_preserves_filenames_and_acronyms():
    assert "test.py" in normalize_persian("فایل test.py را باز کن")
    assert "U.S.A" in normalize_persian("در U.S.A")
    # Persian sentence dots still gain the following space.
    assert normalize_persian("سلام.دوست") == "سلام. دوست"
    # Decimals are untouched.
    assert "3.11" in normalize_persian("نسخه 3.11")


# ── Config robustness & credential allowlist ────────────────────────────────


def test_prediction_opacity_bad_value_keeps_config():
    raw = {
        "prediction_opacity": "oops",
        "snippets": [{"trigger": ";em", "replacement": "user@example.com"}],
    }
    cfg = config_from_dict(raw)
    assert cfg.prediction_opacity == 0.95
    assert len(cfg.snippets) == 1  # one bad field must not reset the whole config


def test_wincred_targets_are_allowlisted(monkeypatch):
    import ravan.core.crypto as crypto

    requested: list[str] = []

    def fake_get_credential(target: str) -> str | None:
        requested.append(target)
        return "SECRET-X"

    monkeypatch.setattr(crypto, "get_credential", fake_get_credential)

    # A config naming an arbitrary Credential Manager target must be rerouted to
    # Ravaan's own target — never read a third-party entry.
    cfg = config_from_dict({"gist_token": "wincred:SomeOtherApp"})
    assert cfg.gist_token == "SECRET-X"
    assert requested[0] == crypto.CRED_TARGET_GIST

    # The app's own targets remain readable (webdav/gist lookup defaults are
    # also queried, so check membership for the AI target).
    requested.clear()
    cfg = config_from_dict({"ai_api_key": f"wincred:{crypto.CRED_TARGET_AI}"})
    assert cfg.ai_api_key == "SECRET-X"
    assert crypto.CRED_TARGET_AI in requested


# ── Clipboard privacy filter ─────────────────────────────────────────────────


def test_private_key_patterns_detected():
    assert is_sensitive_pattern("-----BEGIN OPENSSH PRIVATE KEY-----b3BlbnNzaC1rZXk=")
    assert is_sensitive_pattern("-----BEGIN DSA PRIVATE KEY-----")
    assert is_sensitive_pattern("-----BEGIN PGP PRIVATE KEY BLOCK-----")
    assert is_sensitive_pattern("-----BEGIN RSA PRIVATE KEY-----")
    assert is_sensitive_pattern("-----BEGIN EC PRIVATE KEY-----")


# ── Deep-link hardening ──────────────────────────────────────────────────────


@pytest.mark.skipif(sys.platform != "win32", reason="win32 protocol module")
def test_protocol_url_param_limit_never_throws():
    from ravan.platform.protocol import parse_protocol_url

    flooded = "ravan://settings?" + "&".join(f"p{i}=v" for i in range(25))
    res = parse_protocol_url(flooded)
    assert res["valid"] is False
    # Normal deep links still parse.
    ok = parse_protocol_url("ravan://settings?tab=sync")
    assert ok["valid"] is True and ok["params"]["tab"] == "sync"


# ── Language chip popup timing ───────────────────────────────────────────────


@pytest.mark.skipif(sys.platform != "win32", reason="requires win32 UI stack")
def test_show_lang_indicator_stamps_popup_timer(monkeypatch):
    import ravan.ui.app_actions as actions_mod

    class FakeLang:
        tag = "en"
        is_persian = False
        hkl = 0x0409

    class FakeCaret:
        x = 10
        y = 10
        height = 20

    class FakeOverlay:
        def show_language(self, *args, **kwargs):
            pass

    class App(actions_mod.AppActionsMixin):
        cfg = SimpleNamespace(translit_enabled=False)
        overlay = FakeOverlay()

    monkeypatch.setattr(actions_mod, "current_language", lambda: FakeLang())
    monkeypatch.setattr(actions_mod, "language_label", lambda lang: "English")
    monkeypatch.setattr(actions_mod, "get_caret_rect", lambda: FakeCaret())

    app = App()
    app._popup_shown_at = time.monotonic() - 999  # stale stamp (pre-fix initial state)
    app._show_lang_indicator()
    # The chip must reset the popup timer, or _maybe_timeout_popup hides it
    # immediately on the next main-loop tick.
    assert app._popup_shown_at > time.monotonic() - 5


@pytest.mark.skipif(sys.platform != "win32", reason="requires win32 UI stack")
def test_timeout_popup_respects_fresh_stamp():
    import ravan.ui.app_polling as polling_mod

    class FakeOverlay:
        visible = True
        hidden = False

        def hide(self):
            self.hidden = True

    class App(polling_mod.AppPollingMixin):
        overlay = FakeOverlay()
        cfg = SimpleNamespace(popup_timeout_ms=4000)

    app = App()
    app._popup_shown_at = time.monotonic()  # freshly shown
    app._maybe_timeout_popup()
    assert app.overlay.hidden is False

    app._popup_shown_at = time.monotonic() - 10  # stale beyond timeout
    app._maybe_timeout_popup()
    assert app.overlay.hidden is True

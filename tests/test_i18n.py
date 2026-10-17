"""Unit tests for the i18n localization engine (ravan.core.i18n)."""

from unittest.mock import MagicMock, patch

from ravan.core.i18n import (
    detect_system_locale,
    get_locale,
    is_rtl,
    load_locale,
    set_locale,
    t,
)


def test_get_and_set_locale():
    orig = get_locale()
    try:
        set_locale("fa")
        assert get_locale() == "fa"
        assert is_rtl() is True

        set_locale("en")
        assert get_locale() == "en"
        assert is_rtl() is False
    finally:
        set_locale(orig)


def test_t_lookup_en_and_fa():
    orig = get_locale()
    try:
        set_locale("en")
        assert t("app_name") == "Ravaan"
        assert t("tray.quit") == "Quit"

        set_locale("fa")
        assert t("app_name") == "روان"
        assert t("tray.quit") == "خروج"
    finally:
        set_locale(orig)


def test_t_fallback():
    orig = get_locale()
    try:
        set_locale("en")
        assert t("non_existent.nested.key", "Default Fallback") == "Default Fallback"
        assert t("non_existent_key") == "non_existent_key"
    finally:
        set_locale(orig)


def test_t_format_parameters():
    orig = get_locale()
    try:
        set_locale("en")
        msg = t("notifications.autocorrect_undone", "Reverted to '{orig}'", orig="سلام")
        assert "سلام" in msg

        set_locale("fa")
        msg_fa = t("notifications.autocorrect_undone", orig="سلام")
        assert "سلام" in msg_fa
    finally:
        set_locale(orig)


def test_detect_system_locale_persian():
    mock_windll = MagicMock()
    mock_windll.kernel32.GetUserDefaultUILanguage.return_value = 0x0429  # Persian LCID
    with patch("ctypes.windll", mock_windll, create=True):
        assert detect_system_locale() == "fa"


def test_detect_system_locale_english():
    mock_windll = MagicMock()
    mock_windll.kernel32.GetUserDefaultUILanguage.return_value = 0x0409  # English (US)
    with patch("ctypes.windll", mock_windll, create=True):
        assert detect_system_locale() == "en"


def test_detect_system_locale_exception():
    with patch("ctypes.windll", side_effect=AttributeError, create=True):
        assert detect_system_locale() == "en"


def test_load_locale_nonexistent():
    catalog = load_locale("nonexistent_lang_code_xyz")
    assert catalog == {}


def test_catalogs_parity():
    """Verify that both en.json and fa.json have identical nested key structures."""
    en_cat = load_locale("en")
    fa_cat = load_locale("fa")

    def get_all_keys(d: dict, prefix: str = "") -> set[str]:
        keys = set()
        for k, v in d.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                keys.update(get_all_keys(v, full_key))
            else:
                keys.add(full_key)
        return keys

    en_keys = get_all_keys(en_cat)
    fa_keys = get_all_keys(fa_cat)

    missing_in_fa = en_keys - fa_keys
    missing_in_en = fa_keys - en_keys
    assert not missing_in_fa, f"Keys in en.json missing in fa.json: {missing_in_fa}"
    assert not missing_in_en, f"Keys in fa.json missing in en.json: {missing_in_en}"

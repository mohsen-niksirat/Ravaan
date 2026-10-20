"""Unit tests for Phase 4: Autocorrect & Language Intelligence."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from ravan.core.config import Config
from ravan.core.dict import DictEntry, Dictionary, Language
from ravan.core.normalizer import normalize_persian_typos
from ravan.core.predictor import DictPredictor
from ravan.ui.app import RavanApp


def test_persian_confusable_typos_normalization():
    # Test normalization of common typos
    assert "دانشگاهی" in normalize_persian_typos("دانشگاهي")  # ي -> ی
    assert "حرکت" in normalize_persian_typos("حركت")        # ك -> ک
    assert "نقطه" in normalize_persian_typos("نقطة")        # ة -> ه
    assert "حرکت" in normalize_persian_typos("حركة")        # ة -> ت


def test_bilingual_awareness():
    en_dict = Dictionary(
        [
            DictEntry("the", 1, frequency=100000),
            DictEntry("hello", 2, frequency=50000),
        ],
        Language.ENGLISH,
    )
    fa_dict = Dictionary(
        [
            DictEntry("سلام", 1, frequency=100000),
            DictEntry("دانشگاه", 2, frequency=50000),
        ],
        Language.PERSIAN,
    )
    predictor = DictPredictor(english=en_dict, persian=fa_dict)

    # 1. When Persian layout is active, English typos must NEVER be autocorrected
    cand_fa_mode = predictor.correct("teh", lang="fa")
    assert cand_fa_mode is None

    # 2. When English layout is active, English typos ARE autocorrected
    cand_en_mode = predictor.correct("teh", lang="en")
    assert cand_en_mode is not None
    assert cand_en_mode.text == "the"

    # 3. When English layout is active, Persian typos must NEVER be autocorrected
    cand_en_fa_word = predictor.correct("سلان", lang="en")
    assert cand_en_fa_word is None

    # 4. When Persian layout is active, Persian typos ARE autocorrected
    cand_fa_word = predictor.correct("سلان", lang="fa")
    assert cand_fa_word is not None
    assert cand_fa_word.text == "سلام"


def test_persian_confusable_autocorrect():
    fa_dict = Dictionary(
        [
            DictEntry("دانشگاهی", 10, frequency=20000),
            DictEntry("حرکت", 15, frequency=18000),
            DictEntry("نقطه", 25, frequency=12000),
        ],
        Language.PERSIAN,
    )
    predictor = DictPredictor(english=None, persian=fa_dict)

    # Arabic Yeh -> Persian Yeh
    c1 = predictor.correct("دانشگاهي", lang="fa")
    assert c1 is not None
    assert c1.text == "دانشگاهی"

    # Arabic Kaf -> Persian Kaf
    c2 = predictor.correct("حركت", lang="fa")
    assert c2 is not None
    assert c2.text == "حرکت"

    # Teh Marbuta -> Heh
    c3 = predictor.correct("نقطة", lang="fa")
    assert c3 is not None
    assert c3.text == "نقطه"


def test_frequency_weighted_autocorrect():
    # Candidate A has low frequency, Candidate B has very high frequency
    en_dict = Dictionary(
        [
            DictEntry("the", 1, frequency=1000000),
            DictEntry("thy", 3000, frequency=50),
        ],
        Language.ENGLISH,
    )
    predictor = DictPredictor(english=en_dict, persian=None)

    # "th" might be close to both, but "the" has massive frequency advantage
    c = predictor.correct("thw", lang="en")
    assert c is not None
    assert c.text == "the"


def test_undo_autocorrect_flow():
    app = RavanApp(overlay=MagicMock())
    # Simulate an autocorrect having taken place: user typed "teh", got "the "
    app._last_autocorrect = ("teh", "the", time.monotonic(), " ")

    with patch("ravan.ui.app.replace_last_n_with") as mock_replace:
        ok = app._undo_last_autocorrect()
        assert ok is True
        # delete_len = len("the") + len(" ") = 4, replace_text = "teh "
        mock_replace.assert_called_once_with(4, "teh ")
        assert app._last_autocorrect is None


def test_config_undo_hotkey_persistence():
    cfg = Config()
    assert cfg.undo_autocorrect_hotkey.key == "Z"
    assert "Ctrl" in cfg.undo_autocorrect_hotkey.modifiers
    assert cfg.fix_punctuation_spacing is True


def test_autocorrect_token_screening_never_touches_special_tokens():
    from ravan.core.predictor import is_safe_autocorrect_token

    en_dict = Dictionary.english()
    fa_dict = Dictionary.persian()
    predictor = DictPredictor(english=en_dict, persian=fa_dict, autocorrect_mode="safe")

    # Tokens with digits
    digits_tokens = ["v2", "win32", "x86", "100m", "3x", "۱۰درصد", "۱۰۰متر", "۳راه", "5تومان", "h2o"]
    for tok in digits_tokens:
        assert not is_safe_autocorrect_token(tok), f"Expected {tok} to be screened out"
        assert predictor.correct(tok, lang="en") is None
        assert predictor.correct(tok, lang="fa") is None

    # URLs and web domains
    url_tokens = ["http://example.com", "https://google.com", "www.site.ir", "t.me/channel", "github.com"]
    for tok in url_tokens:
        assert not is_safe_autocorrect_token(tok), f"Expected URL {tok} to be screened out"
        assert predictor.correct(tok, lang="en") is None
        assert predictor.correct(tok, lang="fa") is None

    # Emails and @mentions
    email_tokens = ["user@example.com", "info@site.org", "@username", "@admin", "@mohammad"]
    for tok in email_tokens:
        assert not is_safe_autocorrect_token(tok), f"Expected email/mention {tok} to be screened out"
        assert predictor.correct(tok, lang="en") is None
        assert predictor.correct(tok, lang="fa") is None

    # Hashtags
    hashtag_tokens = ["#iran", "#خبر", "#python", "#coding"]
    for tok in hashtag_tokens:
        assert not is_safe_autocorrect_token(tok), f"Expected hashtag {tok} to be screened out"
        assert predictor.correct(tok, lang="en") is None
        assert predictor.correct(tok, lang="fa") is None

    # File paths and filenames with extensions
    file_tokens = [r"C:\Windows\System32", "/usr/bin/python", "config.json", "main.py", "document.pdf", "data.txt"]
    for tok in file_tokens:
        assert not is_safe_autocorrect_token(tok), f"Expected file path {tok} to be screened out"
        assert predictor.correct(tok, lang="en") is None
        assert predictor.correct(tok, lang="fa") is None

    # Code identifiers and mixed syntax
    code_tokens = ["snake_case", "__init__", "my_var", "$variable", "jQuery", "camelCase", "XmlParser", "getById"]
    for tok in code_tokens:
        assert not is_safe_autocorrect_token(tok), f"Expected code token {tok} to be screened out"
        assert predictor.correct(tok, lang="en") is None
        assert predictor.correct(tok, lang="fa") is None

    # Acronyms
    acronym_tokens = ["API", "SDK", "URL", "HTML", "USA", "CSS", "RAM"]
    for tok in acronym_tokens:
        assert not is_safe_autocorrect_token(tok), f"Expected acronym {tok} to be screened out"
        assert predictor.correct(tok, lang="en") is None


def test_autocorrect_safe_defaults_valid_words():
    en_dict = Dictionary.english()
    fa_dict = Dictionary.persian()
    predictor = DictPredictor(english=en_dict, persian=fa_dict, autocorrect_mode="safe")

    # Valid words in English dictionary must never be changed
    valid_en = ["the", "information", "computer", "hello", "keyboard", "window", "language"]
    for w in valid_en:
        assert predictor.correct(w, lang="en") is None

    # Valid words in Persian dictionary must never be changed
    valid_fa = ["سلام", "دانشگاه", "کتاب", "اطلاعات", "برنامه", "توسعه", "زندگی", "ممنون"]
    for w in valid_fa:
        assert predictor.correct(w, lang="fa") is None

    # Real typos ARE corrected
    c1 = predictor.correct("teh", lang="en")
    assert c1 is not None and c1.text == "the"

    c2 = predictor.correct("دانشگاهي", lang="fa")
    assert c2 is not None and c2.text == "دانشگاهی"


from ravan.core.config import Config
from ravan.core.zwnj import (
    ZWNJ,
    is_prefix_exception,
    is_zwnj_prefix,
    normalize_zwnj,
    should_attach_suffix,
)
from ravan.ui.app import RavanApp


def test_zwnj_prefix_check():
    assert is_zwnj_prefix("می") is True
    assert is_zwnj_prefix("نمی") is True
    assert is_zwnj_prefix("بی") is True
    assert is_zwnj_prefix("کتاب") is False


def test_zwnj_prefix_exceptions():
    assert is_prefix_exception("مینا") is True
    assert is_prefix_exception("بیمار") is True
    assert is_prefix_exception("بیست") is True
    assert is_prefix_exception("میروم") is False


def test_zwnj_suffix_check():
    assert should_attach_suffix("کتاب", "ها") is True
    assert should_attach_suffix("کتاب", "هایم") is True
    assert should_attach_suffix("دوست", "هایمان") is True
    assert should_attach_suffix("بزرگ", "ترین") is True
    assert should_attach_suffix("سریع", "تر") is True
    assert should_attach_suffix("سریع", "ترش") is True
    assert should_attach_suffix("خانه", "ام") is True
    assert should_attach_suffix("خانه", "ای") is True
    assert should_attach_suffix("خانه", "ایم") is True
    assert should_attach_suffix("خانه", "اید") is True
    assert should_attach_suffix("خانه", "اند") is True
    assert should_attach_suffix("خانه", "تان") is True
    assert should_attach_suffix("خانه", "شان") is True
    assert should_attach_suffix("خانه", "مان") is True
    assert should_attach_suffix("خانه", "ی") is True

    # Vowel endings (ا, و) attach personal endings
    assert should_attach_suffix("دانشجو", "ام") is True
    assert should_attach_suffix("رویا", "یم") is False
    assert should_attach_suffix("دانشجو", "اید") is True

    # Word not ending in silent Heh/vowel should not attach "ام" as ZWNJ
    assert should_attach_suffix("کتاب", "ام") is False


def test_zwnj_suffix_exceptions():
    assert should_attach_suffix("روز", "نامه") is False
    assert should_attach_suffix("شاه", "نامه") is False


def test_normalize_zwnj_text():
    raw = (
        "من می روم و کتاب هایم را به بزرگ ترین خانه ام می برم "
        "و نامه ی او را می خوانم و دوستان مان را می بینیم."
    )
    normalized = normalize_zwnj(raw)
    assert f"می{ZWNJ}روم" in normalized
    assert f"کتاب{ZWNJ}هایم" in normalized
    assert f"بزرگ{ZWNJ}ترین" in normalized
    assert f"خانه{ZWNJ}ام" in normalized
    assert f"نامه{ZWNJ}ی" in normalized
    assert f"دوستان{ZWNJ}مان" not in normalized  # دوستان does not end in silent Heh
    assert f"خانه{ZWNJ}مان" in normalize_zwnj("خانه مان")


def test_normalize_zwnj_compounds():
    raw = "ما درباره سیستم عامل و پیش فرض های برنامه نویسی به گفت و گو نشستیم."
    normalized = normalize_zwnj(raw)
    assert f"سیستم{ZWNJ}عامل" in normalized
    assert f"پیش{ZWNJ}فرض" in normalized
    assert f"برنامه{ZWNJ}نویسی" in normalized
    assert f"گفت{ZWNJ}وگو" in normalized


def test_normalize_zwnj_cleanup():
    # Double ZWNJ cleaned to single
    double_raw = f"کتاب{ZWNJ}{ZWNJ}ها"
    assert normalize_zwnj(double_raw) == f"کتاب{ZWNJ}ها"

    # Misplaced ZWNJ around spaces cleaned
    space_raw = f"کتاب {ZWNJ} ها"
    assert normalize_zwnj(space_raw) == f"کتاب{ZWNJ}ها"

    # ZWNJ before punctuation cleaned
    punct_raw = f"سلام{ZWNJ}، حال شما؟"
    assert normalize_zwnj(punct_raw) == "سلام، حال شما؟"


class MockOverlay:
    def __init__(self) -> None:
        self.predicting = False
        self.clipboard_open = False
        self.active_popup = False
    def hide(self) -> None: pass
    def destroy(self) -> None: pass
    def tick(self) -> None: pass


def test_app_suffix_zwnj_attachment():
    cfg = Config()
    cfg.auto_zwnj_enabled = True
    app = RavanApp(cfg, overlay=MockOverlay())
    try:
        # Simulate typing "کتاب ها "
        for ch in "کتاب ها ":
            app.journal.push(ch)

        # Trigger suffix attachment
        res = app._maybe_attach_suffix_zwnj("ها")
        assert res is True
        assert app.journal.text() == f"کتاب{ZWNJ}ها "
    finally:
        app.stop()

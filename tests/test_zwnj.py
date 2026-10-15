from ravan.core.zwnj import ZWNJ, is_zwnj_prefix, normalize_zwnj, should_attach_suffix
from ravan.core.config import Config
from ravan.ui.app import RavanApp


def test_zwnj_prefix_check():
    assert is_zwnj_prefix("می") is True
    assert is_zwnj_prefix("نمی") is True
    assert is_zwnj_prefix("بی") is True
    assert is_zwnj_prefix("کتاب") is False


def test_zwnj_suffix_check():
    assert should_attach_suffix("کتاب", "ها") is True
    assert should_attach_suffix("بزرگ", "ترین") is True
    assert should_attach_suffix("خانه", "ام") is True
    # Word not ending in silent Heh should not attach "ام" as ZWNJ
    assert should_attach_suffix("کتاب", "ام") is False


def test_normalize_zwnj_text():
    raw = "من می روم و کتاب ها را به بزرگ ترین خانه ام می برم"
    normalized = normalize_zwnj(raw)
    assert f"می{ZWNJ}روم" in normalized
    assert f"کتاب{ZWNJ}ها" in normalized
    assert f"بزرگ{ZWNJ}ترین" in normalized
    assert f"خانه{ZWNJ}ام" in normalized


class MockOverlay:
    def __init__(self) -> None:
        self.predicting = False
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

from unittest.mock import MagicMock, patch

from ravan.core.config import Config
from ravan.ui.app import RavanApp


class MockOverlay:
    def __init__(self) -> None:
        self.predicting = False
        self.clipboard_open = False
        self.active_popup = False
    def hide(self) -> None: pass
    def destroy(self) -> None: pass
    def tick(self) -> None: pass


def test_clean_clipboard_action():
    cfg = Config()
    app = RavanApp(cfg, overlay=MockOverlay())
    app._show_toast = MagicMock()
    app.tray = MagicMock()

    raw_text = 'من می روم به کتابخانه ، تا کتاب هایم را بخوانم ? آیا می آیید ؟ "بسیار خوب" ...'

    try:
        with (
            patch("ravan.platform.clipboard.get_clipboard_text", return_value=raw_text),
            patch("ravan.platform.clipboard.set_clipboard_text") as mock_set,
        ):
            ok = app._clean_clipboard_text()
            assert ok is True
            mock_set.assert_called_once()
            cleaned = mock_set.call_args[0][0]
            # Verify ZWNJ
            assert "\u200c" in cleaned
            assert "می‌روم" in cleaned
            assert "کتاب‌هایم" in cleaned
            # Verify Persian comma and question mark
            assert "،" in cleaned
            assert "؟" in cleaned
            # Verify smart quotes and ellipsis
            assert "«بسیار خوب»" in cleaned
            assert "…" in cleaned
            # Verify toast was shown
            app._show_toast.assert_called_with("متن کلیپ‌بورد پاک‌سازی و استاندارد شد")

        # Test already clean clipboard
        with (
            patch("ravan.platform.clipboard.get_clipboard_text", return_value=cleaned),
            patch("ravan.platform.clipboard.set_clipboard_text") as mock_set_noop,
        ):
            ok2 = app._clean_clipboard_text()
            assert ok2 is True
            mock_set_noop.assert_not_called()
            app._show_toast.assert_called_with("متن کلیپ‌بورد از قبل استاندارد است")

        # Test empty clipboard
        with (
            patch("ravan.platform.clipboard.get_clipboard_text", return_value="   "),
            patch("ravan.platform.clipboard.set_clipboard_text") as mock_set_empty,
        ):
            ok3 = app._clean_clipboard_text()
            assert ok3 is False
            mock_set_empty.assert_not_called()
            app._show_toast.assert_called_with("کلیپ‌بورد خالی است")
    finally:
        app.stop()

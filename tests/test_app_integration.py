from ravan.core.config import Config, Snippet
from ravan.ui.app import RavanApp


class MockOverlay:
    def __init__(self) -> None:
        self.predicting = False
        self.clipboard_open = False
        self.active_popup = False
    def hide(self) -> None: pass
    def destroy(self) -> None: pass
    def tick(self) -> None: pass


def test_app_journal_and_word_completion():
    cfg = Config()
    cfg.snippets.append(Snippet(trigger="@@", replacement="me@test.com"))
    app = RavanApp(cfg, overlay=MockOverlay())

    try:
        # Simulate typing 't', 'e', 'h', ' '
        for ch in "teh":
            app.journal.push(ch)

        # Word boundary triggered with space
        word = app.journal.last_word(allow_trailing_spaces=False)
        assert word == "teh"
        # Autocorrect should correct teh -> the
        handled = app._on_word_completed(word, delimiter=" ")
        assert handled is True
        # Journal should now have "the "
        assert app.journal.text() == "the "

        # Test snippet completion @@ + space
        app.journal.clear()
        for ch in "@@":
            app.journal.push(ch)
        word = app.journal.last_word(allow_trailing_spaces=False)
        assert word == "@@"
        handled = app._on_word_completed(word, delimiter=" ")
        assert handled is True
        assert app.journal.text() == "me@test.com "
    finally:
        app.stop()


def test_app_convert_last_word_with_trailing_space():
    cfg = Config()
    app = RavanApp(cfg, overlay=MockOverlay())
    try:
        # User typed "o,vn " (with trailing space)
        for ch in "o,vn ":
            app.journal.push(ch)

        app._convert_last_word()
        # Should be converted to "خورد " preserving the trailing space
        assert app.journal.text() == "خورد "
    finally:
        app.stop()

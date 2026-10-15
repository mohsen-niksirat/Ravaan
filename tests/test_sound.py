import sys
from unittest.mock import MagicMock

from ravan.platform.sound import play_beep_async, play_layout_switch_sound


def test_play_layout_switch_sound_runs_without_error(monkeypatch):
    mock_beep = MagicMock()
    if sys.platform == "win32":
        monkeypatch.setattr("winsound.Beep", mock_beep)

    play_layout_switch_sound(is_persian=True)
    play_layout_switch_sound(is_persian=False)


def test_play_beep_async(monkeypatch):
    mock_beep = MagicMock()
    if sys.platform == "win32":
        monkeypatch.setattr("winsound.Beep", mock_beep)

    play_beep_async(800, 20)

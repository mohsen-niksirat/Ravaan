"""Subtle audio feedback on keyboard events and layout switches."""

from __future__ import annotations

import logging
import sys
import threading

log = logging.getLogger(__name__)


def play_beep_async(freq: int, duration_ms: int) -> None:
    """Play a non-blocking tone on Windows."""
    if sys.platform != "win32":
        return

    def _beep() -> None:
        try:
            import winsound

            winsound.Beep(freq, duration_ms)
        except Exception as e:
            log.debug("winsound.Beep failed: %s", e)

    threading.Thread(target=_beep, daemon=True).start()


def play_layout_switch_sound(is_persian: bool) -> None:
    """Subtle audio cue when switching keyboard layout:

    - Persian: warm, lower tone (650 Hz, 35 ms)
    - English: crisp, higher tone (1100 Hz, 25 ms)
    """
    freq = 650 if is_persian else 1100
    duration = 35 if is_persian else 25
    play_beep_async(freq, duration)

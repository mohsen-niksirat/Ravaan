"""Macro recorder and player for keystroke automation (M23).

Records sequences of keystrokes with relative timings, serializes
into snippet triggers, and replays keystrokes safely.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

from ravan.platform import winapi as w
from ravan.platform.inject import inject_text

log = logging.getLogger(__name__)

MACRO_PREFIX = "__macro__:"


class MacroRecorder:
    """Records keystrokes until Esc is pressed."""

    def __init__(self) -> None:
        self._recording: bool = False
        self._events: list[dict[str, Any]] = []
        self._last_time: float = 0.0

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        self._recording = True
        self._events = []
        self._last_time = time.monotonic()
        log.info("Macro recording started")

    def record(self, vk: int, char: str = "") -> None:
        if not self._recording:
            return
        # Do not record the final Escape key
        if vk == w.VK_ESCAPE:
            return

        now = time.monotonic()
        dt_ms = (now - self._last_time) * 1000.0 if self._last_time > 0 else 0.0
        # Cap initial and long pauses to 1.0 second max
        capped_dt_ms = min(max(dt_ms, 0.0), 1000.0)
        self._last_time = now

        self._events.append({
            "vk": vk,
            "char": char,
            "delay_ms": round(capped_dt_ms, 1),
        })

    def stop(self) -> list[dict[str, Any]]:
        self._recording = False
        events = list(self._events)
        self._events = []
        log.info("Macro recording stopped with %d events", len(events))
        return events


def serialize_macro(events: list[dict[str, Any]], preserve_timing: bool = False) -> str:
    """Encode macro events and timing setting into snippet replacement string."""
    payload = {
        "v": 1,
        "preserve_timing": bool(preserve_timing),
        "events": events,
    }
    return f"{MACRO_PREFIX}{json.dumps(payload, ensure_ascii=False)}"


def is_macro_snippet(replacement: str) -> bool:
    """Return True if the snippet replacement contains a macro payload."""
    return replacement.startswith(MACRO_PREFIX)


def parse_macro_snippet(replacement: str) -> dict[str, Any] | None:
    """Parse macro payload from snippet replacement string."""
    if not is_macro_snippet(replacement):
        return None
    raw = replacement[len(MACRO_PREFIX) :]
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "events" in data:
            return data
    except Exception as exc:
        log.warning("Corrupt macro snippet JSON: %s", exc)
    return None


class MacroPlayer:
    """Replays recorded keystroke sequences."""

    @staticmethod
    def play(
        macro_data: dict[str, Any],
        on_suppress: Any = None,
    ) -> None:
        """Play back recorded macro events in a background thread."""
        events = macro_data.get("events", [])
        preserve_timing = bool(macro_data.get("preserve_timing", False))
        if not events:
            return

        def _run() -> None:
            # Estimate duration for input hook suppression
            total_delay = (
                sum(min(e.get("delay_ms", 10.0), 500.0) for e in events) / 1000.0
                if preserve_timing
                else len(events) * 0.015
            )
            if callable(on_suppress):
                on_suppress(total_delay + 0.3)

            from ravan.platform.inject import _vk_input

            for ev in events:
                vk = int(ev.get("vk", 0))
                char = str(ev.get("char", ""))
                delay_ms = float(ev.get("delay_ms", 0.0))

                if preserve_timing and delay_ms > 0:
                    time.sleep(min(delay_ms / 1000.0, 0.5))
                else:
                    time.sleep(0.005)

                if char and char.isprintable() and char not in ("\r", "\n", "\t"):
                    inject_text(char)
                elif vk in (w.VK_RETURN, w.VK_TAB, w.VK_SPACE, w.VK_BACK):
                    inputs = [_vk_input(vk, False), _vk_input(vk, True)]
                    arr = (w.INPUT * len(inputs))(*inputs)
                    w.user32.SendInput(len(inputs), arr, ctypes.sizeof(w.INPUT))
                elif char:
                    inject_text(char)

        import ctypes

        threading.Thread(target=_run, name="ravan-macro-player", daemon=True).start()

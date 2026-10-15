"""Clipboard history ring buffer (سابقه کلیپ‌بورد)."""

from __future__ import annotations

from collections import deque


class ClipboardHistory:
    def __init__(self, maxlen: int = 25) -> None:
        self.maxlen = maxlen
        self._items: deque[str] = deque(maxlen=maxlen)
        self._last_seen: str | None = None

    def add(self, text: str | None) -> bool:
        """Add text to history if valid, non-empty, and not a duplicate of top."""
        if not text:
            return False
        stripped = text.strip()
        if not stripped:
            return False
        # Ignore Ravan internal sentinels
        if stripped.startswith("__ravan_"):
            return False
        if stripped == self._last_seen:
            return False

        self._last_seen = stripped
        # Remove if already exists elsewhere in history to bring it to the top
        try:
            self._items.remove(stripped)
        except ValueError:
            pass
        self._items.appendleft(stripped)
        return True

    def items(self) -> list[str]:
        return list(self._items)

    def clear(self) -> None:
        self._items.clear()
        self._last_seen = None

    def __len__(self) -> int:
        return len(self._items)

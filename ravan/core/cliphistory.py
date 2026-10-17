"""Clipboard history ring buffer (سابقه کلیپ‌بورد)."""

from __future__ import annotations

import json
import logging
from collections import deque
from pathlib import Path

log = logging.getLogger(__name__)


class ClipboardHistory:
    def __init__(self, maxlen: int = 50, storage_path: Path | None = None) -> None:
        self.maxlen = maxlen
        self.storage_path = storage_path
        self._items: deque[str] = deque(maxlen=maxlen)
        self._pinned: list[str] = []
        self._last_seen: str | None = None
        if self.storage_path is not None:
            self.load()

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
        self.save()
        return True

    def toggle_pin(self, text: str) -> bool:
        clean = text.strip()
        if clean in self._pinned:
            self._pinned.remove(clean)
            self.save()
            return False
        else:
            self._pinned.append(clean)
            self.save()
            return True

    def is_pinned(self, text: str) -> bool:
        return text.strip() in self._pinned

    def items(self) -> list[str]:
        # Pinned items first, then unpinned
        unpinned = [it for it in self._items if it not in self._pinned]
        return [*self._pinned, *unpinned]

    def clear(self) -> None:
        self._items.clear()
        self._pinned.clear()
        self._last_seen = None
        self.save()

    def __len__(self) -> int:
        return len(self.items())

    def save(self) -> None:
        if self.storage_path is None:
            return
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "pinned": self._pinned,
                "items": list(self._items),
            }
            tmp = self.storage_path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            tmp.replace(self.storage_path)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to save clipboard history: %s", exc)

    def load(self) -> None:
        if self.storage_path is None or not self.storage_path.is_file():
            return
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._pinned = [
                    str(x) for x in data.get("pinned", []) if str(x).strip()
                ]
                loaded_items = [
                    str(x) for x in data.get("items", []) if str(x).strip()
                ]
                self._items.clear()
                for it in reversed(loaded_items[: self.maxlen]):
                    self._items.appendleft(it)
                if self._items:
                    self._last_seen = self._items[0]
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to load clipboard history: %s", exc)

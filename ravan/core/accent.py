"""Quick Accent engine for Persian & Arabic letter variants and numerals."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

ACCENT_VARIANTS: dict[str, list[str]] = {
    # Persian/Arabic letter variants
    "h": ["ه", "ة", "ھ", "هٔ"],
    "ه": ["ه", "ة", "ھ", "هٔ"],
    "y": ["ی", "ي", "ئ", "ى"],
    "ی": ["ی", "ي", "ئ", "ى"],
    "k": ["ک", "ك"],
    "ک": ["ک", "ك"],
    "a": ["ا", "آ", "أ", "إ", "ء", "ٱ"],
    "ا": ["ا", "آ", "أ", "إ", "ء", "ٱ"],
    "w": ["و", "ؤ"],
    "و": ["و", "ؤ"],
    # Space hold -> ZWNJ (نیم‌فاصله)
    " ": ["\u200c"],
    # Digits -> Persian and Eastern Arabic numerals
    "0": ["۰", "٠"],
    "1": ["۱", "١"],
    "2": ["۲", "٢"],
    "3": ["۳", "٣"],
    "4": ["۴", "٤"],
    "5": ["۵", "٥"],
    "6": ["۶", "٦"],
    "7": ["۷", "٧"],
    "8": ["۸", "٨"],
    "9": ["۹", "٩"],
}


class AccentEngine:
    """Manages key-hold tracking, variant lookups, and selection state."""

    def __init__(self, hold_ms: int = 300) -> None:
        self.hold_ms = hold_ms
        self._held_vk: int | None = None
        self._held_char: str = ""
        self._press_time: float = 0.0
        self._active_variants: list[str] = []
        self._selected_index: int = 0
        self._bar_visible: bool = False

    @property
    def is_active(self) -> bool:
        return self._bar_visible and bool(self._active_variants)

    @property
    def active_variants(self) -> list[str]:
        return list(self._active_variants)

    @property
    def selected_index(self) -> int:
        return self._selected_index

    def get_variants_for_char(self, char: str) -> list[str]:
        """Return variant characters for a base character if supported."""
        return ACCENT_VARIANTS.get(char.lower(), [])

    def on_key_down(self, vk: int, char: str, now: float) -> list[str] | None:
        """Track key press start. Returns variants if hold threshold was reached."""
        if self._held_vk != vk:
            self._held_vk = vk
            self._held_char = char
            self._press_time = now
            self._bar_visible = False
            self._active_variants = []
            return None

        # Same key held down (typematic auto-repeat)
        elapsed_ms = (now - self._press_time) * 1000.0
        if elapsed_ms >= self.hold_ms and not self._bar_visible:
            variants = self.get_variants_for_char(self._held_char)
            if variants:
                self._active_variants = variants
                self._selected_index = 0
                self._bar_visible = True
                log.debug("Quick accent triggered for %r: %s", self._held_char, variants)
                return variants

        return self._active_variants if self._bar_visible else None

    def on_key_up(self, vk: int, now: float) -> tuple[bool, str | None]:
        """Process key release. Returns (was_bar_active, selected_or_original_char)."""
        if self._held_vk == vk:
            was_active = self._bar_visible
            char = self._held_char
            self._held_vk = None
            self._held_char = ""
            self._press_time = 0.0
            if not was_active:
                self.reset()
            return was_active, char
        return False, None

    def select_digit(self, digit: int) -> str | None:
        """Select variant by 1-based number key (1 to 9)."""
        if not self.is_active:
            return None
        idx = digit - 1
        if 0 <= idx < len(self._active_variants):
            chosen = self._active_variants[idx]
            self.reset()
            return chosen
        return None

    def move_selection(self, delta: int) -> int:
        """Move horizontal arrow selection left (-1) or right (+1)."""
        if not self.is_active or not self._active_variants:
            return 0
        self._selected_index = (self._selected_index + delta) % len(self._active_variants)
        return self._selected_index

    def accept_current(self) -> str | None:
        """Confirm currently highlighted variant."""
        if not self.is_active or not self._active_variants:
            return None
        chosen = self._active_variants[self._selected_index]
        self.reset()
        return chosen

    def reset(self) -> None:
        """Dismiss accent picker and clear tracking."""
        self._held_vk = None
        self._held_char = ""
        self._press_time = 0.0
        self._active_variants = []
        self._selected_index = 0
        self._bar_visible = False

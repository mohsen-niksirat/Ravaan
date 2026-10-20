"""Non-annoying feature hint notification manager for Ravaan.

Guarantees:
- Max one hint per feature ever (persisted across restarts in Config.shown_hints).
- Fully dismissible forever ("Don't show again" or global toggle).
- Never interrupts active typing or steals window focus.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from ravan.core.config import Config, save_config

log = logging.getLogger(__name__)


class HintManager:
    """Manages educational hints and tips shown to the user."""

    def __init__(
        self,
        cfg: Config,
        on_show_toast: Callable[[str], None] | None = None,
    ) -> None:
        self.cfg = cfg
        self._on_show_toast = on_show_toast

    def should_show(self, hint_id: str) -> bool:
        """Check whether a specific hint is allowed to be shown."""
        if not getattr(self.cfg, "enable_feature_hints", True):
            return False
        shown = set(getattr(self.cfg, "shown_hints", []))
        return hint_id not in shown

    def show_hint(self, hint_id: str, message: str) -> bool:
        """Display hint if allowed, and immediately mark it as shown forever.

        Returns True if the hint was shown, False if suppressed.
        """
        if not self.should_show(hint_id):
            log.debug("Hint '%s' suppressed (already shown or hints disabled)", hint_id)
            return False

        # Mark as shown in config and persist
        shown = list(getattr(self.cfg, "shown_hints", []))
        if hint_id not in shown:
            shown.append(hint_id)
            self.cfg.shown_hints = shown
            try:
                save_config(self.cfg)
            except Exception as exc:
                log.warning("Could not persist shown_hints to config: %s", exc)

        log.info("Displaying hint '%s'", hint_id)
        if self._on_show_toast:
            try:
                self._on_show_toast(message)
            except Exception as exc:
                log.warning("Failed to display hint toast: %s", exc)

        return True

    def dismiss_forever(self, hint_id: str | None = None) -> None:
        """Permanently disable either a single hint or all feature hints."""
        if hint_id:
            shown = list(getattr(self.cfg, "shown_hints", []))
            if hint_id not in shown:
                shown.append(hint_id)
                self.cfg.shown_hints = shown
        else:
            self.cfg.enable_feature_hints = False

        try:
            save_config(self.cfg)
        except Exception as exc:
            log.warning("Could not persist hint dismissal: %s", exc)

    def reset_all_hints(self) -> None:
        """Clear the history of shown hints so they can appear again."""
        self.cfg.shown_hints = []
        try:
            save_config(self.cfg)
        except Exception as exc:
            log.warning("Could not reset shown_hints: %s", exc)

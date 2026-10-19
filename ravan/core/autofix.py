"""Automatic wrong-layout correction engine (Punto / Caramba / NeuroSwitcher style)."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ravan.core.layout import LayoutMapper, is_persian_or_arabic

if TYPE_CHECKING:
    from ravan.core.dict import Dictionary
    from ravan.core.user_dict import UserDictionary

log = logging.getLogger(__name__)


@dataclass
class AutoFixRecord:
    original: str
    fixed: str
    timestamp: float
    app: str = ""
    layout_from: str = ""
    layout_to: str = ""
    undone: bool = False
    delimiter: str = ""


class AutoFixEngine:
    """Automatic wrong-layout detection and in-place correction engine."""

    def __init__(
        self,
        mapper: LayoutMapper | None = None,
        en_dict: Dictionary | None = None,
        fa_dict: Dictionary | None = None,
        user_dict: UserDictionary | None = None,
        mode: str = "safe",
    ) -> None:
        self.mapper = mapper or LayoutMapper()
        self.en_dict = en_dict
        self.fa_dict = fa_dict
        self.user_dict = user_dict
        self.mode = mode.lower()  # "off" | "safe" | "aggressive"
        self.correction_stack: list[AutoFixRecord] = []
        self.blacklist: set[tuple[str, str]] = set()
        self.undo_counts: dict[tuple[str, str], int] = {}
        self.session_suppressed_until: float = 0.0
        self.app_modes: dict[str, str] = {}

    def is_en_word(self, word: str) -> bool:
        if not word:
            return False
        clean = word.strip().lower()
        if self.user_dict and self.user_dict.contains(clean):
            return True
        if self.en_dict and self.en_dict.contains(clean):
            return True
        return False

    def is_fa_word(self, word: str) -> bool:
        if not word:
            return False
        clean = word.strip()
        if self.user_dict and self.user_dict.contains(clean):
            return True
        if self.fa_dict and self.fa_dict.contains(clean):
            return True
        return False

    def is_pair_blacklisted(self, orig: str, fixed: str) -> bool:
        return (orig.strip().lower(), fixed.strip().lower()) in self.blacklist

    def blacklist_pair(self, orig: str, fixed: str) -> None:
        key = (orig.strip().lower(), fixed.strip().lower())
        self.blacklist.add(key)
        log.info("Blacklisted auto-fix pair: %r -> %r", orig, fixed)

    def unblacklist_pair(self, orig: str, fixed: str) -> None:
        key = (orig.strip().lower(), fixed.strip().lower())
        self.blacklist.discard(key)

    def load_blacklist(self, pairs: list[list[str]] | set[tuple[str, str]]) -> None:
        self.blacklist.clear()
        for p in pairs:
            if len(p) >= 2:
                self.blacklist.add((str(p[0]).strip().lower(), str(p[1]).strip().lower()))

    def export_blacklist(self) -> list[list[str]]:
        return [[o, f] for o, f in sorted(self.blacklist)]

    def on_manual_edit(self, elapsed_since_last_fix: float) -> None:
        """Annoyance guard: manual edit within 2s cancels further auto-fixes."""
        if 0.0 <= elapsed_since_last_fix <= 2.0:
            self.session_suppressed_until = time.monotonic() + 5.0
            log.debug("Auto-fix session suppressed due to rapid manual edit (%.2fs)", elapsed_since_last_fix)

    def _is_context_persian(self, context: list[str] | None) -> bool:
        if not context:
            return False
        fa_count = sum(1 for w in context if any(is_persian_or_arabic(c) for c in w))
        return (fa_count / len(context)) >= 0.85

    def _is_context_english(self, context: list[str] | None) -> bool:
        if not context:
            return False
        en_count = sum(1 for w in context if any("a" <= c.lower() <= "z" for c in w))
        return (en_count / len(context)) >= 0.85

    def detect(
        self,
        word: str,
        active_layout: str = "en",
        app_name: str = "",
        context: list[str] | None = None,
    ) -> tuple[str, str] | None:
        """Detect wrong-layout word and return (replacement, target_layout) or None."""
        if self.mode == "off":
            return None

        if app_name:
            base_app = os.path.basename(app_name).lower()
            app_mode = self.app_modes.get(base_app) or self.app_modes.get(app_name.lower())
            if app_mode == "off":
                return None

        if time.monotonic() < self.session_suppressed_until:
            return None

        clean_word = word.strip()
        if len(clean_word) < 2:
            return None

        has_fa = any(is_persian_or_arabic(c) for c in clean_word)
        has_en = any("a" <= c.lower() <= "z" for c in clean_word)

        if has_en and not has_fa:
            # Typed in English layout
            is_valid_en = self.is_en_word(clean_word)
            if is_valid_en:
                if self.mode != "aggressive":
                    return None
                if not self._is_context_persian(context):
                    return None

            cand_fa = self.mapper.en_to_fa_word(clean_word.lower())
            if not cand_fa or not self.is_fa_word(cand_fa):
                return None

            # Reverse unambiguous check
            back_en = self.mapper.fa_to_en_word(cand_fa)
            if not back_en or back_en.lower() != clean_word.lower():
                return None

            if self.is_pair_blacklisted(clean_word, cand_fa):
                return None

            return cand_fa, "fa"

        if has_fa and not has_en:
            # Typed in Persian layout
            is_valid_fa = self.is_fa_word(clean_word)
            if is_valid_fa:
                if self.mode != "aggressive":
                    return None
                if not self._is_context_english(context):
                    return None

            cand_en = self.mapper.fa_to_en_word(clean_word)
            if not cand_en or not self.is_en_word(cand_en):
                return None

            # Reverse unambiguous check
            back_fa = self.mapper.en_to_fa_word(cand_en)
            if not back_fa or back_fa != clean_word:
                return None

            if self.is_pair_blacklisted(clean_word, cand_en):
                return None

            return cand_en, "en"

        return None

    def record_fix(
        self,
        original: str,
        fixed: str,
        app_name: str = "",
        layout_from: str = "",
        layout_to: str = "",
        delimiter: str = "",
    ) -> AutoFixRecord:
        rec = AutoFixRecord(
            original=original,
            fixed=fixed,
            timestamp=time.monotonic(),
            app=app_name,
            layout_from=layout_from,
            layout_to=layout_to,
            delimiter=delimiter,
        )
        self.correction_stack.append(rec)
        if len(self.correction_stack) > 50:
            self.correction_stack.pop(0)
        return rec

    def pop_last_correction(self) -> AutoFixRecord | None:
        for rec in reversed(self.correction_stack):
            if not rec.undone:
                rec.undone = True
                return rec
        return None

    def record_undo(self, rec: AutoFixRecord) -> bool:
        """Record an undo action. Return True if pair hit 3 undos and was blacklisted."""
        key = (rec.original.strip().lower(), rec.fixed.strip().lower())
        count = self.undo_counts.get(key, 0) + 1
        self.undo_counts[key] = count
        if count >= 3:
            self.blacklist_pair(rec.original, rec.fixed)
            log.warning("Pair %r -> %r auto-blacklisted permanently after 3 undos.", rec.original, rec.fixed)
            return True
        return False

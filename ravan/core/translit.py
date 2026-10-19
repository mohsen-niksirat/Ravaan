"""Transliteration engine: Finglish -> Persian script."""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def normalize_finglish(word: str) -> str:
    """Normalize Finglish variations (e.g., salAm -> salam, khabar -> khabar)."""
    w = word.strip().lower()
    w = w.replace("aa", "a").replace("ee", "i").replace("oo", "u")
    return w


class TranslitEngine:
    """Bilingual Finglish to Persian transliteration engine with learning and fuzzy fallback."""

    def __init__(
        self,
        dict_path: Path | None = None,
        user_dict_path: Path | None = None,
    ) -> None:
        self.mappings: dict[str, list[str]] = {}
        self.user_frequency: dict[str, dict[str, int]] = {}
        self.user_dict_path = user_dict_path
        self._load_table(dict_path)
        self._load_user_dict()

    def _load_table(self, dict_path: Path | None = None) -> None:
        if dict_path is None:
            data_dir = Path(__file__).resolve().parent.parent / "data"
            dict_path = data_dir / "finglish_dict.json"
        if dict_path.is_file():
            try:
                data = json.loads(dict_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self.mappings = data
            except Exception as exc:  # noqa: BLE001
                log.warning("Failed to load finglish_dict.json: %s", exc)

    def _load_user_dict(self) -> None:
        if self.user_dict_path and self.user_dict_path.is_file():
            try:
                data = json.loads(self.user_dict_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self.user_frequency = data
            except Exception as exc:  # noqa: BLE001
                log.warning("Failed to load user translit dict: %s", exc)

    def _save_user_dict(self) -> None:
        if self.user_dict_path:
            try:
                self.user_dict_path.parent.mkdir(parents=True, exist_ok=True)
                self.user_dict_path.write_text(
                    json.dumps(self.user_frequency, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("Failed to save user translit dict: %s", exc)

    def transliterate(self, word: str) -> list[str]:
        """Return Persian candidate words for a given Finglish word ordered by confidence."""
        clean = word.strip()
        if not clean:
            return []

        w_low = clean.lower()
        candidates: list[str] = list(self.mappings.get(w_low, []))

        # Check normalized form if no exact match
        if not candidates:
            norm = normalize_finglish(w_low)
            candidates = list(self.mappings.get(norm, []))

        # Check fuzzy fallback
        if not candidates:
            candidates = self.fuzzy_transliterate(w_low)

        # Apply user learned preferences
        user_picks = self.user_frequency.get(w_low, {})
        if user_picks:
            # Add user picks that might not be in candidates list
            for chosen in user_picks:
                if chosen not in candidates:
                    candidates.append(chosen)
            candidates.sort(key=lambda c: user_picks.get(c, 0), reverse=True)

        return candidates

    def transliterate_word(self, word: str) -> list[str]:
        """Alias for transliterate."""
        return self.transliterate(word)

    def top_candidate(self, word: str) -> str | None:
        """Return the top-1 Persian transliteration or None."""
        cands = self.transliterate(word)
        return cands[0] if cands else None

    def record_pick(self, finglish_word: str, chosen_fa: str) -> None:
        """Update personal frequency table when a user selects a candidate."""
        w_low = finglish_word.strip().lower()
        sub = self.user_frequency.setdefault(w_low, {})
        sub[chosen_fa] = sub.get(chosen_fa, 0) + 1
        log.debug(
            "Learned translit preference: %r -> %r (count=%d)",
            w_low,
            chosen_fa,
            sub[chosen_fa],
        )
        self._save_user_dict()

    def fuzzy_transliterate(self, word: str) -> list[str]:
        """Fuzzy phoneme-matching fallback for unknown Finglish words."""
        norm = normalize_finglish(word)
        if len(norm) < 3:
            return []
        matches: list[tuple[int, list[str]]] = []
        for k, v in self.mappings.items():
            if k.startswith(norm[:3]) or norm.startswith(k[:3]):
                dist = abs(len(k) - len(norm))
                matches.append((dist, v))
                if len(matches) >= 5:
                    break
        matches.sort(key=lambda item: item[0])
        out: list[str] = []
        for _, cands in matches:
            for c in cands:
                if c not in out:
                    out.append(c)
        return out[:5]

    def transliterate_text(self, text: str) -> str:
        """Transliterate whole sentence or phrase for CLI / bulk text."""
        import re

        tokens = re.split(r"(\s+|[^\w]+)", text)
        out: list[str] = []
        for tok in tokens:
            if not tok or re.match(r"^\s+$", tok) or re.match(r"^[^\w]+$", tok):
                out.append(tok)
            elif any("a" <= c.lower() <= "z" for c in tok):
                cand = self.top_candidate(tok)
                out.append(cand if cand else tok)
            else:
                out.append(tok)
        return "".join(out)

"""Predictor — dictionary lookups and candidate ranking."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .config import Config
from .dict import Dictionary
from .events import Candidate, CandidateKind


def is_arabic_persian(c: str) -> bool:
    code = ord(c)
    return (
        0x0600 <= code <= 0x06FF
        or 0xFB50 <= code <= 0xFDFF
        or 0xFE70 <= code <= 0xFEFF
    )


class Predictor(ABC):
    @abstractmethod
    def predict(self, prefix: str, context: str, limit: int) -> list[Candidate]:
        raise NotImplementedError


class DictPredictor(Predictor):
    def __init__(self, english: Dictionary | None, persian: Dictionary | None) -> None:
        self.english = english
        self.persian = persian

    @classmethod
    def from_config(cls, cfg: Config) -> DictPredictor:
        return cls(
            english=Dictionary.english() if cfg.english_dict_enabled else None,
            persian=Dictionary.persian() if cfg.persian_dict_enabled else None,
        )

    def _dict_for(self, word: str) -> Dictionary | None:
        if any(is_arabic_persian(c) for c in word):
            return self.persian
        return self.english

    def predict(self, prefix: str, context: str, limit: int) -> list[Candidate]:
        del context  # reserved for n-gram / LLM predictors
        if not prefix:
            return []

        dict_ = self._dict_for(prefix)
        if dict_ is None:
            return []

        candidates: list[Candidate] = []
        for entry in dict_.completions(prefix, limit):
            if entry.word.lower() != prefix.lower():
                candidates.append(
                    Candidate(
                        text=entry.word,
                        score=1.0 / (entry.rank + 1.0),
                        kind=CandidateKind.COMPLETION,
                    )
                )
        # Completions are the user's intent → always preferred over fuzzy matches
        candidates.sort(key=lambda c: c.score, reverse=True)

        if len(candidates) < limit:
            fuzzy = dict_.fuzzy_matches(prefix, 2, limit - len(candidates))
            prefix_rank = dict_.rank_of(prefix)
            for entry, dist in fuzzy:
                # Never suggest a word already in the dictionary unless much more frequent
                if prefix_rank is not None and entry.rank >= prefix_rank:
                    continue
                score = (1.0 / (entry.rank + 1.0)) * (1.0 / (dist + 1.0))
                candidates.append(
                    Candidate(
                        text=entry.word,
                        score=score,
                        kind=CandidateKind.AUTOCORRECT,
                    )
                )

        seen: set[str] = set()
        unique: list[Candidate] = []
        for c in candidates:
            if c.text not in seen:
                seen.add(c.text)
                unique.append(c)
        return unique[:limit]

    def correct(self, word: str) -> Candidate | None:
        """Return a safe autocorrect candidate for a completed word, or None.

        Safe means:
        - the typed word is NOT in the dictionary,
        - the typed word is NOT a valid prefix of any dictionary word
          (otherwise the user is probably still typing and will pick a completion),
        - the candidate is close (edit distance 1 for short words),
        - the candidate is far more frequent than the typed word.
        """
        if len(word) < 3 or not word.isalpha():
            return None
        dict_ = self._dict_for(word)
        if dict_ is None:
            return None
        # Exact word → nothing to fix
        if dict_.contains(word):
            return None
        # Still typing a plausible short word (a completion exists within a
        # couple characters)? Don't auto-mangle it — let the popup serve it.
        limit_len = len(word) + 2
        if any(len(e.word) <= limit_len for e in dict_.completions(word, 8)):
            return None
        max_dist = 1 if len(word) <= 4 else 2
        matches = dict_.fuzzy_matches(word, max_dist, 3)
        if not matches:
            return None
        entry, dist = matches[0]
        # Require a large frequency advantage to avoid random swaps
        if entry.rank > 500 and dist > 1:
            return None
        return Candidate(
            text=entry.word,
            score=1.0 / (entry.rank + 1.0) / (dist + 1.0),
            kind=CandidateKind.AUTOCORRECT,
        )

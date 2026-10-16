"""Predictor — dictionary lookups and candidate ranking."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .config import Config
from .dict import DictEntry, Dictionary
from .events import Candidate, CandidateKind
from .learning import UserLearningEngine


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

    def record_selection(self, word: str, context: str | None = None) -> None:
        """Record a user-accepted candidate to boost future predictions."""
        del word, context  # Optional hook for subclasses to override


class DictPredictor(Predictor):
    def __init__(
        self,
        english: Dictionary | None,
        persian: Dictionary | None,
        learning_engine: UserLearningEngine | None = None,
    ) -> None:
        self.english = english
        self.persian = persian
        self.learning = (
            learning_engine
            if learning_engine is not None
            else UserLearningEngine(auto_load=False)
        )
        self._selection_counts: dict[str, int] = {}

    def record_selection(self, word: str, context: str | None = None) -> None:
        key = word.strip().lower()
        if key:
            self._selection_counts[key] = self._selection_counts.get(key, 0) + 1
            self.learning.learn_word(word)
            if context:
                self.learning.learn_transition(context, word)
            self.learning.save()

    @classmethod
    def from_config(cls, cfg: Config) -> DictPredictor:
        from .user_dict import load_user_words

        en_dict = Dictionary.english() if cfg.english_dict_enabled else None
        fa_dict = Dictionary.persian() if cfg.persian_dict_enabled else None

        for w in load_user_words():
            if any(is_arabic_persian(c) for c in w):
                if fa_dict is not None:
                    fa_dict.add_word(w, priority=True)
            else:
                if en_dict is not None:
                    en_dict.add_word(w, priority=True)

        learning = UserLearningEngine(auto_load=True)
        return cls(english=en_dict, persian=fa_dict, learning_engine=learning)

    def _dict_for(self, word: str, lang: str | None = None) -> Dictionary | None:
        if lang == "fa":
            return self.persian
        elif lang == "en":
            return self.english
        if any(is_arabic_persian(c) for c in word):
            return self.persian
        return self.english


    def predict(self, prefix: str, context: str, limit: int) -> list[Candidate]:
        if not prefix:
            if not context:
                return []
            next_words = self.learning.predict_next_words(context, limit)
            return [
                Candidate(
                    text=w,
                    score=100.0 - i,
                    kind=CandidateKind.NEXT_WORD,
                )
                for i, w in enumerate(next_words)
            ]

        dict_ = self._dict_for(prefix)
        if dict_ is None:
            return []

        candidates: list[Candidate] = []
        seen_texts: set[str] = set()

        # 1. Learned completions from user typing history (highest priority)
        learned_matches = self.learning.top_learned_completions(prefix, limit)
        for w in learned_matches:
            if w.lower() != prefix.lower():
                candidates.append(
                    Candidate(
                        text=w,
                        score=2000.0 + self.learning.get_word_boost(w),
                        kind=CandidateKind.COMPLETION,
                    )
                )
                seen_texts.add(w)

        # 2. Dictionary completions
        scan_limit = max(limit * 3, 20)
        for entry in dict_.completions(prefix, scan_limit):
            if entry.word.lower() != prefix.lower() and entry.word not in seen_texts:
                boost = (
                    self._selection_counts.get(entry.word.lower(), 0)
                    + self.learning.get_word_boost(entry.word)
                )
                # Boost if it matches a context transition
                if context and context in self.learning.transitions:
                    if entry.word in self.learning.transitions[context]:
                        boost += 50.0

                # Ranking hierarchy: Custom Dict (rank=0) > Frequency (with adaptive boost)
                if entry.rank == 0:
                    score = 1000.0 + boost
                else:
                    base_freq = 1.0 / (entry.rank + 1.0)
                    score = base_freq * (1.0 + boost * 2.0) + (boost * 0.1)

                candidates.append(
                    Candidate(
                        text=entry.word,
                        score=score,
                        kind=CandidateKind.COMPLETION,
                    )
                )
                seen_texts.add(entry.word)

        # Completions are the user's intent → always preferred over fuzzy matches
        candidates.sort(key=lambda c: c.score, reverse=True)
        completions = candidates[:limit]

        if len(completions) < limit:
            fuzzy = dict_.fuzzy_matches(prefix, 2, limit - len(completions))
            prefix_rank = dict_.rank_of(prefix)
            for entry, dist in fuzzy:
                if entry.word in seen_texts:
                    continue
                # Never suggest a word already in the dictionary unless much more frequent
                if prefix_rank is not None and entry.rank >= prefix_rank:
                    continue
                # Fuzzy matches are penalised by edit distance so they rank strictly below completions
                score = (1.0 / (entry.rank + 1.0)) * (1.0 / (dist * 10.0 + 1.0))
                completions.append(
                    Candidate(
                        text=entry.word,
                        score=score,
                        kind=CandidateKind.AUTOCORRECT,
                    )
                )
                seen_texts.add(entry.word)

        return completions[:limit]

    def correct(self, word: str, lang: str | None = None) -> Candidate | None:
        """Return a safe autocorrect candidate for a completed word, or None.

        Safe and intelligent autocorrect:
        - Bilingual awareness: only autocorrect in active language (never mix).
        - Persian-specific typos: similar-looking letters (ه/ة, ي/ی, ك/ک, etc.).
        - Exact dictionary words are never modified.
        - Plausible in-progress prefixes are not mangled.
        - Per-word probability ranking based on frequency, edit distance, and adaptive learning.
        """
        if len(word) < 3 or not word.isalpha():
            return None

        # Bilingual check: never mix languages
        if lang == "fa" and not any(is_arabic_persian(c) for c in word):
            return None
        if lang == "en" and any(is_arabic_persian(c) for c in word):
            return None

        dict_ = self._dict_for(word, lang=lang)
        if dict_ is None:
            return None

        # Exact word → already correct
        if dict_.contains(word):
            return None

        # 1. Persian confusable typo normalization (highest confidence)
        if any(is_arabic_persian(c) for c in word):
            from .normalizer import normalize_persian_typos

            for variant in normalize_persian_typos(word):
                if dict_.contains(variant):
                    entry = dict_._lower[variant.lower()]
                    boost = self._selection_counts.get(variant.lower(), 0)
                    score = 1000.0 + (1.0 / (entry.rank + 1.0)) + boost
                    return Candidate(
                        text=entry.word,
                        score=score,
                        kind=CandidateKind.AUTOCORRECT,
                    )

        # 2. Still typing a plausible prefix of a short word? Don't auto-mangle
        if len(word) >= 3:
            limit_len = len(word) + 2
            if any(len(e.word) <= limit_len for e in dict_.completions(word, 8)):
                return None

        # 3. Fuzzy matches with frequency probability
        max_dist = 1 if len(word) <= 4 else 2
        matches = dict_.fuzzy_matches(word, max_dist, 8)
        if not matches:
            return None

        import math

        scored: list[tuple[float, DictEntry, int]] = []
        for entry, dist in matches:
            boost = self._selection_counts.get(entry.word.lower(), 0)
            if entry.rank == 0:
                prob = 1000.0 + boost
            else:
                freq = entry.frequency if entry.frequency > 0 else max(1, 15000 - entry.rank * 2)
                log_freq = math.log10(freq + 10)
                dist_penalty = 1.0 if dist == 1 else 3.5
                prob = (log_freq / dist_penalty) + (boost * 0.5)

                if dist > 1 and entry.rank > 2000:
                    continue

            scored.append((prob, entry, dist))

        if not scored:
            return None

        scored.sort(key=lambda t: t[0], reverse=True)
        best_prob, best_entry, best_dist = scored[0]

        return Candidate(
            text=best_entry.word,
            score=best_prob,
            kind=CandidateKind.AUTOCORRECT,
        )


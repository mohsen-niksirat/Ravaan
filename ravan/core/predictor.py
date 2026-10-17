"""Predictor — dictionary lookups and candidate ranking."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

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
        english: Dictionary | None = None,
        persian: Dictionary | None = None,
        learning_engine: UserLearningEngine | None = None,
        ignored_words: set[str] | list[str] | None = None,
        autocorrect_mode: str = "safe",
        lazy_en_loader: Callable[[], Dictionary | None] | None = None,
        lazy_fa_loader: Callable[[], Dictionary | None] | None = None,
        lazy_learning_loader: Callable[[], UserLearningEngine] | None = None,
    ) -> None:
        self._english = english
        self._persian = persian
        self._learning = learning_engine
        self._lazy_en_loader = lazy_en_loader
        self._lazy_fa_loader = lazy_fa_loader
        self._lazy_learning_loader = lazy_learning_loader
        self.ignored_words = {
            w.strip().lower() for w in (ignored_words or []) if w and w.strip()
        }
        self.session_suppressed: set[str] = set()
        self.autocorrect_mode = autocorrect_mode.strip().lower()
        self._selection_counts: dict[str, int] = {}

    @property
    def english(self) -> Dictionary | None:
        if self._english is None and self._lazy_en_loader is not None:
            self._english = self._lazy_en_loader()
            self._lazy_en_loader = None
        return self._english

    @english.setter
    def english(self, value: Dictionary | None) -> None:
        self._english = value
        self._lazy_en_loader = None

    @property
    def persian(self) -> Dictionary | None:
        if self._persian is None and self._lazy_fa_loader is not None:
            self._persian = self._lazy_fa_loader()
            self._lazy_fa_loader = None
        return self._persian

    @persian.setter
    def persian(self, value: Dictionary | None) -> None:
        self._persian = value
        self._lazy_fa_loader = None

    @property
    def learning(self) -> UserLearningEngine:
        if self._learning is None:
            if self._lazy_learning_loader is not None:
                self._learning = self._lazy_learning_loader()
                self._lazy_learning_loader = None
            else:
                self._learning = UserLearningEngine(auto_load=False)
        return self._learning

    @learning.setter
    def learning(self, value: UserLearningEngine) -> None:
        self._learning = value
        self._lazy_learning_loader = None

    def suppress_session_word(self, word: str) -> None:
        """Suppress autocorrection for this word for the rest of the running session."""
        w = word.strip().lower()
        if w:
            self.session_suppressed.add(w)

    def record_selection(self, word: str, context: str | None = None) -> None:
        key = word.strip().lower()
        if key:
            self._selection_counts[key] = self._selection_counts.get(key, 0) + 1
            self.learning.learn_word(word)
            if context:
                parts = context.strip().split()
                if len(parts) >= 2:
                    self.learning.learn_trigram(parts[-2], parts[-1], word)
                if parts:
                    self.learning.learn_transition(parts[-1], word)
            self.learning.save()

    @classmethod
    def from_config(cls, cfg: Config) -> DictPredictor:
        from .user_dict import load_user_words

        def _load_en() -> Dictionary | None:
            if not cfg.english_dict_enabled:
                return None
            d = Dictionary.english()
            for w in load_user_words():
                if not any(is_arabic_persian(c) for c in w):
                    d.add_word(w, priority=True)
            return d

        def _load_fa() -> Dictionary | None:
            if not cfg.persian_dict_enabled:
                return None
            d = Dictionary.persian()
            for w in load_user_words():
                if any(is_arabic_persian(c) for c in w):
                    d.add_word(w, priority=True)
            return d

        def _load_learning() -> UserLearningEngine:
            return UserLearningEngine(auto_load=True)

        return cls(
            english=None,
            persian=None,
            learning_engine=None,
            ignored_words=cfg.ignored_words,
            autocorrect_mode=cfg.autocorrect_mode if cfg.autocorrect_enabled else "off",
            lazy_en_loader=_load_en,
            lazy_fa_loader=_load_fa,
            lazy_learning_loader=_load_learning,
        )


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

        if len(completions) < limit and len(prefix) >= 3:
            fuzzy = dict_.fuzzy_matches(prefix, 1, limit - len(completions))
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
        """Return an autocorrect candidate for a completed word based on configured mode, or None."""
        if self.autocorrect_mode == "off":
            return None

        if len(word) < 3 or not word.isalpha():
            return None

        w_low = word.lower()
        if w_low in self.ignored_words or w_low in self.session_suppressed:
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

        # 2. Still typing a plausible prefix of a short word? Don't auto-mangle in safe mode
        if self.autocorrect_mode == "safe" and len(word) >= 3:
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


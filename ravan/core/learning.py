"""User typing style learning engine: tracks vocabulary frequency and bigram sentence transitions."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ravan.core.config import config_dir

log = logging.getLogger(__name__)

# Common Persian starter transitions (seeded bigrams) for out-of-the-box next-word / sentence prediction
_SEEDED_PERSIAN_TRANSITIONS: dict[str, list[str]] = {
    "سلام": ["عزیز", "علیکم", "وقتتون", "دوست", "خوبید", "احوال", "روزتون"],
    "درود": ["بر", "شما", "عزیز", "همکاران"],
    "با": ["تشکر", "احترام", "سلام", "توجه", "آرزوی", "عنایت", "امید"],
    "خیلی": ["ممنون", "خوب", "عالی", "سپاسگزارم", "لطف", "متشکرم"],
    "به": ["نام", "عنوان", "صورت", "نظر", "ویژه", "خاطر", "دلیل", "امید"],
    "از": ["شما", "این", "طریق", "جمله", "طرف", "سوی", "لحاظ"],
    "در": ["حال", "رابطه", "باره", "مورد", "این", "صورت", "دسترس"],
    "دست": ["شما", "درد", "مریزاد"],
    "لطفا": ["بررسی", "ارسال", "بفرمایید", "پیگیری", "تماس", "اطلاع"],
    "خواهش": ["می‌کنم", "میکنم", "دارم"],
    "ان‌شاءالله": ["سلامت", "موفق", "پیروز", "خیر"],
    "امیدوارم": ["خوب", "سلامت", "موفق", "عالی"],
    "وقت": ["بخیر", "شریف", "شما"],
    "روز": ["بخیر", "خوشی", "خوبی"],
    "صبح": ["بخیر", "زیبایتان"],
    "شب": ["بخیر", "خوش"],
    "قربان": ["شما", "محبت"],
    "ارادتمند": ["شما", "همگی"],
    "موفق": ["و", "باشید", "پیروز"],
    "برای": ["شما", "این", "انجام", "اطلاعات"],
}


_SEEDED_ENGLISH_TRANSITIONS: dict[str, list[str]] = {
    "how": ["are", "is", "to", "do", "can"],
    "thank": ["you", "so", "very"],
    "thanks": ["for", "again", "a"],
    "good": ["morning", "afternoon", "evening", "luck", "job", "idea"],
    "please": ["let", "find", "see", "check", "help", "note"],
    "let": ["me", "us", "know"],
    "looking": ["forward", "for", "at", "into"],
    "nice": ["to", "meeting", "day"],
    "best": ["regards", "wishes", "way"],
    "would": ["like", "be", "have", "you"],
    "could": ["you", "be", "have", "not"],
    "can": ["you", "i", "we", "be"],
    "i": ["am", "will", "would", "have", "think", "want"],
    "we": ["are", "will", "have", "can", "hope"],
    "you": ["can", "are", "have", "will", "need"],
    "it": ["is", "was", "will", "would"],
    "there": ["is", "are", "was", "were"],
    "as": ["well", "soon", "long", "per"],
    "have": ["a", "been", "to", "any"],
    "what": ["is", "are", "do", "you"],
}

_SEEDED_TRIGRAMS: dict[str, list[str]] = {
    "thank you": ["very", "so", "much", "for", "again"],
    "خیلی ممنون": ["از", "شما", "عزیز", "همگی"],
    "به نام": ["خدا", "ایزد", "او"],
    "با تشکر": ["از", "و", "فراوان", "احترام"],
    "لطفا بررسی": ["بفرمایید", "کنید", "فرمایید"],
    "how are": ["you", "things", "doing"],
    "let me": ["know", "see", "check"],
    "looking forward": ["to", "hearing"],
    "would like": ["to", "have"],
    "i hope": ["you", "this", "all"],
    "امیدوارم حال": ["شما", "خوبی"],
    "در رابطه": ["با", "به"],
    "به عنوان": ["مثال", "یک"],
    "دست شما": ["درد", "نکنه"],
    "as soon": ["as", "possible"],
    "in order": ["to", "for"],
}


class UserLearningEngine:
    """Tracks words, bigram, and trigram sentence transitions to adapt to user typing style."""

    def __init__(
        self, storage_path: Path | None = None, auto_load: bool = True
    ) -> None:
        self.storage_path = storage_path or (config_dir() / "user_learning.json")
        self.word_counts: dict[str, int] = {}
        self.transitions: dict[str, dict[str, int]] = {}
        self.trigrams: dict[str, dict[str, int]] = {}
        self._seed_defaults()
        if auto_load:
            self._load()

    def _seed_defaults(self) -> None:
        for prev, nexts in _SEEDED_PERSIAN_TRANSITIONS.items():
            trans_map = self.transitions.setdefault(prev, {})
            base_score = 50
            for idx, nxt in enumerate(nexts):
                trans_map.setdefault(nxt, base_score - idx * 5)

        for prev, nexts in _SEEDED_ENGLISH_TRANSITIONS.items():
            trans_map = self.transitions.setdefault(prev, {})
            base_score = 50
            for idx, nxt in enumerate(nexts):
                trans_map.setdefault(nxt, base_score - idx * 5)

        for tri_key, nexts in _SEEDED_TRIGRAMS.items():
            tri_map = self.trigrams.setdefault(tri_key, {})
            base_score = 70
            for idx, nxt in enumerate(nexts):
                tri_map.setdefault(nxt, base_score - idx * 5)

    def learn_word(self, word: str) -> None:
        clean = word.strip()
        if not clean or len(clean) < 2:
            return
        self.word_counts[clean] = self.word_counts.get(clean, 0) + 1

    def learn_transition(self, prev_word: str, next_word: str) -> None:
        w1 = prev_word.strip()
        w2 = next_word.strip()
        if not w1 or not w2:
            return
        self.learn_word(w2)
        trans_map = self.transitions.setdefault(w1, {})
        trans_map[w2] = trans_map.get(w2, 0) + 1

    def learn_trigram(self, w1: str, w2: str, w3: str) -> None:
        k1 = w1.strip()
        k2 = w2.strip()
        target = w3.strip()
        if not k1 or not k2 or not target:
            return
        self.learn_word(target)
        self.learn_transition(k2, target)
        tri_key = f"{k1.lower()} {k2.lower()}"
        tri_map = self.trigrams.setdefault(tri_key, {})
        tri_map[target] = tri_map.get(target, 0) + 1

    def predict_next_words(self, context: str, limit: int = 5) -> list[str]:
        raw = context.strip()
        if not raw:
            return []

        words = raw.split()
        results: list[tuple[str, float]] = []
        seen: set[str] = set()

        # 1. Trigram context if 2 or more words available
        if len(words) >= 2:
            tri_key = f"{words[-2].lower()} {words[-1].lower()}"
            tri_cands = self.trigrams.get(tri_key)
            if tri_cands:
                for w, score in tri_cands.items():
                    boost = score * 2.0 + (self.word_counts.get(w, 0) * 0.2)
                    results.append((w, boost))
                    seen.add(w.lower())

        # 2. Bigram fallback from last word
        last_word = words[-1]
        cands = self.transitions.get(last_word)
        if not cands and last_word.lower() != last_word:
            cands = self.transitions.get(last_word.lower())

        if cands:
            for w, score in cands.items():
                if w.lower() not in seen:
                    boost = score + (self.word_counts.get(w, 0) * 0.2)
                    results.append((w, boost))
                    seen.add(w.lower())

        results.sort(key=lambda item: item[1], reverse=True)
        return [word for word, _ in results[:limit]]

    def get_word_boost(self, word: str) -> float:
        return float(self.word_counts.get(word.strip(), 0))

    def top_learned_completions(self, prefix: str, limit: int = 5) -> list[str]:
        if not prefix:
            return []
        matches: list[tuple[str, int]] = []
        for word, count in self.word_counts.items():
            if word.startswith(prefix) and word != prefix:
                matches.append((word, count))
        matches.sort(key=lambda x: x[1], reverse=True)
        return [w for w, _ in matches[:limit]]

    def save(self) -> None:
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data: dict[str, Any] = {
                "version": 2,
                "word_counts": self.word_counts,
                "transitions": self.transitions,
                "trigrams": self.trigrams,
            }
            tmp = self.storage_path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tmp.replace(self.storage_path)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to save user learning model: %s", exc)

    def _load(self) -> None:
        if not self.storage_path.is_file():
            return
        try:
            with open(self.storage_path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                saved_words = data.get("word_counts", {})
                if isinstance(saved_words, dict):
                    self.word_counts.update(
                        {str(k): int(v) for k, v in saved_words.items()}
                    )
                saved_trans = data.get("transitions", {})
                if isinstance(saved_trans, dict):
                    for k, v in saved_trans.items():
                        if isinstance(v, dict):
                            self.transitions.setdefault(str(k), {}).update(
                                {str(nk): int(nv) for nk, nv in v.items()}
                            )
                saved_tri = data.get("trigrams", {})
                if isinstance(saved_tri, dict):
                    for k, v in saved_tri.items():
                        if isinstance(v, dict):
                            self.trigrams.setdefault(str(k), {}).update(
                                {str(nk): int(nv) for nk, nv in v.items()}
                            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to load user learning model: %s", exc)

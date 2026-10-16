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


class UserLearningEngine:
    """Tracks words and word-to-word bigram transitions to adapt to the user's personal typing style."""

    def __init__(
        self, storage_path: Path | None = None, auto_load: bool = True
    ) -> None:
        self.storage_path = storage_path or (config_dir() / "user_learning.json")
        self.word_counts: dict[str, int] = {}
        self.transitions: dict[str, dict[str, int]] = {}
        self._seed_defaults()
        if auto_load:
            self._load()

    def _seed_defaults(self) -> None:
        for prev, nexts in _SEEDED_PERSIAN_TRANSITIONS.items():
            trans_map = self.transitions.setdefault(prev, {})
            base_score = 50
            for idx, nxt in enumerate(nexts):
                trans_map.setdefault(nxt, base_score - idx * 5)

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

    def predict_next_words(self, prev_word: str, limit: int = 5) -> list[str]:
        w1 = prev_word.strip()
        if not w1:
            return []

        # Exact match or normalized lookup
        candidates = self.transitions.get(w1)
        if not candidates and w1.lower() != w1:
            candidates = self.transitions.get(w1.lower())

        if not candidates:
            return []

        # Sort by frequency count descending
        sorted_next = sorted(
            candidates.items(),
            key=lambda item: item[1] + (self.word_counts.get(item[0], 0) * 0.2),
            reverse=True,
        )
        return [word for word, _ in sorted_next[:limit]]

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
                "version": 1,
                "word_counts": self.word_counts,
                "transitions": self.transitions,
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
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to load user learning model: %s", exc)

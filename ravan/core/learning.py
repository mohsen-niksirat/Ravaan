"""User typing style learning engine v2: vocabulary, stupid backoff n-grams, decay, and per-app weights."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from ravan.core.config import config_dir

log = logging.getLogger(__name__)

# Seeded bigrams for instant next-word prediction
_SEEDED_PERSIAN_TRANSITIONS: dict[str, list[str]] = {
    "سلام": ["عزیز", "علیکم", "وقتتون", "دوست", "خوبید", "احوال", "روزتون"],
    "درود": ["بر", "شما", "عزیز", "همکاران"], "دست": ["شما", "درد", "مریزاد"],
    "با": ["تشکر", "احترام", "سلام", "توجه", "آرزوی", "عنایت", "امید"],
    "خیلی": ["ممنون", "خوب", "عالی", "سپاسگزارم", "لطف", "متشکرم"],
    "به": ["نام", "عنوان", "صورت", "نظر", "ویژه", "خاطر", "دلیل", "امید"],
    "از": ["شما", "این", "طریق", "جمله", "طرف", "سوی", "لحاظ"],
    "در": ["حال", "رابطه", "باره", "مورد", "این", "صورت", "دسترس"],
    "لطفا": ["بررسی", "ارسال", "بفرمایید", "پیگیری", "تماس", "اطلاع"],
    "خواهش": ["می‌کنم", "میکنم", "دارم"], "ان‌شاءالله": ["سلامت", "موفق", "پیروز", "خیر"],
    "امیدوارم": ["خوب", "سلامت", "موفق", "عالی", "حال"], "وقت": ["بخیر", "شریف", "شما"],
    "روز": ["بخیر", "خوشی", "خوبی"], "صبح": ["بخیر", "زیبایتان"], "شب": ["بخیر", "خوش"],
    "قربان": ["شما", "محبت"], "ارادتمند": ["شما", "همگی"], "موفق": ["و", "باشید", "پیروز"],
    "برای": ["شما", "این", "انجام", "اطلاعات"],
}

_SEEDED_ENGLISH_TRANSITIONS: dict[str, list[str]] = {
    "how": ["are", "is", "to", "do", "can"], "thank": ["you", "so", "very"],
    "thanks": ["for", "again", "a"], "best": ["regards", "wishes", "way"],
    "good": ["morning", "afternoon", "evening", "luck", "job", "idea"],
    "please": ["let", "find", "see", "check", "help", "note"],
    "let": ["me", "us", "know"], "looking": ["forward", "for", "at", "into"],
    "nice": ["to", "meeting", "day"], "would": ["like", "be", "have", "you"],
    "could": ["you", "be", "have", "not"], "can": ["you", "i", "we", "be"],
    "i": ["am", "will", "would", "have", "think", "want"],
    "we": ["are", "will", "have", "can", "hope"], "you": ["can", "are", "have", "will", "need"],
    "it": ["is", "was", "will", "would"], "there": ["is", "are", "was", "were"],
    "as": ["well", "soon", "long", "per"], "have": ["a", "been", "to", "any"],
    "what": ["is", "are", "do", "you"],
}

_SEEDED_TRIGRAMS: dict[str, list[str]] = {
    "thank you": ["very", "so", "much", "for", "again"],
    "خیلی ممنون": ["از", "شما", "عزیز", "همگی"], "به نام": ["خدا", "ایزد", "او"],
    "با تشکر": ["از", "و", "فراوان", "احترام"], "لطفا بررسی": ["بفرمایید", "کنید", "فرمایید"],
    "how are": ["you", "things", "doing"], "let me": ["know", "see", "check"],
    "looking forward": ["to", "hearing"], "would like": ["to", "have"],
    "i hope": ["you", "this", "all"], "امیدوارم حال": ["شما", "خوبی"],
    "در رابطه": ["با", "به"], "به عنوان": ["مثال", "یک"], "دست شما": ["درد", "نکنه"],
    "as soon": ["as", "possible"], "in order": ["to", "for"],
}

_SEEDED_SENTENCES: list[str] = [
    "خوش آمدید", "خوش آمدید به جمع ما", "خیلی ممنون از شما", "خیلی ممنون و متشکر",
    "با تشکر و احترام", "با تشکر فراوان", "دست شما درد نکنه", "به نام خدا",
    "لطفا بررسی بفرمایید", "امیدوارم حال شما خوب باشد", "thank you very much",
    "thank you so much", "looking forward to hearing from you", "as soon as possible",
    "let me know if you need anything", "have a great day",
]


class UserLearningEngine:
    """Adaptive typing engine v2: n-gram smoothing, exponential decay, and per-app weighting."""

    def __init__(self, storage_path: Path | None = None, auto_load: bool = True) -> None:
        self.storage_path = storage_path or (config_dir() / "user_learning.json")
        self.word_counts: dict[str, float] = {}
        self.transitions: dict[str, dict[str, float]] = {}
        self.trigrams: dict[str, dict[str, float]] = {}
        self.app_word_counts: dict[str, dict[str, float]] = {}
        self.last_decay_time: float = time.time()
        self._top_cache: list[str] | None = None
        self._seed_defaults()
        if auto_load:
            self._load()

    def _seed_defaults(self) -> None:
        for m, seeds in (
            (self.transitions, _SEEDED_PERSIAN_TRANSITIONS),
            (self.transitions, _SEEDED_ENGLISH_TRANSITIONS),
            (self.trigrams, _SEEDED_TRIGRAMS),
        ):
            for prev, nexts in seeds.items():
                target_map = m.setdefault(prev, {})
                for idx, nxt in enumerate(nexts):
                    target_map.setdefault(nxt, float(max(10, 50 - idx * 5)))

    def learn_word(self, word: str, app_name: str | None = None) -> None:
        clean = word.strip()
        if not clean or len(clean) < 2:
            return
        self.word_counts[clean] = self.word_counts.get(clean, 0.0) + 1.0
        self._top_cache = None
        if app_name:
            app_key = app_name.strip().lower()
            if app_key:
                self.app_word_counts.setdefault(app_key, {})[clean] = (
                    self.app_word_counts.setdefault(app_key, {}).get(clean, 0.0) + 1.0
                )

    def learn_transition(self, prev_word: str, next_word: str, app_name: str | None = None) -> None:
        w1, w2 = prev_word.strip(), next_word.strip()
        if not w1 or not w2:
            return
        self.learn_word(w2, app_name=app_name)
        trans = self.transitions.setdefault(w1, {})
        trans[w2] = trans.get(w2, 0.0) + 1.0

    def learn_trigram(self, w1: str, w2: str, w3: str, app_name: str | None = None) -> None:
        k1, k2, target = w1.strip(), w2.strip(), w3.strip()
        if not k1 or not k2 or not target:
            return
        self.learn_word(target, app_name=app_name)
        self.learn_transition(k2, target, app_name=app_name)
        tri_map = self.trigrams.setdefault(f"{k1.lower()} {k2.lower()}", {})
        tri_map[target] = tri_map.get(target, 0.0) + 1.0

    def get_word_boost(self, word: str, app_name: str | None = None) -> float:
        clean = word.strip()
        base = self.word_counts.get(clean, 0.0)
        if app_name:
            base += self.app_word_counts.get(app_name.strip().lower(), {}).get(clean, 0.0) * 3.0
        return base

    def compute_smoothed_score(
        self, w3: str, w2: str | None = None, w1: str | None = None, alpha: float = 0.4
    ) -> float:
        """Compute stupid backoff and linear interpolation score for w3 given context (w1, w2)."""
        c123, c12 = 0.0, 0.0
        if w1 and w2:
            tri = self.trigrams.get(f"{w1.lower()} {w2.lower()}", {})
            c123, c12 = tri.get(w3, 0.0), sum(tri.values())

        c23, c2 = 0.0, 0.0
        if w2:
            bi = self.transitions.get(w2) or self.transitions.get(w2.lower(), {})
            c23, c2 = bi.get(w3, 0.0), sum(bi.values())

        c3 = self.word_counts.get(w3, 0.0)
        total_n = max(1.0, sum(self.word_counts.values()))

        # Stupid Backoff
        if c123 > 0.0 and c12 > 0.0:
            sb = c123 / c12
        elif c23 > 0.0 and c2 > 0.0:
            sb = alpha * (c23 / c2)
        else:
            sb = (alpha**2) * ((c3 + 0.5) / (total_n + 50.0))

        # Linear Interpolation
        p_tri = (c123 / c12) if c12 > 0.0 else 0.0
        p_bi = (c23 / c2) if c2 > 0.0 else 0.0
        interp = (0.60 * p_tri) + (0.28 * p_bi) + (0.12 * ((c3 + 0.5) / (total_n + 50.0)))

        return (sb * 0.5) + (interp * 0.5)

    def predict_next_words(self, context: str, limit: int = 5, app_name: str | None = None) -> list[str]:
        raw = context.strip()
        if not raw:
            return []
        words = raw.split()
        w1 = words[-2] if len(words) >= 2 else None
        w2 = words[-1]

        candidates: set[str] = set()
        if w1 and w2:
            candidates.update(self.trigrams.get(f"{w1.lower()} {w2.lower()}", {}).keys())
        if w2:
            candidates.update((self.transitions.get(w2) or self.transitions.get(w2.lower(), {})).keys())

        if len(candidates) < limit:
            if self._top_cache is None:
                self._top_cache = [w for w, _ in sorted(self.word_counts.items(), key=lambda x: x[1], reverse=True)[:15]]
            candidates.update(self._top_cache[:10])

        scored = [
            (c, self.compute_smoothed_score(c, w2=w2, w1=w1) * 100.0 + self.get_word_boost(c, app_name=app_name) * 2.0)
            for c in candidates
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        return [w for w, _ in scored[:limit]]

    def predict_sentence_continuations(
        self, context: str, prefix: str = "", limit: int = 3, app_name: str | None = None
    ) -> list[str]:
        """Offer top multi-word completions matching current context and typing prefix."""
        combined = f"{context} {prefix}".strip().lower()
        if not combined:
            return []

        results: list[str] = []
        for sentence in _SEEDED_SENTENCES:
            low_s = sentence.lower()
            if low_s.startswith(combined) and low_s != combined:
                results.append(sentence)
                if len(results) >= limit:
                    return results

        if not context:
            return results

        next_words = self.predict_next_words(context, limit=2, app_name=app_name)
        for nw in next_words:
            if prefix and not nw.lower().startswith(prefix.lower()):
                continue
            sub_context = f"{context} {nw}".strip()
            second_words = self.predict_next_words(sub_context, limit=2, app_name=app_name)
            for sw in second_words:
                cand_sentence = f"{nw} {sw}"
                if cand_sentence not in results:
                    results.append(cand_sentence)
                    if len(results) >= limit:
                        return results

        return results[:limit]

    def top_learned_completions(self, prefix: str, limit: int = 5, app_name: str | None = None) -> list[str]:
        if not prefix:
            return []
        matches: list[tuple[str, float]] = []
        for word in self.word_counts:
            if word.startswith(prefix) and word != prefix:
                matches.append((word, self.get_word_boost(word, app_name=app_name)))
        matches.sort(key=lambda x: x[1], reverse=True)
        return [w for w, _ in matches[:limit]]

    def decay_frequencies(self, half_life_days: float = 30.0, current_time: float | None = None) -> float:
        """Apply exponential decay to frequency counts based on elapsed time."""
        now = current_time if current_time is not None else time.time()
        elapsed = max(0.0, now - self.last_decay_time)
        factor = 2.0 ** (-elapsed / max(1.0, half_life_days * 86400.0))
        if factor >= 0.999:
            return factor

        def _decay_dict(d: dict[str, float]) -> None:
            for k in list(d.keys()):
                val = d[k] * factor
                if val < 0.1:
                    del d[k]
                else:
                    d[k] = val

        _decay_dict(self.word_counts)
        self._top_cache = None
        for nested in (self.transitions, self.trigrams, self.app_word_counts):
            for parent_k in list(nested.keys()):
                _decay_dict(nested[parent_k])
                if not nested[parent_k]:
                    del nested[parent_k]

        self.last_decay_time = now
        return factor

    def export_profile(self, target_path: Path | str | None = None) -> dict[str, Any]:
        """Export learned vocabulary, n-grams, and app profiles as a dictionary and optional JSON."""
        data: dict[str, Any] = {
            "version": 3,
            "exported_at": time.time(),
            "last_decay_time": self.last_decay_time,
            "word_counts": self.word_counts,
            "transitions": self.transitions,
            "trigrams": self.trigrams,
            "app_word_counts": self.app_word_counts,
        }
        if target_path:
            p = Path(target_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        return data

    def import_profile(self, source: Path | str | dict[str, Any], merge: bool = True) -> int:
        """Import learned profile data from a JSON file or dictionary."""
        data = json.loads(Path(source).read_text(encoding="utf-8")) if isinstance(source, (str, Path)) else source
        if not isinstance(data, dict):
            return 0

        if not merge:
            self.word_counts.clear()
            self.transitions.clear()
            self.trigrams.clear()
            self.app_word_counts.clear()
            self._seed_defaults()

        count = 0
        for k, v in data.get("word_counts", {}).items():
            self.word_counts[str(k)] = self.word_counts.get(str(k), 0.0) + float(v)
            count += 1
        self._top_cache = None

        for target, key in (
            (self.transitions, "transitions"),
            (self.trigrams, "trigrams"),
            (self.app_word_counts, "app_word_counts"),
        ):
            for pk, sub in data.get(key, {}).items():
                if isinstance(sub, dict):
                    m = target.setdefault(str(pk), {})
                    for nk, v in sub.items():
                        m[str(nk)] = m.get(str(nk), 0.0) + float(v)

        return count

    def save(self) -> None:
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.storage_path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.export_profile(), f, ensure_ascii=False, indent=2)
            tmp.replace(self.storage_path)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to save user learning model: %s", exc)

    def _load(self) -> None:
        if not self.storage_path.is_file():
            return
        try:
            with open(self.storage_path, encoding="utf-8") as f:
                data = json.load(f)
            self.import_profile(data, merge=True)
            self.last_decay_time = float(data.get("last_decay_time", time.time()))
            self.decay_frequencies()
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to load user learning model: %s", exc)

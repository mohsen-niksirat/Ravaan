"""User typing style learning engine v2: vocabulary, stupid backoff n-grams, decay, and per-app weights."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from ravan.core.config import config_dir
from ravan.core.normalizer import (
    is_numeric_or_symbol_token,
    is_persian_script_token,
    is_valid_prediction_context_word,
    normalize_arabic_chars,
)

log = logging.getLogger(__name__)

_CORPUS_SENTENCE_SPLIT_RE = re.compile(r"[.!?؟؛\r\n]+")
_CORPUS_URL_EMAIL_RE = re.compile(
    r"(https?://\S+|www\.\S+|[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9-.]+)"
)
_CORPUS_TOKEN_RE = re.compile(r"[\u0621-\u06FF\u200c]+|[A-Za-z][A-Za-z'’-]*")

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

    def __init__(
        self,
        storage_path: Path | None = None,
        auto_load: bool = True,
        learning_enabled: bool = True,
    ) -> None:
        self.storage_path = storage_path or (config_dir() / "user_learning.json")
        self.learning_enabled = learning_enabled
        # Deferred persistence: record_selection() fires on every completed word;
        # serializing + DPAPI-encrypting the whole model per word stalls the UI
        # thread (and starves the keyboard hook) as the model grows. Saves are
        # lazy (min interval) and flushed periodically / on shutdown.
        self._dirty = False
        self._last_save_at = time.monotonic()  # defer even the first lazy save
        self._lazy_save_interval = 30.0
        self.word_counts: dict[str, float] = {}
        self.transitions: dict[str, dict[str, float]] = {}
        self.trigrams: dict[str, dict[str, float]] = {}
        self.app_word_counts: dict[str, dict[str, float]] = {}
        self.last_decay_time: float = time.time()
        self.half_life_days: float = 30.0
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
        if not self.learning_enabled:
            return
        clean = word.strip()
        if not clean or len(clean) < 2 or is_numeric_or_symbol_token(clean):
            return
        self.word_counts[clean] = self.word_counts.get(clean, 0.0) + 1.0
        self._top_cache = None
        if app_name:
            app_key = app_name.strip().lower()
            if app_key:
                app_map = self.app_word_counts.setdefault(app_key, {})
                app_map[clean] = app_map.get(clean, 0.0) + 1.0

    def learn_transition(self, prev_word: str, next_word: str, app_name: str | None = None) -> None:
        if not self.learning_enabled:
            return
        w1, w2 = prev_word.strip(), next_word.strip()
        if not w1 or not w2 or is_numeric_or_symbol_token(w1) or is_numeric_or_symbol_token(w2):
            return
        self.learn_word(w2, app_name=app_name)
        trans = self.transitions.setdefault(w1, {})
        trans[w2] = trans.get(w2, 0.0) + 1.0

    def learn_trigram(self, w1: str, w2: str, w3: str, app_name: str | None = None) -> None:
        if not self.learning_enabled:
            return
        k1, k2, target = w1.strip(), w2.strip(), w3.strip()
        if (
            not k1
            or not k2
            or not target
            or is_numeric_or_symbol_token(k1)
            or is_numeric_or_symbol_token(k2)
            or is_numeric_or_symbol_token(target)
        ):
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
        if not is_valid_prediction_context_word(w2):
            return []

        candidates: set[str] = set()
        if w1 and w2:
            candidates.update(self.trigrams.get(f"{w1.lower()} {w2.lower()}", {}).keys())
        if w2:
            candidates.update((self.transitions.get(w2) or self.transitions.get(w2.lower(), {})).keys())

        if len(candidates) < limit:
            if self._top_cache is None:
                self._top_cache = [
                    w
                    for w, _ in sorted(self.word_counts.items(), key=lambda x: x[1], reverse=True)
                    if not is_numeric_or_symbol_token(w)
                ][:20]
            ctx_is_fa = is_persian_script_token(w2)
            w2_low = w2.lower()
            for top_w in self._top_cache:
                if top_w.lower() == w2_low:
                    continue
                if is_persian_script_token(top_w) != ctx_is_fa:
                    continue
                candidates.add(top_w)
                if len(candidates) >= limit + 5:
                    break

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
        """Export learned vocabulary, n-grams, and app profiles as a citable artifact."""
        top_words = [
            w for w, _ in sorted(self.word_counts.items(), key=lambda it: it[1], reverse=True)[:10]
        ]
        stats = {
            "total_words": len(self.word_counts),
            "total_bigrams": sum(len(v) for v in self.transitions.values()),
            "total_trigrams": sum(len(v) for v in self.trigrams.values()),
            "apps_tracked": len(self.app_word_counts),
            "decay_half_life_days": self.half_life_days,
            "top_words": top_words,
        }
        data: dict[str, Any] = {
            "artifact": "ravaan_learning_profile",
            "version": 3,
            "exported_at": time.time(),
            "last_decay_time": self.last_decay_time,
            "stats": stats,
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
            try:
                fv = float(v)
            except (ValueError, TypeError):
                continue
            self.word_counts[str(k)] = self.word_counts.get(str(k), 0.0) + fv
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
                        try:
                            fv = float(v)
                        except (ValueError, TypeError):
                            continue
                        m[str(nk)] = m.get(str(nk), 0.0) + fv

        return count

    def clear_learned_data(self) -> None:
        """Clear all user learned vocabulary, transitions, trigrams, and per-app weights."""
        self.word_counts.clear()
        self.transitions.clear()
        self.trigrams.clear()
        self.app_word_counts.clear()
        self._top_cache = None
        self._seed_defaults()
        self.save()

    def list_learned_words(
        self,
        query: str = "",
        limit: int = 100,
        app_name: str | None = None,
    ) -> list[tuple[str, float]]:
        """Return top learned words matching optional query/app filter, highest weight first."""
        q = normalize_arabic_chars(query or "").strip().lower()
        results: list[tuple[str, float]] = []
        if app_name:
            source_words = self.app_word_counts.get(app_name.strip().lower(), {})
            for word, count in source_words.items():
                if count <= 0:
                    continue
                if q and q not in normalize_arabic_chars(word).lower():
                    continue
                results.append((word, float(count)))
        else:
            for word, count in self.word_counts.items():
                if count <= 0:
                    continue
                if q and q not in normalize_arabic_chars(word).lower():
                    continue
                results.append((word, float(count)))
        results.sort(key=lambda item: (-item[1], item[0]))
        return results[: max(1, limit)]

    def forget_word(self, word: str, save_now: bool = True) -> bool:
        """Remove a learned word from vocabulary, per-app counts, bigrams, and trigrams."""
        clean = word.strip()
        if not clean:
            return False
        targets = {clean, clean.lower(), normalize_arabic_chars(clean), normalize_arabic_chars(clean).lower()}
        removed = False

        def _matches(key: str) -> bool:
            k_norm = normalize_arabic_chars(key).strip()
            return key in targets or key.lower() in targets or k_norm in targets or k_norm.lower() in targets

        for wk in [k for k in self.word_counts if _matches(k)]:
            del self.word_counts[wk]
            removed = True

        for app_key in list(self.app_word_counts.keys()):
            app_map = self.app_word_counts[app_key]
            for wk in [k for k in app_map if _matches(k)]:
                del app_map[wk]
                removed = True
            if not app_map:
                del self.app_word_counts[app_key]

        for pk in list(self.transitions.keys()):
            if _matches(pk):
                del self.transitions[pk]
                removed = True
                continue
            sub = self.transitions[pk]
            for nk in [k for k in sub if _matches(k)]:
                del sub[nk]
                removed = True
            if not sub:
                del self.transitions[pk]

        for tk in list(self.trigrams.keys()):
            parts = tk.split(" ", 1)
            if any(_matches(p) for p in parts):
                del self.trigrams[tk]
                removed = True
                continue
            sub = self.trigrams[tk]
            for nk in [k for k in sub if _matches(k)]:
                del sub[nk]
                removed = True
            if not sub:
                del self.trigrams[tk]

        if removed:
            self._top_cache = None
            self._dirty = True
            if save_now:
                self.save()
        return removed

    def exclude_word(self, word: str, cfg: Any | None = None, save_now: bool = True) -> bool:
        """Forget word from learning model and add it to Config.ignored_words when provided."""
        clean = word.strip()
        if not clean:
            return False
        forgot = self.forget_word(clean, save_now=save_now)
        added_ignore = False
        if cfg is not None and hasattr(cfg, "ignored_words"):
            existing = {str(w).strip().lower() for w in cfg.ignored_words}
            if clean.lower() not in existing:
                cfg.ignored_words.append(clean)
                added_ignore = True
        return forgot or added_ignore

    def import_corpus_text(
        self,
        text: str,
        *,
        app_name: str | None = None,
        min_len: int = 2,
        max_words: int = 25000,
        save_now: bool = True,
    ) -> dict[str, int]:
        """Learn words, bigrams, and trigrams from plain text without crossing sentences."""
        if not text or not text.strip():
            return {"words_added": 0, "unique_words": 0, "transitions_added": 0, "trigrams_added": 0}

        cleaned_text = _CORPUS_URL_EMAIL_RE.sub(" ", text)
        prev_enabled = self.learning_enabled
        self.learning_enabled = True
        words_added = 0
        transitions_added = 0
        trigrams_added = 0
        unique_seen: set[str] = set()

        try:
            for segment in _CORPUS_SENTENCE_SPLIT_RE.split(cleaned_text):
                if words_added >= max_words:
                    break
                tokens: list[str] = []
                for raw_tok in _CORPUS_TOKEN_RE.findall(segment):
                    tok = raw_tok.strip("\u200c'’-")
                    if any("\u0600" <= c <= "\u06ff" for c in tok):
                        tok = normalize_arabic_chars(tok)
                    if len(tok) < min_len:
                        continue
                    if tok.isdigit() or all(c in "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩" for c in tok):
                        continue
                    tokens.append(tok)
                    if words_added + len(tokens) >= max_words:
                        break

                app_key = app_name.strip().lower() if app_name else ""
                app_map = self.app_word_counts.setdefault(app_key, {}) if app_key else None
                for idx, tok in enumerate(tokens):
                    self.word_counts[tok] = self.word_counts.get(tok, 0.0) + 1.0
                    if app_map is not None:
                        app_map[tok] = app_map.get(tok, 0.0) + 1.0
                    words_added += 1
                    unique_seen.add(tok)
                    if idx >= 1:
                        prev_w = tokens[idx - 1]
                        trans = self.transitions.setdefault(prev_w, {})
                        trans[tok] = trans.get(tok, 0.0) + 1.0
                        transitions_added += 1
                    if idx >= 2:
                        k1, k2 = tokens[idx - 2].lower(), tokens[idx - 1].lower()
                        tri_map = self.trigrams.setdefault(f"{k1} {k2}", {})
                        tri_map[tok] = tri_map.get(tok, 0.0) + 1.0
                        trigrams_added += 1

            if words_added > 0:
                self._top_cache = None
                self._dirty = True
                if save_now:
                    self.save()
        finally:
            self.learning_enabled = prev_enabled

        return {
            "words_added": words_added,
            "unique_words": len(unique_seen),
            "transitions_added": transitions_added,
            "trigrams_added": trigrams_added,
        }

    def import_corpus_file(
        self,
        source_path: str | Path,
        *,
        app_name: str | None = None,
        max_bytes: int = 2_000_000,
        save_now: bool = True,
    ) -> dict[str, int]:
        """Read a plain text corpus file (UTF-8 / UTF-8-SIG / Windows-1256) and learn from it."""
        path = Path(source_path)
        if not path.is_file():
            raise FileNotFoundError(f"Corpus file not found: {path}")
        raw_bytes = path.read_bytes()[:max_bytes]
        text = ""
        for enc in ("utf-8-sig", "utf-8", "cp1256"):
            try:
                text = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if not text and raw_bytes:
            text = raw_bytes.decode("utf-8", errors="ignore")
        return self.import_corpus_text(text, app_name=app_name, save_now=save_now)

    def save(self, lazy: bool = False) -> None:
        if lazy:
            # Defer: skip the write when one happened recently; flush() persists later.
            if time.monotonic() - self._last_save_at < self._lazy_save_interval:
                self._dirty = True
                return
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.storage_path.with_suffix(".tmp")
            raw_json = json.dumps(self.export_profile(), ensure_ascii=False, indent=2)
            from ravan.core.crypto import protect_secret

            encrypted = protect_secret(raw_json)
            tmp.write_text(encrypted, encoding="utf-8")
            tmp.replace(self.storage_path)
            self._dirty = False
            self._last_save_at = time.monotonic()
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to save user learning model: %s", exc)

    def flush(self) -> None:
        """Persist deferred (lazy) changes immediately if any are pending."""
        if self._dirty:
            self.save()

    def _load(self) -> None:
        if not self.storage_path.is_file():
            return
        try:
            text = self.storage_path.read_text(encoding="utf-8").strip()
            if not text:
                return
            from ravan.core.crypto import DPAPI_PREFIX, MOCK_PREFIX, unprotect_secret

            if text.startswith((DPAPI_PREFIX, MOCK_PREFIX)):
                decrypted, _ = unprotect_secret(text)
                data = json.loads(decrypted)
            else:
                data = json.loads(text)
            self.import_profile(data, merge=True)
            self.last_decay_time = float(data.get("last_decay_time", time.time()))
            self.decay_frequencies(half_life_days=self.half_life_days)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to load user learning model: %s", exc)


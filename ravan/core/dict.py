"""Dictionary module — word-frequency lists and fuzzy matching."""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from enum import Enum, auto


class Language(Enum):
    ENGLISH = auto()
    PERSIAN = auto()


@dataclass(frozen=True)
class DictEntry:
    word: str
    rank: int  # 1 = most common, 0 = top priority custom word
    frequency: int = 0


def levenshtein(a: str, b: str, max_dist: int | None = None) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    # Band optimization: skip rows that cannot beat max_dist
    if max_dist is not None and abs(len(a) - len(b)) > max_dist:
        return max_dist + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        best = i
        for j, cb in enumerate(b, 1):
            ins = curr[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (ca != cb)
            d = min(ins, delete, sub)
            curr.append(d)
            if d < best:
                best = d
        if max_dist is not None and best > max_dist:
            return max_dist + 1
        prev = curr
    return prev[-1]


def osa_distance(a: str, b: str, max_dist: int | None = None) -> int:
    """Optimal string alignment distance (Damerau-Levenshtein restricted).

    Counts transpositions (e.g. "teh" → "the") as a single edit, which is
    what users expect from typo correction.
    """
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if not a:
        return lb
    if not b:
        return la
    if max_dist is not None and abs(la - lb) > max_dist:
        return max_dist + 1
    prev2: list[int] | None = None
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        curr = [i] + [0] * lb
        best = i
        ca = a[i - 1]
        for j in range(1, lb + 1):
            cb = b[j - 1]
            cost = 0 if ca == cb else 1
            d = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
            if (
                i > 1
                and j > 1
                and ca == b[j - 2]
                and a[i - 2] == cb
            ):
                assert prev2 is not None
                d = min(d, prev2[j - 2] + 1)
            curr[j] = d
            if d < best:
                best = d
        if max_dist is not None and best > max_dist:
            return max_dist + 1
        prev2 = prev
        prev = curr
    return prev[lb]


def load_dictionary_entries(filename_or_path: str) -> list[DictEntry]:
    """Load words and optional frequencies from an external UTF-8 file.

    Format per line:
      word
      OR
      word<TAB>frequency
    """
    from pathlib import Path

    path = Path(filename_or_path)
    if not path.is_file():
        # Search ravan/data
        data_dir = Path(__file__).resolve().parent.parent / "data"
        candidate = data_dir / filename_or_path
        if candidate.is_file():
            path = candidate
        else:
            # Search repository root data/
            repo_data = Path(__file__).resolve().parent.parent.parent / "data"
            candidate = repo_data / filename_or_path
            if candidate.is_file():
                path = candidate
            else:
                return []

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []

    raw_items: list[tuple[str, int | None, int]] = []
    seen: set[str] = set()

    for idx, line in enumerate(lines):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" in line:
            parts = line.split("\t", 1)
            word = parts[0].strip()
            try:
                freq: int | None = int(parts[1].strip())
            except ValueError:
                freq = None
        else:
            parts = line.split()
            if len(parts) >= 2 and parts[-1].isdigit():
                word = " ".join(parts[:-1]).strip()
                freq = int(parts[-1])
            else:
                word = line
                freq = None

        if not word:
            continue
        key = word.lower()
        if key in seen:
            continue
        seen.add(key)
        raw_items.append((word, freq, idx))

    has_frequency = any(f is not None for _, f, _ in raw_items)
    if has_frequency:
        raw_items.sort(
            key=lambda it: (it[1] is not None, it[1] if it[1] is not None else 0, -it[2]),
            reverse=True,
        )

    return [
        DictEntry(word=w, rank=rank, frequency=freq if freq is not None else 0)
        for rank, (w, freq, _) in enumerate(raw_items, 1)
    ]


class Dictionary:
    def __init__(self, entries: list[DictEntry], language: Language) -> None:
        self.entries = list(entries)
        self.language = language
        self._lower = {e.word.lower(): e for e in entries}
        # Sorted-by-length index for fast fuzzy candidate scan
        self._by_len: dict[int, list[tuple[DictEntry, str]]] = {}
        for e in entries:
            self._by_len.setdefault(len(e.word), []).append((e, e.word.lower()))

        sorted_pairs = sorted(((e.word.lower(), e) for e in entries), key=lambda p: p[0])
        self._sorted_keys = [p[0] for p in sorted_pairs]
        self._sorted_entries = [p[1] for p in sorted_pairs]

    def add_word(self, word: str, priority: bool = True) -> None:
        """Add a dynamic word to the dictionary in-memory."""
        clean = word.strip()
        if not clean:
            return
        key = clean.lower()
        if key in self._lower:
            if priority and self._lower[key].rank != 0:
                old = self._lower[key]
                new_entry = DictEntry(word=clean, rank=0, frequency=max(old.frequency, 10000000))
                self._lower[key] = new_entry
                try:
                    self.entries.remove(old)
                except ValueError:
                    pass
                self.entries.insert(0, new_entry)
                idx = bisect.bisect_left(self._sorted_keys, key)
                if idx < len(self._sorted_keys) and self._sorted_keys[idx] == key:
                    self._sorted_entries[idx] = new_entry
            return

        rank = 0 if priority else len(self.entries) + 1
        entry = DictEntry(word=clean, rank=rank, frequency=10000000 if priority else 1)
        if priority:
            self.entries.insert(0, entry)
        else:
            self.entries.append(entry)
        self._lower[key] = entry
        self._by_len.setdefault(len(clean), []).append((entry, key))
        idx = bisect.bisect_left(self._sorted_keys, key)
        self._sorted_keys.insert(idx, key)
        self._sorted_entries.insert(idx, entry)

    @classmethod
    def english(cls) -> Dictionary:
        entries = load_dictionary_entries("words_en.txt")
        if not entries:
            entries = [
                DictEntry(word=w, rank=i + 1)
                for i, w in enumerate(_dedupe(_ENGLISH_WORDS))
            ]
        return cls(entries, Language.ENGLISH)

    @classmethod
    def persian(cls) -> Dictionary:
        entries = load_dictionary_entries("words_fa.txt")
        if not entries:
            entries = [
                DictEntry(word=w, rank=i + 1)
                for i, w in enumerate(_dedupe(_PERSIAN_WORDS))
            ]
        return cls(entries, Language.PERSIAN)

    def completions(self, prefix: str, limit: int) -> list[DictEntry]:
        prefix_lower = prefix.lower()
        if not prefix_lower:
            return self.entries[:limit]
        idx = bisect.bisect_left(self._sorted_keys, prefix_lower)
        matches: list[DictEntry] = []
        n = len(self._sorted_keys)
        while idx < n and self._sorted_keys[idx].startswith(prefix_lower):
            matches.append(self._sorted_entries[idx])
            idx += 1
        matches.sort(key=lambda e: e.rank)
        return matches[:limit]

    def fuzzy_matches(
        self, word: str, max_dist: int, limit: int
    ) -> list[tuple[DictEntry, int]]:
        word_lower = word.lower()
        n = len(word_lower)
        matches: list[tuple[DictEntry, int]] = []
        # Only compare against words within the edit-distance length window
        for ln in range(max(1, n - max_dist), n + max_dist + 1):
            for e, w_low in self._by_len.get(ln, ()):
                if e.rank > 3000:
                    continue
                dist = osa_distance(w_low, word_lower, max_dist=max_dist)
                if 0 < dist <= max_dist:
                    matches.append((e, dist))
        matches.sort(key=lambda t: (t[1], t[0].rank))
        return matches[:limit]

    def contains(self, word: str) -> bool:
        return word.lower() in self._lower

    def rank_of(self, word: str) -> int | None:
        entry = self._lower.get(word.lower())
        return entry.rank if entry else None


def _dedupe(words: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for w in words:
        key = w.lower()
        if key not in seen:
            seen.add(key)
            out.append(w)
    return out


_ENGLISH_WORDS: list[str] = [
    # top function words
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "it",
    "for", "not", "on", "with", "he", "as", "you", "do", "at", "this",
    "but", "his", "by", "from", "they", "we", "say", "her", "she", "or",
    "an", "will", "my", "one", "all", "would", "there", "their", "what",
    "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
    "when", "make", "can", "like", "time", "no", "just", "him", "know",
    "take", "people", "into", "year", "your", "good", "some", "could",
    "them", "see", "other", "than", "then", "now", "look", "only", "come",
    "its", "over", "think", "also", "back", "after", "use", "two", "how",
    "our", "work", "first", "well", "way", "even", "new", "want", "because",
    "any", "these", "give", "day", "most", "us",
    # common verbs / nouns / adjectives
    "is", "are", "was", "were", "been", "being", "am", "has", "had",
    "does", "did", "doing", "said", "says", "going", "got", "made",
    "great", "large", "often", "hand", "high", "place", "hold", "today",
    "bring", "point", "world", "build", "house", "water", "night", "life",
    "child", "children", "family", "friend", "group", "country", "city",
    "school", "student", "teacher", "word", "book", "page", "line",
    "part", "case", "number", "name", "question", "answer", "example",
    "problem", "program", "process", "product", "project", "public",
    "purpose", "quality", "price", "print", "private", "present",
    "pretty", "protect", "prove", "provide", "quick", "quiet", "quite",
    "read", "ready", "real", "reason", "receive", "recent", "record",
    "red", "reduce", "remain", "remember", "remove", "report", "represent",
    "request", "require", "research", "result", "return", "right", "rise",
    "road", "role", "room", "run", "safe", "same", "second", "service",
    "set", "show", "simple", "since", "small", "something", "sometimes",
    "soon", "sound", "special", "stand", "start", "state", "still",
    "stop", "study", "such", "support", "system", "table", "tell",
    "thing", "think", "through", "together", "too", "town", "true",
    "turn", "type", "under", "until", "value", "very", "view", "want",
    "water", "whole", "write", "year", "yet", "young", "hello", "thanks",
    "please", "welcome", "sorry", "morning", "evening", "today",
    "tomorrow", "yesterday", "week", "month", "hour", "minute",
    "computer", "keyboard", "screen", "file", "folder", "window",
    "email", "message", "phone", "meeting", "office", "company", "team",
    "manager", "money", "price", "market", "report", "data", "code",
    "test", "user", "website", "internet", "software", "hardware",
    "language", "english", "persian", "farsi", "iran", "tehran",
    "beautiful", "better", "best", "big", "black", "blue", "brown",
    "clean", "clear", "cold", "dark", "difficult", "easy", "fast",
    "free", "full", "funny", "happy", "hard", "hot", "important",
    "interesting", "kind", "light", "little", "long", "loud", "low",
    "nice", "old", "open", "polite", "rich", "short", "slow", "smart",
    "strong", "sweet", "tall", "warm", "weak", "white", "wrong",
]

_PERSIAN_WORDS: list[str] = [
    "و", "در", "به", "از", "که", "این", "را", "با", "است", "آن",
    "یک", "هم", "می", "شد", "او", "ما", "اما", "یا", "بر", "همه",
    "باید", "کرد", "شود", "برای", "هر", "تا", "من", "بود", "نیست",
    "داد", "چه", "دارد", "نه", "بین", "مورد", "نظر", "پس", "حتی",
    "روز", "بار", "مردم", "کار", "سال", "جا", "دو", "نیز", "پیش",
    "وی", "شده", "دارند", "بسیار", "چون", "خود", "دهد",
    "ولی", "طور", "وقتی", "قبل", "البته", "آنها", "بنابراین", "آنچه",
    "هنوز", "دیگر", "کنند", "اگر", "ممکن", "واقع", "کنیم", "چند",
    "خوب", "بزرگ", "کوچک", "جدید", "قدیم", "اول", "آخر", "زیاد",
    "کم", "زود", "دیر", "خیلی", "تنها", "درست", "نادرست", "مهم",
    "دولت", "ملت", "کشور", "شهر", "خانه", "کتاب", "دانشگاه",
    "ایران", "تهران", "اطلاعات", "ارتباط", "توسعه", "برنامه", "سیستم",
    "خورد", "سلام", "خداحافظ", "ممنون", "لطفا", "مرسی", "علیک",
    "سلام علیکم", "صبح", "شب", "ظهر", "امروز", "فردا", "دیروز",
    "هفته", "ماه", "سال", "ساعت", "دقیقه", "ثانیه", "وقت",
    "آب", "نان", "برنج", "گوشت", "مرغ", "ماهی", "میوه", "سیب",
    "پرتقال", "انگور", "هویج", "پیاز", "سیب‌زمینی", "چای", "قهوه",
    "شیر", "شکر", "نمک", "روغن", "گل", "درخت", "آسمان", "زمین",
    "خورشید", "ماه", "ستاره", "دریا", "کوه", "جنگل", "باران",
    "برف", "باد", "آتش", "خاک", "هوا", "زندگی", "مرگ", "عشق",
    "دوست", "دشمن", "برادر", "خواهر", "پدر", "مادر", "فرزند",
    "دختر", "پسر", "مرد", "زن", "بچه", "اسم", "فرد", "انسان",
    "زمان", "ساعت", "مکان", "راه", "خیابان", "کوچه", "ماشین",
    "هواپیما", "قطار", "اتوبوس", "دوچرخه", "کفش", "لباس", "پیراهن",
    "شلوار", "کلاه", "دست", "پا", "سر", "چشم", "گوش", "دهان",
    "بینی", "مو", "قلب", "مغز", "خون", "زبان", "دندان",
    "مدرسه", "کلاس", "معلم", "دانشجو", "استاد", "درس", "امتحان",
    "نمره", "دفتر", "مداد", "خودکار", "تخته", "کاغذ", "زنگ",
    "دین", "مسجد", "نماز", "قرآن", "خدا", "پیامبر", "دعا",
    "عید", "جشن", "عروسی", "مهمانی", "هدیه", "کادو", "شادی",
    "غصه", "ترس", "امید", "آرزو", "خوشحال", "ناراحت", "خسته",
    "عصبانی", "آرام", "شاد", "غمگین", "سریع", "آهسته", "گرم",
    "سرد", "خوشگل", "زیبا", "بد", "تمیز", "کثیف", "سنگین",
    "سبک", "نو", "کهنه",     "همیشه", "هرگز", "گاهی", "دوباره",
    "همین", "الان", "بعدا", "چیزی", "کسی", "جایی", "هیچ",
    "چطور", "چرا", "کجا", "کی", "چندتا", "بله",
    "باشه", "اجازه", "شرمنده", "متاسفانه",
    "خواهش", "قابل", "ندارد", "فدات", "شما", "تو",
    "ایشان", "اینها", "خودم", "خودت", "خودش",
]

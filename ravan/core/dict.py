"""Dictionary module — word-frequency lists and fuzzy matching."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class Language(Enum):
    ENGLISH = auto()
    PERSIAN = auto()


@dataclass(frozen=True)
class DictEntry:
    word: str
    rank: int  # 1 = most common


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


def _load_asset_words(filename: str) -> list[str]:
    from pathlib import Path
    data_dir = Path(__file__).resolve().parent.parent / "data"
    asset_path = data_dir / filename
    if asset_path.is_file():
        try:
            lines = asset_path.read_text(encoding="utf-8").splitlines()
            return [w.strip() for w in lines if w.strip() and not w.startswith("#")]
        except Exception:
            pass
    return []


class Dictionary:
    def __init__(self, entries: list[DictEntry], language: Language) -> None:
        self.entries = entries
        self.language = language
        self._lower = {e.word.lower(): e for e in entries}
        # Sorted-by-length index for fast fuzzy candidate scan
        self._by_len: dict[int, list[DictEntry]] = {}
        for e in entries:
            self._by_len.setdefault(len(e.word), []).append(e)

    @classmethod
    def english(cls) -> Dictionary:
        words = _load_asset_words("words_en.txt") or _ENGLISH_WORDS
        entries = [
            DictEntry(word=w, rank=i + 1)
            for i, w in enumerate(_dedupe(words))
        ]
        return cls(entries, Language.ENGLISH)

    @classmethod
    def persian(cls) -> Dictionary:
        words = _load_asset_words("words_fa.txt") or _PERSIAN_WORDS
        entries = [
            DictEntry(word=w, rank=i + 1)
            for i, w in enumerate(_dedupe(words))
        ]
        return cls(entries, Language.PERSIAN)

    def completions(self, prefix: str, limit: int) -> list[DictEntry]:
        prefix_lower = prefix.lower()
        matches = [
            e for e in self.entries if e.word.lower().startswith(prefix_lower)
        ]
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
            for e in self._by_len.get(ln, ()):
                dist = osa_distance(e.word.lower(), word_lower, max_dist=max_dist)
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

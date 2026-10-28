"""Dictionary module — word-frequency lists and fuzzy matching."""

from __future__ import annotations

import bisect
import logging
import mmap
import os
import struct
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

MAGIC = b"RVN2"


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


def compile_dict_binary(txt_path: str | Path, bin_path: str | Path) -> int:
    """Compile a words_<lang>.txt file into words_<lang>.bin."""
    txt = Path(txt_path)
    out = Path(bin_path)

    if not txt.is_file():
        raise FileNotFoundError(f"Input dictionary text file not found: {txt}")

    lines = txt.read_text(encoding="utf-8").splitlines()
    raw_entries: list[tuple[str, int, int]] = []
    seen: set[str] = set()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" in line:
            parts = line.split("\t", 1)
            word = parts[0].strip()
            try:
                freq = int(parts[1].strip())
            except ValueError:
                freq = 0
        else:
            parts = line.split()
            if len(parts) >= 2 and parts[-1].isdigit():
                word = " ".join(parts[:-1]).strip()
                freq = int(parts[-1])
            else:
                word = line
                freq = 0

        if not word:
            continue
        key = word.lower()
        if key in seen:
            continue
        seen.add(key)
        raw_entries.append((word, freq, len(raw_entries)))

    has_frequency = any(f > 0 for _, f, _ in raw_entries)
    if has_frequency:
        raw_entries.sort(key=lambda it: (it[1], -it[2]), reverse=True)

    ranked_entries = [
        (word, rank, freq)
        for rank, (word, freq, _) in enumerate(raw_entries, 1)
    ]

    count = len(ranked_entries)
    tmp_out = out.with_suffix(".tmp")
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(tmp_out, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<III", count, 2, 0))

        table_alpha_pos = f.tell()
        f.write(b"\x00" * (count * 4))
        table_rank_pos = f.tell()
        f.write(b"\x00" * (count * 4))

        rank_offsets: list[int] = []
        indexed_items: list[tuple[str, int]] = []
        for word, rank, freq in ranked_entries:
            offset = f.tell()
            rank_offsets.append(offset)
            indexed_items.append((word.lower(), offset))
            w_bytes = word.encode("utf-8")
            if len(w_bytes) > 255:
                w_bytes = w_bytes[:255]
            f.write(struct.pack("<IIB", rank, freq, len(w_bytes)))
            f.write(w_bytes)

        indexed_items.sort(key=lambda it: it[0])
        alpha_offsets = [it[1] for it in indexed_items]

        f.seek(table_alpha_pos)
        f.write(struct.pack(f"<{count}I", *alpha_offsets))
        f.seek(table_rank_pos)
        f.write(struct.pack(f"<{count}I", *rank_offsets))

    if out.exists():
        os.remove(out)
    os.rename(tmp_out, out)
    return count


class _MmapEntriesSequence(Sequence[DictEntry]):
    """Zero-copy lazy sequence of DictEntry objects backed by memory-mapped RVN2."""

    def __init__(self, dictionary: Dictionary) -> None:
        self._d = dictionary

    def __len__(self) -> int:
        overlay_len = len(self._d._overlay)
        return self._d._count + overlay_len

    def __getitem__(self, index: int | slice) -> Any:
        total = len(self)
        if isinstance(index, slice):
            start, stop, step = index.indices(total)
            return [self[i] for i in range(start, stop, step)]
        if index < 0:
            index += total
        if index < 0 or index >= total:
            raise IndexError("Dictionary index out of range")

        ov_list = list(self._d._overlay.values())
        if index < len(ov_list):
            return ov_list[index]

        mmap_idx = index - len(ov_list)
        mm = self._d._mmap
        assert mm is not None
        table2_pos = 16 + self._d._count * 4
        off = struct.unpack_from("<I", mm, table2_pos + mmap_idx * 4)[0]
        rank, freq, wlen = struct.unpack_from("<IIB", mm, off)
        w = mm[off + 9 : off + 9 + wlen].decode("utf-8")
        return DictEntry(word=w, rank=rank, frequency=freq)

    def __iter__(self) -> Iterator[DictEntry]:
        yield from self._d._overlay.values()
        mm = self._d._mmap
        if mm is not None:
            count = self._d._count
            table2_pos = 16 + count * 4
            for i in range(count):
                off = struct.unpack_from("<I", mm, table2_pos + i * 4)[0]
                rank, freq, wlen = struct.unpack_from("<IIB", mm, off)
                w = mm[off + 9 : off + 9 + wlen].decode("utf-8")
                yield DictEntry(word=w, rank=rank, frequency=freq)


_PERSIAN_ZWNJ_PREFIXES: tuple[str, ...] = ("می\u200c", "نمی\u200c", "بی\u200c")
_PERSIAN_ZWNJ_SUFFIXES: tuple[str, ...] = (
    "\u200cهایمان",
    "\u200cهایتان",
    "\u200cهایشان",
    "\u200cهایی",
    "\u200cهایم",
    "\u200cهایت",
    "\u200cهایش",
    "\u200cترین",
    "\u200cهای",
    "\u200cمان",
    "\u200cتان",
    "\u200cشان",
    "\u200cها",
    "\u200cتر",
    "\u200cام",
    "\u200cات",
    "\u200cاش",
    "\u200cای",
    "\u200cاست",
    "\u200cیم",
    "\u200cید",
    "\u200cاند",
)


class Dictionary:
    def __init__(
        self,
        entries: list[DictEntry] | None = None,
        language: Language = Language.ENGLISH,
        _mmap_info: tuple[mmap.mmap, int, Any] | None = None,
    ) -> None:
        self.language = language
        self._overlay: dict[str, DictEntry] = {}
        self._overlay_by_len: dict[int, list[tuple[DictEntry, str]]] = {}
        self._mmap: mmap.mmap | None = None
        self._count: int = 0
        self._file_handle: Any = None
        self._top_cached_by_len: dict[int, list[tuple[DictEntry, str]]] | None = None
        self._single_char_top: dict[str, list[DictEntry]] | None = None
        self._completions_cache: dict[tuple[str, int], list[DictEntry]] = {}

        if _mmap_info is not None:
            self._mmap, self._count, self._file_handle = _mmap_info
            self._entries_seq: Sequence[DictEntry] = _MmapEntriesSequence(self)
        elif entries is not None:
            self._entries_list: list[DictEntry] = list(entries)
            self._lower: dict[str, DictEntry] = {e.word.lower(): e for e in entries}
            self._by_len: dict[int, list[tuple[DictEntry, str]]] = {}
            for e in entries:
                self._by_len.setdefault(len(e.word), []).append((e, e.word.lower()))
            sorted_pairs = sorted(((e.word.lower(), e) for e in entries), key=lambda p: p[0])
            self._sorted_keys = [p[0] for p in sorted_pairs]
            self._sorted_entries = [p[1] for p in sorted_pairs]
            self._entries_seq = self._entries_list
        else:
            self._entries_list = []
            self._lower = {}
            self._by_len = {}
            self._sorted_keys = []
            self._sorted_entries = []
            self._entries_seq = self._entries_list

    def __len__(self) -> int:
        return self._count if self._mmap is not None else len(self._entries_list)

    @property
    def entries(self) -> Sequence[DictEntry]:
        return self._entries_seq

    @entries.setter
    def entries(self, value: Sequence[DictEntry]) -> None:
        self._completions_cache.clear()
        if isinstance(value, list):
            self._entries_list = value
            self._entries_seq = value
            self._lower = {e.word.lower(): e for e in value}
            self._by_len = {}
            for e in value:
                self._by_len.setdefault(len(e.word), []).append((e, e.word.lower()))
            sorted_pairs = sorted(((e.word.lower(), e) for e in value), key=lambda p: p[0])
            self._sorted_keys = [p[0] for p in sorted_pairs]
            self._sorted_entries = [p[1] for p in sorted_pairs]

    def close(self) -> None:
        if self._mmap is not None:
            try:
                self._mmap.close()
            except Exception:
                pass
            self._mmap = None
        if self._file_handle is not None:
            try:
                self._file_handle.close()
            except Exception:
                pass
            self._file_handle = None

    def __del__(self) -> None:
        self.close()

    def add_word(self, word: str, priority: bool = True) -> None:
        """Add a dynamic word to the dictionary in-memory."""
        clean = word.strip()
        if not clean:
            return
        self._completions_cache.clear()
        key = clean.lower()

        if self._mmap is not None:
            rank = 0 if priority else len(self._entries_seq) + 1
            entry = DictEntry(word=clean, rank=rank, frequency=10000000 if priority else 1)
            self._overlay[key] = entry
            self._overlay_by_len.setdefault(len(clean), []).append((entry, key))
            return

        if key in self._lower:
            if priority and self._lower[key].rank != 0:
                old = self._lower[key]
                new_entry = DictEntry(word=clean, rank=0, frequency=max(old.frequency, 10000000))
                self._lower[key] = new_entry
                try:
                    self._entries_list.remove(old)
                except ValueError:
                    pass
                self._entries_list.insert(0, new_entry)
                idx = bisect.bisect_left(self._sorted_keys, key)
                if idx < len(self._sorted_keys) and self._sorted_keys[idx] == key:
                    self._sorted_entries[idx] = new_entry
            return

        rank = 0 if priority else len(self._entries_list) + 1
        entry = DictEntry(word=clean, rank=rank, frequency=10000000 if priority else 1)
        if priority:
            self._entries_list.insert(0, entry)
        else:
            self._entries_list.append(entry)
        self._lower[key] = entry
        self._by_len.setdefault(len(clean), []).append((entry, key))
        idx = bisect.bisect_left(self._sorted_keys, key)
        self._sorted_keys.insert(idx, key)
        self._sorted_entries.insert(idx, entry)

    @classmethod
    def from_binary(cls, bin_path: str | Path, language: Language) -> Dictionary:
        path = Path(bin_path)
        if not path.is_file():
            raise FileNotFoundError(f"Binary dictionary not found: {path}")
        f = open(path, "rb")
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        if mm[:4] != MAGIC:
            mm.close()
            f.close()
            raise ValueError(f"Invalid binary dictionary format in {path}")
        count = struct.unpack_from("<I", mm, 4)[0]
        return cls(language=language, _mmap_info=(mm, count, f))

    @classmethod
    def english(cls) -> Dictionary:
        return cls._load_auto("words_en", Language.ENGLISH, _ENGLISH_WORDS)

    @classmethod
    def persian(cls) -> Dictionary:
        return cls._load_auto("words_fa", Language.PERSIAN, _PERSIAN_WORDS)

    @classmethod
    def _load_auto(cls, stem: str, language: Language, fallback_words: list[str]) -> Dictionary:
        data_dir = Path(__file__).resolve().parent.parent / "data"
        bin_path = data_dir / f"{stem}.bin"
        txt_path = data_dir / f"{stem}.txt"

        if bin_path.is_file():
            if txt_path.is_file() and txt_path.stat().st_mtime > bin_path.stat().st_mtime:
                try:
                    compile_dict_binary(txt_path, bin_path)
                except Exception as ex:
                    log.warning("Failed to auto-recompile %s: %s", bin_path, ex)
            try:
                return cls.from_binary(bin_path, language)
            except Exception as ex:
                log.warning("Failed to mmap %s (%s), falling back to txt", bin_path, ex)

        if txt_path.is_file():
            try:
                compile_dict_binary(txt_path, bin_path)
                return cls.from_binary(bin_path, language)
            except Exception as ex:
                log.warning("Failed to compile binary dict %s: %s", bin_path, ex)
                entries = load_dictionary_entries(str(txt_path))
                return cls(entries, language)

        entries = [DictEntry(word=w, rank=i + 1) for i, w in enumerate(_dedupe(fallback_words))]
        return cls(entries, language)

    def _find_in_mmap(self, target_lower: str) -> DictEntry | None:
        if self._mmap is None or self._count == 0:
            return None
        mm = self._mmap
        low = 0
        high = self._count - 1
        while low <= high:
            mid = (low + high) // 2
            off = struct.unpack_from("<I", mm, 16 + mid * 4)[0]
            wlen = mm[off + 8]
            w = mm[off + 9 : off + 9 + wlen].decode("utf-8")
            wl = w.lower()
            if wl == target_lower:
                rank, freq = struct.unpack_from("<II", mm, off)
                return DictEntry(word=w, rank=rank, frequency=freq)
            elif wl < target_lower:
                low = mid + 1
            else:
                high = mid - 1
        return None

    def completions(self, prefix: str, limit: int) -> list[DictEntry]:
        prefix_lower = prefix.lower()
        cache_key = (prefix_lower, limit)
        if cache_key in self._completions_cache:
            return self._completions_cache[cache_key]

        if self._mmap is not None:
            res = self._completions_mmap(prefix_lower, limit)
        elif not prefix_lower:
            res = self._entries_list[:limit]
        else:
            idx = bisect.bisect_left(self._sorted_keys, prefix_lower)
            matches: list[DictEntry] = []
            n = len(self._sorted_keys)
            while idx < n and self._sorted_keys[idx].startswith(prefix_lower):
                matches.append(self._sorted_entries[idx])
                idx += 1
            matches.sort(key=lambda e: e.rank)
            res = matches[:limit]

        if len(self._completions_cache) < 1024:
            self._completions_cache[cache_key] = res
        return res

    def _ensure_single_char_top(self) -> dict[str, list[DictEntry]]:
        if self._single_char_top is None:
            self._single_char_top = {}
            if self._mmap is not None:
                mm = self._mmap
                count = self._count
                table2_pos = 16 + count * 4
                limit_scan = min(20000, count)
                for i in range(limit_scan):
                    off = struct.unpack_from("<I", mm, table2_pos + i * 4)[0]
                    rank, freq, wlen = struct.unpack_from("<IIB", mm, off)
                    w = mm[off + 9 : off + 9 + wlen].decode("utf-8")
                    first = w.lower()[:1]
                    lst = self._single_char_top.setdefault(first, [])
                    if len(lst) < 15:
                        lst.append(DictEntry(word=w, rank=rank, frequency=freq))
        return self._single_char_top

    def _completions_mmap(self, prefix_lower: str, limit: int) -> list[DictEntry]:
        mm = self._mmap
        assert mm is not None
        count = self._count
        table2_pos = 16 + count * 4

        if not prefix_lower:
            out: list[DictEntry] = list(self._overlay.values())
            for i in range(min(limit, count)):
                off = struct.unpack_from("<I", mm, table2_pos + i * 4)[0]
                rank, freq, wlen = struct.unpack_from("<IIB", mm, off)
                w = mm[off + 9 : off + 9 + wlen].decode("utf-8")
                out.append(DictEntry(word=w, rank=rank, frequency=freq))
            out.sort(key=lambda e: e.rank)
            return out[:limit]

        # For single-character prefix (e.g. 'س' or 't'), return top-frequency words
        # so the user gets instant, highly-relevant common words (e.g. سلام, سال, ساعت).
        if len(prefix_lower) == 1:
            matches: list[DictEntry] = []
            for ov_key, ov_entry in self._overlay.items():
                if ov_key.startswith(prefix_lower):
                    matches.append(ov_entry)
            single_map = self._ensure_single_char_top()
            cached_top = single_map.get(prefix_lower, [])
            for e in cached_top:
                if e not in matches:
                    matches.append(e)
            if len(matches) >= limit:
                matches.sort(key=lambda e: e.rank)
                return matches[:limit]

        low = 0
        high = count - 1
        first_idx = count
        while low <= high:
            mid = (low + high) // 2
            off = struct.unpack_from("<I", mm, 16 + mid * 4)[0]
            wlen = mm[off + 8]
            w = mm[off + 9 : off + 9 + wlen].decode("utf-8").lower()
            if w >= prefix_lower:
                first_idx = mid
                high = mid - 1
            else:
                low = mid + 1

        matches = []
        idx = first_idx
        # For prefixes of length >= 2, scan matching words in Table 1 up to 3500
        # so words aren't truncated alphabetically before sorting by rank.
        max_scan = 3500
        while idx < count:
            off = struct.unpack_from("<I", mm, 16 + idx * 4)[0]
            wlen = mm[off + 8]
            w = mm[off + 9 : off + 9 + wlen].decode("utf-8")
            if not w.lower().startswith(prefix_lower):
                break
            rank, freq = struct.unpack_from("<II", mm, off)
            matches.append(DictEntry(word=w, rank=rank, frequency=freq))
            idx += 1
            if len(matches) >= max_scan:
                break

        for ov_key, ov_entry in self._overlay.items():
            if ov_key.startswith(prefix_lower) and ov_entry not in matches:
                matches.append(ov_entry)

        matches.sort(key=lambda e: e.rank)
        return matches[:limit]

    def _ensure_top_by_len(self) -> dict[int, list[tuple[DictEntry, str]]]:
        if self._top_cached_by_len is None:
            self._top_cached_by_len = {}
            if self._mmap is not None:
                mm = self._mmap
                count = self._count
                limit_top = min(3000, count)
                table2_pos = 16 + count * 4
                for i in range(limit_top):
                    off = struct.unpack_from("<I", mm, table2_pos + i * 4)[0]
                    rank, freq, wlen = struct.unpack_from("<IIB", mm, off)
                    w = mm[off + 9 : off + 9 + wlen].decode("utf-8")
                    e = DictEntry(word=w, rank=rank, frequency=freq)
                    self._top_cached_by_len.setdefault(len(w), []).append((e, w.lower()))
        return self._top_cached_by_len

    def fuzzy_matches(
        self, word: str, max_dist: int, limit: int
    ) -> list[tuple[DictEntry, int]]:
        word_lower = word.lower()
        n = len(word_lower)
        matches: list[tuple[DictEntry, int]] = []
        lens = sorted(range(max(1, n - max_dist), n + max_dist + 1), key=lambda x: abs(x - n))

        source_by_len = self._ensure_top_by_len() if self._mmap is not None else self._by_len

        for ln in lens:
            # Check overlay words
            for e, w_low in self._overlay_by_len.get(ln, ()):
                dist = osa_distance(w_low, word_lower, max_dist=max_dist)
                if 0 < dist <= max_dist:
                    matches.append((e, dist))

            # Check top vocabulary
            for e, w_low in source_by_len.get(ln, ()):
                if e.rank > 3000:
                    continue
                dist = osa_distance(w_low, word_lower, max_dist=max_dist)
                if 0 < dist <= max_dist:
                    matches.append((e, dist))
                    if len(matches) >= limit * 4:
                        break
            if len(matches) >= limit * 4:
                break
        matches.sort(key=lambda t: (t[1], t[0].rank))
        return matches[:limit]

    def _exact_contains(self, key: str) -> bool:
        if key in self._overlay:
            return True
        if self._mmap is not None:
            return self._find_in_mmap(key) is not None
        return key in self._lower

    def _exact_get(self, key: str) -> DictEntry | None:
        if key in self._overlay:
            return self._overlay[key]
        if self._mmap is not None:
            return self._find_in_mmap(key)
        return self._lower.get(key)

    def contains(self, word: str) -> bool:
        key = word.lower()
        if self._exact_contains(key):
            return True

        if "\u200c" in key:
            # 1. Joined form without ZWNJ (e.g. می‌کند -> میکند)
            joined = key.replace("\u200c", "")
            if self._exact_contains(joined):
                return True

            # 2. Verbal & privative prefixes (می‌رود -> رود, بی‌دلیل -> دلیل)
            for prefix in _PERSIAN_ZWNJ_PREFIXES:
                if key.startswith(prefix):
                    stem = key[len(prefix):]
                    if stem and (self._exact_contains(stem) or self._exact_contains(stem.replace("\u200c", ""))):
                        return True

            # 3. Standard suffixes (کتاب‌ها -> کتاب, کهن‌ترین -> کهن)
            for suffix in _PERSIAN_ZWNJ_SUFFIXES:
                if key.endswith(suffix):
                    base = key[:-len(suffix)]
                    if base and (self._exact_contains(base) or self._exact_contains(base.replace("\u200c", ""))):
                        return True

            # 4. Compound words: all components separated by ZWNJ are dictionary words (دوزبانه -> دو + زبانه)
            parts = key.split("\u200c")
            if len(parts) >= 2 and all(p and self._exact_contains(p) for p in parts):
                return True

        return False

    def get(self, word: str) -> DictEntry | None:
        key = word.lower()
        entry = self._exact_get(key)
        if entry is not None:
            return entry

        if "\u200c" in key:
            # 1. Joined form
            joined = key.replace("\u200c", "")
            joined_entry = self._exact_get(joined)
            if joined_entry is not None:
                return DictEntry(word=word, rank=joined_entry.rank, frequency=joined_entry.frequency)

            # 2. Verbal & privative prefixes
            for prefix in _PERSIAN_ZWNJ_PREFIXES:
                if key.startswith(prefix):
                    stem = key[len(prefix):]
                    stem_entry = self._exact_get(stem) or self._exact_get(stem.replace("\u200c", ""))
                    if stem_entry is not None:
                        return DictEntry(
                            word=word,
                            rank=stem_entry.rank + 500,
                            frequency=max(1, stem_entry.frequency // 2),
                        )

            # 3. Standard suffixes
            for suffix in _PERSIAN_ZWNJ_SUFFIXES:
                if key.endswith(suffix):
                    base = key[:-len(suffix)]
                    base_entry = self._exact_get(base) or self._exact_get(base.replace("\u200c", ""))
                    if base_entry is not None:
                        return DictEntry(
                            word=word,
                            rank=base_entry.rank + 200,
                            frequency=max(1, base_entry.frequency // 2),
                        )

            # 4. Compound words
            parts = key.split("\u200c")
            if len(parts) >= 2:
                part_entries = [self._exact_get(p) for p in parts]
                if all(e is not None for e in part_entries):
                    max_rank = max(e.rank for e in part_entries if e is not None)
                    min_freq = min(e.frequency for e in part_entries if e is not None)
                    return DictEntry(
                        word=word,
                        rank=max_rank + 1000,
                        frequency=max(1, min_freq // 4),
                    )

        return None

    def rank_of(self, word: str) -> int | None:
        entry = self.get(word)
        return entry.rank if entry is not None else None

    def __getitem__(self, word: str) -> DictEntry:
        entry = self.get(word)
        if entry is None:
            raise KeyError(word)
        return entry



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
    "دوزبانه", "دوطرفه", "دوجانبه",
]

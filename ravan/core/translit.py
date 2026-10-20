"""Transliteration engine: Finglish -> Persian script."""

from __future__ import annotations

import itertools
import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ravan.core.dict import Dictionary

log = logging.getLogger(__name__)

# Common Finglish digraphs & dipthongs
_DIGRAPHS: list[tuple[str, list[str]]] = [
    ("kh", ["خ"]),
    ("sh", ["ش"]),
    ("ch", ["چ"]),
    ("zh", ["ژ"]),
    ("gh", ["ق", "غ"]),
    ("ck", ["ک"]),
    ("ph", ["ف"]),
    ("th", ["ث", "ت"]),
    ("dh", ["ذ", "ز"]),
    ("aa", ["ا", "آ"]),
    ("ee", ["ی"]),
    ("oo", ["و"]),
    ("ou", ["و"]),
    ("ow", ["و"]),
    ("ey", ["ی"]),
    ("ei", ["ی"]),
]

# Irregular / historical Persian orthography stems (e.g. silent vav / واو معدوله)
_ORTHO_STEMS: dict[str, list[str]] = {
    "khah": ["خواه"],
    "kham": ["خوام"],
    "khast": ["خواست"],
    "khab": ["خواب"],
    "khahar": ["خواهر"],
    "bache": ["بچه"],
    "khoshbakht": ["خوشبخت"],
    "behtar": ["بهتر"],
    "darya": ["دریا"],
    "iran": ["ایران"],
    "raft": ["رفت"],
}

# Persian verbal & nominal prefixes
_PREFIXES: list[tuple[str, str]] = [
    ("nemikha", "نمی‌خوا"),
    ("mikha", "می‌خوا"),
    ("nemi", "نمی‌"),
    ("neme", "نمی‌"),
    ("mi", "می‌"),
    ("me", "می‌"),
    ("bi", "بی‌"),
    ("be", "به‌"),
    ("ba", "با"),
    ("na", "ن"),
]

# Persian suffixes (plural, clitic pronouns, comparatives, relational)
_SUFFIXES: list[tuple[str, str]] = [
    ("haaye", "‌های"),
    ("haye", "‌های"),
    ("haa", "‌ها"),
    ("ha", "‌ها"),
    ("tarin", "‌ترین"),
    ("tar", "‌تر"),
    ("emoon", "‌مون"),
    ("etoon", "‌تون"),
    ("eshoon", "‌شون"),
    ("eman", "‌مان"),
    ("etan", "‌تان"),
    ("eshan", "‌شان"),
    ("am", "‌ام"),
    ("at", "‌ات"),
    ("ash", "‌اش"),
    ("et", "‌ات"),
    ("esh", "‌اش"),
    ("am", "م"),
    ("at", "ت"),
    ("ash", "ش"),
    ("et", "ت"),
    ("esh", "ش"),
    ("an", "ان"),
    ("yan", "یان"),
    ("i", "ی"),
    ("ei", "ئی"),
    ("ee", "یی"),
    ("aee", "ایی"),
]

_URL_DOMAIN_SUFFIXES = (
    ".com", ".org", ".net", ".ir", ".io", ".me", ".edu", ".gov", ".co", ".app", ".dev", ".xyz", ".info"
)
_FILE_EXTENSIONS = (
    ".py", ".json", ".txt", ".md", ".exe", ".dll", ".cpp", ".c", ".h", ".ts", ".js",
    ".css", ".html", ".pdf", ".zip", ".png", ".jpg", ".toml", ".yaml", ".log",
)
_SAFE_FINGLISH_PAT = re.compile(r"^[a-zA-Z]+$")


def is_safe_finglish_token(token: str) -> bool:
    """Return False if token is a URL, email, file, digit, code symbol, or non-Finglish."""
    if not token or len(token) < 2:
        return False

    # Pure Latin alphabet letters only
    if not _SAFE_FINGLISH_PAT.match(token):
        return False

    tok_low = token.lower()
    if tok_low.startswith(("http://", "https://", "ftp://", "www.")):
        return False
    if tok_low.endswith(_URL_DOMAIN_SUFFIXES):
        return False
    if tok_low.endswith(_FILE_EXTENSIONS):
        return False

    return True


def normalize_finglish(word: str) -> str:
    """Normalize Finglish variations (e.g., salAm -> salam, khabar -> khabar)."""
    w = word.strip().lower()
    w = (
        w.replace("aa", "a")
        .replace("ee", "i")
        .replace("oo", "u")
        .replace("x", "kh")
        .replace("q", "gh")
        .replace("ck", "k")
    )
    return w


class TranslitEngine:
    """Bilingual Finglish to Persian transliteration engine with learning and fuzzy fallback."""

    def __init__(
        self,
        dict_path: Path | None = None,
        user_dict_path: Path | None = None,
        dict_persian: Dictionary | None = None,
    ) -> None:
        self.mappings: dict[str, list[str]] = {}
        self.user_frequency: dict[str, dict[str, int]] = {}
        self.user_dict_path = user_dict_path
        self._dict_persian: Dictionary | None = dict_persian
        self._dict_persian_loaded: bool = dict_persian is not None
        self._load_table(dict_path)
        self._load_user_dict()

    def _get_persian_dict(self) -> Dictionary | None:
        if not self._dict_persian_loaded:
            self._dict_persian_loaded = True
            try:
                from ravan.core.dict import Dictionary

                self._dict_persian = Dictionary.persian()
            except Exception as exc:  # noqa: BLE001
                log.warning("Failed to initialize Persian dictionary for translit: %s", exc)
                self._dict_persian = None
        return self._dict_persian

    def _load_table(self, dict_path: Path | None = None) -> None:
        if dict_path is None:
            data_dir = Path(__file__).resolve().parent.parent / "data"
            dict_path = data_dir / "finglish_dict.json"
        if dict_path.is_file():
            try:
                data = json.loads(dict_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self.mappings = data
            except Exception as exc:  # noqa: BLE001
                log.warning("Failed to load finglish_dict.json: %s", exc)

    def _load_user_dict(self) -> None:
        if self.user_dict_path and self.user_dict_path.is_file():
            try:
                data = json.loads(self.user_dict_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self.user_frequency = data
            except Exception as exc:  # noqa: BLE001
                log.warning("Failed to load user translit dict: %s", exc)

    def _save_user_dict(self) -> None:
        if self.user_dict_path:
            try:
                self.user_dict_path.parent.mkdir(parents=True, exist_ok=True)
                self.user_dict_path.write_text(
                    json.dumps(self.user_frequency, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("Failed to save user translit dict: %s", exc)

    def _decompose_affixes(self, word: str) -> list[tuple[str, str, str]]:
        """Decompose Finglish word into (prefix, stem, suffix) candidates."""
        results: list[tuple[str, str, str]] = []
        for p_lat, p_fa in _PREFIXES:
            if word.startswith(p_lat) and len(word) > len(p_lat) + 1:
                stem = word[len(p_lat):]
                results.append((p_fa, stem, ""))
                for s_lat, s_fa in _SUFFIXES:
                    if stem.endswith(s_lat) and len(stem) > len(s_lat) + 1:
                        inner_stem = stem[:-len(s_lat)]
                        results.append((p_fa, inner_stem, s_fa))

        for s_lat, s_fa in _SUFFIXES:
            if word.endswith(s_lat) and len(word) > len(s_lat) + 1:
                stem = word[:-len(s_lat)]
                results.append(("", stem, s_fa))

        return results

    def _phonetic_transduce(self, word: str) -> list[str]:
        """Convert a Finglish stem or word to Persian script phonetically."""
        w_norm = word.strip().lower()
        if not w_norm:
            return []
        if w_norm in _ORTHO_STEMS:
            return list(_ORTHO_STEMS[w_norm])

        units: list[str] = []
        i = 0
        n = len(w_norm)
        while i < n:
            matched = False
            for dg, _ in _DIGRAPHS:
                if w_norm.startswith(dg, i):
                    units.append(dg)
                    i += len(dg)
                    matched = True
                    break
            if not matched:
                units.append(w_norm[i])
                i += 1

        cand_lists: list[list[str]] = []
        for idx, u in enumerate(units):
            is_start = idx == 0
            is_end = idx == len(units) - 1
            if u == "kh":
                cand_lists.append(["خ"])
            elif u == "sh":
                cand_lists.append(["ش"])
            elif u == "ch":
                cand_lists.append(["چ"])
            elif u == "zh":
                cand_lists.append(["ژ"])
            elif u == "gh":
                cand_lists.append(["ق", "غ"])
            elif u == "aa":
                cand_lists.append(["آ"] if is_start else ["ا"])
            elif u == "ee":
                cand_lists.append(["ای"] if is_start else ["ی", "یی"])
            elif u == "oo":
                cand_lists.append(["او"] if is_start else ["و"])
            elif u in ("ou", "ow"):
                cand_lists.append(["و"])
            elif u in ("ei", "ey"):
                cand_lists.append(["ای"] if is_start else ["ی", "ئی"])
            elif u == "a":
                if is_start:
                    cand_lists.append(["ا", "آ"])
                elif is_end:
                    cand_lists.append(["ا", "ه"])
                else:
                    cand_lists.append(["ا", ""])
            elif u == "e":
                if is_start:
                    cand_lists.append(["ا", "ای"])
                elif is_end:
                    cand_lists.append(["ه", "ی"])
                else:
                    cand_lists.append(["", "ی"])
            elif u == "o":
                if is_start:
                    cand_lists.append(["ا", "او"])
                else:
                    cand_lists.append(["و", ""])
            elif u == "u":
                if is_start:
                    cand_lists.append(["او", "ا"])
                else:
                    cand_lists.append(["و"])
            elif u == "i":
                if is_start:
                    cand_lists.append(["ای"])
                else:
                    cand_lists.append(["ی"])
            elif u == "b":
                cand_lists.append(["ب"])
            elif u == "p":
                cand_lists.append(["پ"])
            elif u == "t":
                cand_lists.append(["ت", "ط"])
            elif u == "s":
                cand_lists.append(["س", "ص", "ث"])
            elif u == "j":
                cand_lists.append(["ج"])
            elif u == "c":
                cand_lists.append(["ک", "س"])
            elif u == "h":
                cand_lists.append(["ه", "ح"])
            elif u == "x":
                cand_lists.append(["خ"])
            elif u == "d":
                cand_lists.append(["د"])
            elif u == "r":
                cand_lists.append(["ر"])
            elif u == "z":
                cand_lists.append(["ز", "ض", "ظ", "ذ"])
            elif u == "f":
                cand_lists.append(["ف"])
            elif u == "q":
                cand_lists.append(["ق", "غ"])
            elif u == "k":
                cand_lists.append(["ک"])
            elif u == "g":
                cand_lists.append(["گ"])
            elif u == "l":
                cand_lists.append(["ل"])
            elif u == "m":
                cand_lists.append(["م"])
            elif u == "n":
                cand_lists.append(["ن"])
            elif u in ("v", "w"):
                cand_lists.append(["و"])
            elif u == "y":
                cand_lists.append(["ی"])
            else:
                cand_lists.append([u])

        cand_lists = [c[:2] for c in cand_lists]
        total_combos = 1
        for cl in cand_lists:
            total_combos *= len(cl)

        p_dict = self._get_persian_dict()
        out: list[str] = []

        if total_combos <= 256:
            for p in itertools.product(*cand_lists):
                word_cand = "".join(p)
                if word_cand and (p_dict is None or p_dict.contains(word_cand)):
                    if word_cand not in out:
                        out.append(word_cand)
        else:
            top_cand = "".join(cl[0] for cl in cand_lists)
            if top_cand and (p_dict is None or p_dict.contains(top_cand)):
                out.append(top_cand)

        if p_dict is not None:
            out.sort(key=lambda c: p_dict.rank_of(c) or 999999)
        return out

    def transliterate(self, word: str) -> list[str]:
        """Return Persian candidate words for a given Finglish word ordered by confidence."""
        clean = word.strip()
        if not clean or not is_safe_finglish_token(clean):
            return []

        w_low = clean.lower()
        candidates: list[str] = []

        # 1. Exact dictionary matches (preserve exact dictionary preference)
        exact_matches = self.mappings.get(w_low)
        if exact_matches:
            candidates.extend(exact_matches)

        # 2. Normalized dictionary match
        norm = normalize_finglish(w_low)
        if norm != w_low and norm in self.mappings:
            for c in self.mappings[norm]:
                if c not in candidates:
                    candidates.append(c)

        # 3. Morphological affix decomposition
        p_dict = self._get_persian_dict()
        morph_cands: list[str] = []
        for p_fa, stem, s_fa in self._decompose_affixes(w_low):
            stem_norm = normalize_finglish(stem)
            stem_cands = (
                self.mappings.get(stem)
                or self.mappings.get(stem_norm)
                or _ORTHO_STEMS.get(stem)
                or _ORTHO_STEMS.get(stem_norm)
            )
            if not stem_cands:
                stem_cands = self._phonetic_transduce(stem)

            for sc in stem_cands or []:
                combos = [
                    f"{p_fa}{sc}{s_fa}",
                    f"{p_fa}{sc}\u200c{s_fa}" if s_fa.startswith("‌") else f"{p_fa}{sc}{s_fa}",
                    f"{p_fa}{sc}{s_fa.lstrip('‌')}",
                ]
                for c in combos:
                    c_clean = c.replace("\u200c\u200c", "\u200c")
                    if p_dict is None or p_dict.contains(c_clean):
                        if c_clean not in candidates and c_clean not in morph_cands:
                            morph_cands.append(c_clean)

        # Sort morphological candidates by dictionary frequency and typography
        if p_dict is not None and morph_cands:
            morph_cands.sort(
                key=lambda c: (
                    p_dict.rank_of(c) or 999999,
                    0 if "\u200c" in c else 1,
                )
            )
        candidates.extend(morph_cands)

        # 4. Direct phonetic transducer fallback
        if len(candidates) < 3:
            pt_cands = self._phonetic_transduce(w_low)
            for pt in pt_cands:
                if pt not in candidates:
                    candidates.append(pt)

        # 5. Fuzzy edit-distance fallback if still empty
        if not candidates:
            candidates = self.fuzzy_transliterate(w_low)

        # 6. Apply user learned personal preferences (top priority)
        user_picks = self.user_frequency.get(w_low, {})
        if user_picks:
            for chosen in user_picks:
                if chosen not in candidates:
                    candidates.append(chosen)
            candidates.sort(key=lambda c: user_picks.get(c, 0), reverse=True)

        return candidates

    def transliterate_word(self, word: str) -> list[str]:
        """Alias for transliterate."""
        return self.transliterate(word)

    def top_candidate(self, word: str) -> str | None:
        """Return the top-1 Persian transliteration or None."""
        cands = self.transliterate(word)
        return cands[0] if cands else None

    def record_pick(self, finglish_word: str, chosen_fa: str) -> None:
        """Update personal frequency table when a user selects a candidate."""
        w_low = finglish_word.strip().lower()
        sub = self.user_frequency.setdefault(w_low, {})
        sub[chosen_fa] = sub.get(chosen_fa, 0) + 1
        log.debug(
            "Learned translit preference: %r -> %r (count=%d)",
            w_low,
            chosen_fa,
            sub[chosen_fa],
        )
        self._save_user_dict()

    def fuzzy_transliterate(self, word: str) -> list[str]:
        """Fuzzy phoneme-matching fallback for unknown Finglish words."""
        norm = normalize_finglish(word)
        if len(norm) < 3:
            return []
        matches: list[tuple[int, list[str]]] = []
        for k, v in self.mappings.items():
            if k.startswith(norm[:3]) or norm.startswith(k[:3]):
                dist = abs(len(k) - len(norm))
                matches.append((dist, v))
                if len(matches) >= 5:
                    break
        matches.sort(key=lambda item: item[0])
        out: list[str] = []
        for _, cands in matches:
            for c in cands:
                if c not in out:
                    out.append(c)
        return out[:5]

    def transliterate_text(self, text: str) -> str:
        """Transliterate whole sentence or phrase for CLI / bulk text."""
        tokens = re.split(r"(\s+)", text)
        out: list[str] = []
        punct_pat = re.compile(r"^([^a-zA-Z]*)([a-zA-Z]+)([^a-zA-Z]*)$")
        for tok in tokens:
            if not tok or tok.isspace():
                out.append(tok)
                continue
            m = punct_pat.match(tok)
            if m:
                lead, inner, trail = m.groups()
                if is_safe_finglish_token(inner):
                    cand = self.top_candidate(inner)
                    out.append(lead + (cand if cand else inner) + trail)
                else:
                    out.append(tok)
            else:
                out.append(tok)
        return "".join(out)

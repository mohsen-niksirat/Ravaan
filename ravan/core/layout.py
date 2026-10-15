"""Persian ↔ English keyboard layout mapping (ISIRI 9147)."""

from __future__ import annotations

def is_persian_or_arabic(c: str) -> bool:
    code = ord(c)
    return (
        0x0600 <= code <= 0x06FF
        or 0xFB50 <= code <= 0xFDFF
        or 0xFE70 <= code <= 0xFEFF
    )


# (EN key, FA char) — unshifted (standard Windows Persian 00000429 + ISIRI 9147)
_UNSHIFTED: list[tuple[str, str]] = [
    ("q", "ض"), ("w", "ص"), ("e", "ث"), ("r", "ق"), ("t", "ف"),
    ("y", "غ"), ("u", "ع"), ("i", "ه"), ("o", "خ"), ("p", "ح"),
    ("[", "ج"), ("]", "چ"), ("\\", "پ"),
    ("a", "ش"), ("s", "س"), ("d", "ی"), ("f", "ب"), ("g", "ل"),
    ("h", "ا"), ("j", "ت"), ("k", "ن"), ("l", "م"), (";", "ک"),
    ("'", "گ"),
    ("z", "ظ"), ("x", "ط"), ("c", "ز"), ("v", "ر"), ("b", "ذ"),
    ("n", "د"), ("m", "ئ"), (",", "و"), (".", "."), ("/", "/"),
    ("`", "پ"),  # ISIRI 9147 variation
    ("1", "۱"), ("2", "۲"), ("3", "۳"), ("4", "۴"), ("5", "۵"),
    ("6", "۶"), ("7", "۷"), ("8", "۸"), ("9", "۹"), ("0", "۰"),
]

# (EN key, FA char) — shifted
_SHIFTED: list[tuple[str, str]] = [
    ("Q", "ً"), ("W", "ٌ"), ("E", "ٍ"), ("R", "ريال"), ("T", "،"),
    ("Y", "؛"), ("U", ","), ("I", "]"), ("O", "["), ("P", "\\"),
    ("{", "}"), ("}", "{"), ("|", "|"),
    ("A", "َ"), ("S", "ُ"), ("D", "ِ"), ("F", "ّ"), ("G", "ۀ"),
    ("H", "آ"), ("J", "ـ"), ("K", "«"), ("L", "»"), (":", ":"),
    ('"', '"'),
    ("Z", "ة"), ("X", "ي"), ("C", "ژ"), ("V", "ؤ"), ("B", "إ"),
    ("N", "أ"), ("M", "ء"), ("<", "<"), (">", ">"), ("?", "؟"),
    ("~", "×"),
    ("!", "!"), ("@", "@"), ("#", "#"), ("$", "$"), ("%", "٪"),
    ("^", "^"), ("&", "&"), ("*", "*"), ("(", ")"), (")", "("),
    ("_", "_"), ("+", "+"),
]


class LayoutMapper:
    """Bidirectional Persian ↔ English layout converter."""

    def __init__(self) -> None:
        self.en_to_fa: dict[str, str] = {}
        self.fa_to_en: dict[str, str] = {}
        for en, fa in _UNSHIFTED + _SHIFTED:
            self.en_to_fa[en] = fa
            self.fa_to_en.setdefault(fa, en)
        # Aliases and variations for seamless reverse mapping
        self.fa_to_en.setdefault("ژ", "C")
        self.fa_to_en.setdefault("پ", "\\")
        self.fa_to_en.setdefault("ئ", "m")
        self.fa_to_en.setdefault("آ", "H")
        self.fa_to_en.setdefault("ي", "d")  # Arabic Yeh alias to 'd'
        self.fa_to_en.setdefault("ك", ";")  # Arabic Kaf alias to ';'
        self.fa_to_en.setdefault("،", "T")
        self.fa_to_en.setdefault("؛", "Y")
        self.fa_to_en.setdefault("؟", "?")

    def en_to_fa_word(self, word: str) -> str | None:
        out: list[str] = []
        for c in word:
            if c == " ":
                out.append(" ")
                continue
            mapped = self.en_to_fa.get(c)
            if mapped is None:
                return None
            out.append(mapped)
        return "".join(out)

    def fa_to_en_word(self, word: str) -> str | None:
        out: list[str] = []
        for c in word:
            if c == " ":
                out.append(" ")
                continue
            mapped = self.fa_to_en.get(c)
            if mapped is None:
                return None
            out.append(mapped)
        return "".join(out)

    def convert_word(self, word: str) -> str | None:
        """Auto-detect direction: FA→EN if Persian chars present, else EN→FA."""
        if any(is_persian_or_arabic(c) for c in word):
            fa = self.fa_to_en_word(word)
            if fa is not None:
                return fa
            return self.en_to_fa_word(word)
        en = self.en_to_fa_word(word)
        if en is not None:
            return en
        return self.fa_to_en_word(word)

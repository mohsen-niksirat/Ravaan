"""Predictor — dictionary lookups and candidate ranking."""

from __future__ import annotations

import math
import re
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable

from .config import Config
from .dict import DictEntry, Dictionary
from .events import Candidate, CandidateKind
from .learning import UserLearningEngine

_URL_DOMAIN_SUFFIXES = (
    ".com", ".org", ".net", ".ir", ".io", ".me", ".edu", ".gov", ".co", ".app", ".dev", ".xyz", ".info"
)
_FILE_EXTENSIONS = (
    ".py", ".json", ".txt", ".md", ".exe", ".dll", ".cpp", ".c", ".h", ".ts", ".js", ".jsx", ".tsx",
    ".css", ".html", ".pdf", ".zip", ".tar", ".gz", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".xml", ".yml", ".yaml", ".log", ".ico",
    ".toml", ".ini", ".cfg", ".bat", ".sh", ".ps1", ".rs", ".go", ".java", ".class", ".bin"
)
_CAMEL_CASE_PAT = re.compile(r"[a-z][A-Z]")
_PERSIAN_CHAR_PAT = re.compile(r"^[\u0600-\u06FF\u200C]+$")
_ENGLISH_CHAR_PAT = re.compile(r"^[a-zA-Z]+$")

_CODE_KEYWORDS: frozenset[str] = frozenset({
    # Language keywords (Python, JS/TS, C/C++, Rust, Go, Java, C#, SQL, Bash, etc.)
    "abstract", "alignas", "alignof", "and", "arguments", "as", "asm", "assert",
    "async", "auto", "await", "bool", "boolean", "break", "byte", "bytes", "case",
    "catch", "char", "class", "clone", "cmp", "compl", "concept", "const",
    "constexpr", "consteval", "continue", "crate", "debugger", "decltype", "def",
    "default", "defer", "del", "delete", "do", "double", "dyn", "elif", "else",
    "enum", "eval", "except", "exec", "export", "extends", "extern", "false",
    "final", "finally", "float", "fn", "for", "from", "func", "function", "global",
    "go", "goto", "if", "impl", "import", "in", "inline", "instanceof", "int",
    "interface", "is", "lambda", "let", "long", "match", "module", "move", "mut",
    "namespace", "native", "new", "nil", "noexcept", "none", "nonlocal", "not",
    "null", "nullptr", "operator", "or", "override", "package", "pass", "private",
    "protected", "pub", "public", "raise", "range", "ref", "register", "requires",
    "return", "self", "select", "short", "signed", "sizeof", "static", "struct",
    "super", "switch", "synchronized", "template", "this", "throw", "throws",
    "trait", "transient", "true", "try", "type", "typedef", "typeid", "typename",
    "typeof", "union", "unsigned", "use", "using", "val", "var", "virtual", "void",
    "volatile", "where", "while", "with", "yield",
    # Common standard library, types & dev tools
    "argv", "argc", "ascii", "ast", "bin", "cfg", "chmod", "chown", "cli", "cmd",
    "config", "curl", "cwd", "diff", "dir", "dist", "doc", "docs", "docker",
    "env", "err", "errno", "fifo", "fmt", "git", "grep", "guid", "gzip",
    "hostname", "html", "http", "https", "hwnd", "idx", "init", "io", "ip",
    "ipc", "json", "k8s", "kill", "len", "libc", "lib", "lint", "log", "lparam",
    "ls", "make", "malloc", "md5", "mkdir", "mmap", "msg", "mutex", "nginx",
    "noop", "num", "opt", "os", "param", "params", "path", "pid",
    "pip", "pkg", "posix", "proc", "ptr", "pwd", "pydantic", "pytest", "regex",
    "repo", "repr", "req", "res", "rm", "root", "rpc", "rsa", "sdk", "sed",
    "sem", "sha", "shutil", "sig", "sock", "socket", "spawn", "spec", "sql",
    "ssh", "ssl", "stderr", "stdin", "stdout", "str", "sub", "sudo", "sync",
    "sys", "tar", "tcp", "temp", "tmp", "tls", "tmux", "toml", "tty", "udp",
    "uri", "url", "user", "util", "utils", "uuid", "vec", "venv", "vim",
    "vm", "wait", "wget", "win32", "wparam", "xml", "yaml", "yarn", "zip", "zsh",
})


_PUNCT_CHARS: frozenset[str] = frozenset(".,;:!?()[]{}+*=&|<>~`^%\"'")
_DIGITS_SET: frozenset[str] = frozenset("0123456789۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧۸۹")


def is_safe_autocorrect_token(token: str) -> bool:
    """Return False if token should never be modified by autocorrect.

    Conservative screening rules prevent modifying:
    - Tokens containing digits (Latin or Persian/Arabic)
    - URLs, domains, and protocols (http://, https://, www., .com, .ir, etc.)
    - Emails and @mentions (@username, user@domain.com)
    - Hashtags (#topic)
    - File paths and filenames with extensions (C:\\..., /path/..., file.py)
    - Code identifiers (snake_case, camelCase, $var, __init__, operators, keywords)
    - Punctuation-containing tokens or short abbreviations (< 3 chars)
    - All-uppercase English acronyms (API, SDK, HTML, USA)
    - Mixed-script tokens (e.g. Persian letters mixed with Latin letters)
    """
    if not token or len(token) < 3:
        return False

    tok_set = set(token)

    # 1. Digits check (Latin and Persian/Arabic digits)
    if not tok_set.isdisjoint(_DIGITS_SET):
        return False

    # 2. Email, @mention, hashtag, code identifiers
    if "@" in tok_set or "#" in tok_set or "_" in tok_set or "$" in tok_set:
        return False

    # 3. Path separators
    if "/" in tok_set or "\\" in tok_set or ":" in tok_set:
        return False

    # 4. Punctuation
    if not tok_set.isdisjoint(_PUNCT_CHARS):
        return False

    # 5. URLs, protocols, domains, file extensions
    tok_low = token.lower()
    if tok_low.startswith(("http://", "https://", "ftp://", "www.")):
        return False
    if tok_low.endswith(_URL_DOMAIN_SUFFIXES):
        return False
    if tok_low.endswith(_FILE_EXTENSIONS):
        return False

    # 6. Code keywords & developer tokens
    if tok_low in _CODE_KEYWORDS:
        return False

    # 7. Check script consistency (never mixed script)
    has_ascii = any(c.isascii() and c.isalpha() for c in token)
    has_fa = any(is_arabic_persian(c) for c in token)
    if has_ascii and has_fa:
        return False

    # 8. CamelCase and all-uppercase acronyms
    if has_ascii:
        if _CAMEL_CASE_PAT.search(token):
            return False
        if token.isupper() and token.isascii():
            return False
        return bool(_ENGLISH_CHAR_PAT.match(token))

    if has_fa:
        return bool(_PERSIAN_CHAR_PAT.match(token))

    return False


def is_arabic_persian(c: str) -> bool:
    code = ord(c)
    return (
        0x0600 <= code <= 0x06FF
        or 0xFB50 <= code <= 0xFDFF
        or 0xFE70 <= code <= 0xFEFF
    )


class Predictor(ABC):
    @abstractmethod
    def predict(
        self, prefix: str, context: str, limit: int, app_name: str | None = None
    ) -> list[Candidate]:
        raise NotImplementedError

    def record_selection(
        self, word: str, context: str | None = None, app_name: str | None = None
    ) -> None:
        """Record a user-accepted candidate to boost future predictions."""
        del word, context, app_name  # Optional hook for subclasses to override


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
        self._lock = threading.Lock()
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
            with self._lock:
                if self._english is None and self._lazy_en_loader is not None:
                    self._english = self._lazy_en_loader()
                    self._lazy_en_loader = None
        return self._english

    @english.setter
    def english(self, value: Dictionary | None) -> None:
        with self._lock:
            self._english = value
            self._lazy_en_loader = None

    @property
    def persian(self) -> Dictionary | None:
        if self._persian is None and self._lazy_fa_loader is not None:
            with self._lock:
                if self._persian is None and self._lazy_fa_loader is not None:
                    self._persian = self._lazy_fa_loader()
                    self._lazy_fa_loader = None
        return self._persian

    @persian.setter
    def persian(self, value: Dictionary | None) -> None:
        with self._lock:
            self._persian = value
            self._lazy_fa_loader = None

    @property
    def learning(self) -> UserLearningEngine:
        if self._learning is None:
            with self._lock:
                if self._learning is None:
                    if self._lazy_learning_loader is not None:
                        self._learning = self._lazy_learning_loader()
                        self._lazy_learning_loader = None
                    else:
                        self._learning = UserLearningEngine(auto_load=False)
        return self._learning

    @learning.setter
    def learning(self, value: UserLearningEngine) -> None:
        with self._lock:
            self._learning = value
            self._lazy_learning_loader = None

    def suppress_session_word(self, word: str) -> None:
        """Suppress autocorrection for this word for the rest of the running session."""
        w = word.strip().lower()
        if w:
            self.session_suppressed.add(w)

    def record_selection(
        self, word: str, context: str | None = None, app_name: str | None = None
    ) -> None:
        key = word.strip().lower()
        if key:
            self._selection_counts[key] = self._selection_counts.get(key, 0) + 1
            self.learning.learn_word(word, app_name=app_name)
            if context:
                parts = context.strip().split()
                if len(parts) >= 2:
                    self.learning.learn_trigram(parts[-2], parts[-1], word, app_name=app_name)
                if parts:
                    self.learning.learn_transition(parts[-1], word, app_name=app_name)
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
            return UserLearningEngine(
                auto_load=True,
                learning_enabled=getattr(cfg, "learning_enabled", True),
            )

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


    def predict(
        self, prefix: str, context: str, limit: int, app_name: str | None = None
    ) -> list[Candidate]:
        if not prefix:
            if not context:
                return []
            next_words = self.learning.predict_next_words(context, limit, app_name=app_name)
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
        learned_matches = self.learning.top_learned_completions(prefix, limit, app_name=app_name)
        for w in learned_matches:
            if w.lower() != prefix.lower():
                candidates.append(
                    Candidate(
                        text=w,
                        score=2000.0 + self.learning.get_word_boost(w, app_name=app_name),
                        kind=CandidateKind.COMPLETION,
                    )
                )
                seen_texts.add(w)

        # 2. Dictionary completions with smoothed context ranking
        scan_limit = max(limit * 3, 20)
        c_words = context.strip().split() if context else []
        w1 = c_words[-2] if len(c_words) >= 2 else None
        w2 = c_words[-1] if c_words else None

        for entry in dict_.completions(prefix, scan_limit):
            if entry.word.lower() != prefix.lower() and entry.word not in seen_texts:
                boost = (
                    self._selection_counts.get(entry.word.lower(), 0)
                    + self.learning.get_word_boost(entry.word, app_name=app_name)
                )
                if w2:
                    smoothed_score = self.learning.compute_smoothed_score(entry.word, w2=w2, w1=w1)
                    boost += smoothed_score * 80.0

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

        candidates.sort(key=lambda c: c.score, reverse=True)
        completions = candidates[:limit]

        # 3. Sentence continuations (top-3 multi-word completions shown after single words)
        sentence_cands = self.learning.predict_sentence_continuations(
            context, prefix=prefix, limit=3, app_name=app_name
        )
        for sent in sentence_cands:
            if sent not in seen_texts and sent.lower() != prefix.lower():
                completions.append(
                    Candidate(
                        text=sent,
                        score=150.0,
                        kind=CandidateKind.SENTENCE,
                        replace_len=len(prefix),
                    )
                )
                seen_texts.add(sent)

        # 4. Fuzzy matches (fallback when completions are empty)
        if not completions and len(prefix) >= 3:
            fuzzy = dict_.fuzzy_matches(prefix, 1, limit)
            prefix_rank = dict_.rank_of(prefix)
            for entry, dist in fuzzy:
                if entry.word in seen_texts:
                    continue
                if prefix_rank is not None and entry.rank >= prefix_rank:
                    continue
                score = (1.0 / (entry.rank + 1.0)) * (1.0 / (dist * 10.0 + 1.0))
                completions.append(
                    Candidate(
                        text=entry.word,
                        score=score,
                        kind=CandidateKind.AUTOCORRECT,
                    )
                )
                seen_texts.add(entry.word)

        return completions[: limit + 3]

    def correct(self, word: str, lang: str | None = None) -> Candidate | None:
        """Return an autocorrect candidate for a completed word based on configured mode, or None."""
        if self.autocorrect_mode == "off":
            return None

        # 1. Conservative token screening: reject digits, URLs, emails, code, paths, etc.
        if not is_safe_autocorrect_token(word):
            return None

        w_low = word.lower()
        if w_low in self.ignored_words or w_low in self.session_suppressed:
            return None

        # 2. Bilingual consistency check
        if lang == "fa" and not any(is_arabic_persian(c) for c in word):
            return None
        if lang == "en" and any(is_arabic_persian(c) for c in word):
            return None

        dict_ = self._dict_for(word, lang=lang)
        if dict_ is None:
            return None

        # 3. Exact dictionary match: already valid word
        if dict_.contains(word):
            return None

        # Cross-dictionary check: if valid in other language (e.g. English word in Persian text), don't touch
        other_dict = self._persian if dict_ is self._english else self._english
        if other_dict is not None and other_dict.contains(word):
            return None

        # 4. Persian confusable typo normalization (ك->ک, ي->ی, ة->ه/ت, etc.)
        if any(is_arabic_persian(c) for c in word):
            from .normalizer import normalize_persian_typos

            for variant in normalize_persian_typos(word):
                if dict_.contains(variant):
                    entry = dict_.get(variant)
                    if entry is not None:
                        boost = self._selection_counts.get(variant.lower(), 0)
                        score = 1000.0 + (1.0 / (entry.rank + 1.0)) + boost
                        return Candidate(
                            text=entry.word,
                            score=score,
                            kind=CandidateKind.AUTOCORRECT,
                        )

        # 5. Still typing a plausible prefix of a short word? Don't auto-mangle in safe mode
        if self.autocorrect_mode == "safe" and len(word) >= 3:
            limit_len = len(word) + 2
            comps = dict_.completions(word, 8)
            if any(len(e.word) <= limit_len and e.rank <= 5000 for e in comps):
                return None

        # 6. Fuzzy matches with conservative edit-distance rules
        word_len = len(word)
        if word_len <= 5:
            max_dist = 1
        elif self.autocorrect_mode == "safe":
            max_dist = 2 if word_len >= 6 else 1
        else:
            max_dist = 2

        matches = dict_.fuzzy_matches(word, max_dist, 8)
        if not matches:
            return None

        scored: list[tuple[float, DictEntry, int]] = []
        for entry, dist in matches:
            # Conservative constraints:
            # Distance 2 requires word length >= 6 and high-frequency target word
            if dist > 1:
                if word_len < 6 or entry.rank > 1000:
                    continue
            if word_len == 3:
                # 3-letter tokens: only allow identical length with top-ranked vocabulary (e.g. teh -> the)
                if len(entry.word) != 3 or entry.rank > 200:
                    continue

            boost = self._selection_counts.get(entry.word.lower(), 0)
            if entry.rank == 0:
                prob = 1000.0 + boost
            else:
                freq = entry.frequency if entry.frequency > 0 else max(1, 20000 - entry.rank * 2)
                log_freq = math.log10(freq + 10)
                dist_penalty = 1.0 if dist == 1 else 4.0
                prob = (log_freq / dist_penalty) + (boost * 0.5)

            scored.append((prob, entry, dist))

        if not scored:
            return None

        scored.sort(key=lambda t: t[0], reverse=True)
        best_prob, best_entry, best_dist = scored[0]

        # In safe mode, never strip ZWNJ from a user-typed word
        if "\u200c" in word and "\u200c" not in best_entry.word and self.autocorrect_mode == "safe":
            return None

        # Confidence gap: if runner-up exists, ensure clear margin of confidence in safe mode
        if len(scored) > 1 and self.autocorrect_mode == "safe":
            runner_up_prob, runner_up_entry, runner_up_dist = scored[1]
            if runner_up_dist == best_dist and abs(best_prob - runner_up_prob) < 0.25:
                # Ambiguous correction: prefer safe default (do NOT modify user text)
                return None

        return Candidate(
            text=best_entry.word,
            score=best_prob,
            kind=CandidateKind.AUTOCORRECT,
        )


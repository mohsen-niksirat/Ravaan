"""Text expansion snippets with dynamic templates and date/time macros."""

from __future__ import annotations

import re
import uuid
from datetime import date
from typing import Callable

from .config import Config
from .jalali import JalaliDate, current_time_str


def get_macro_values() -> dict[str, str]:
    """Calculate current values for template placeholders."""
    j = JalaliDate.today()
    return {
        "today": j.isoformat_fa(),
        "shamsi": j.isoformat_fa(),
        "shamsi_en": j.isoformat(),
        "tarikh": j.format_persian(include_weekday=False),
        "tarikh_fa": j.format_persian(include_weekday=False),
        "tarikh_full": j.format_persian(include_weekday=True),
        "date": date.today().isoformat(),
        "time": current_time_str(persian_digits=False),
        "time_fa": current_time_str(persian_digits=True),
        "uuid": str(uuid.uuid4()),
        "guid": str(uuid.uuid4()),
    }


def render_template(template: str) -> str:
    """Replace {{placeholder}} with dynamic date/time/uuid values."""
    if "{{" not in template:
        return template
    values = get_macro_values()
    return re.sub(
        r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}",
        lambda m: values.get(m.group(1).lower(), m.group(0)),
        template,
    )


class SnippetEngine:
    def __init__(
        self,
        snippets: list[tuple[str, str]],
        include_default_macros: bool = True,
    ) -> None:
        self._snippets = list(snippets)
        self._macros: dict[str, Callable[[], str]] = {}
        if include_default_macros:
            self._init_default_macros()

    def _init_default_macros(self) -> None:
        self._macros = {
            "/today": lambda: JalaliDate.today().isoformat_fa(),
            "/shamsi": lambda: JalaliDate.today().isoformat_fa(),
            "/امروز": lambda: JalaliDate.today().isoformat_fa(),
            "/tarikh": lambda: JalaliDate.today().format_persian(include_weekday=False),
            "/تاریخ": lambda: JalaliDate.today().format_persian(include_weekday=False),
            "/date": lambda: date.today().isoformat(),
            "/time": lambda: current_time_str(persian_digits=False),
            "/saat": lambda: current_time_str(persian_digits=False),
            "/ساعت": lambda: current_time_str(persian_digits=True),
            "/uuid": lambda: str(uuid.uuid4()),
            "/guid": lambda: str(uuid.uuid4()),
        }

    @classmethod
    def from_config(cls, cfg: Config) -> SnippetEngine:
        return cls([(s.trigger, s.replacement) for s in cfg.snippets])

    def expand(self, word: str) -> str | None:
        for trigger, replacement in self._snippets:
            if trigger == word:
                return render_template(replacement)
        if word in self._macros:
            return self._macros[word]()

        # Number-to-words and formatting suffix triggers (e.g. 1250000/w, 1250000/s, 1250000/t)
        from .normalizer import fa_to_en_digits
        from .num2words import format_thousands, num_to_persian_words, to_toman_words

        suffixes = (
            ("/w", num_to_persian_words),
            ("/words", num_to_persian_words),
            ("/حروف", num_to_persian_words),
            ("/s", lambda n: format_thousands(n, persian_digits=True)),
            ("/sep", lambda n: format_thousands(n, persian_digits=True)),
            ("/t", to_toman_words),
            ("/تومان", to_toman_words),
        )
        for sfx, fn in suffixes:
            if word.endswith(sfx):
                num_part = word[: -len(sfx)]
                clean = fa_to_en_digits(num_part).replace(",", "").replace(".", "")
                if clean and clean.isdigit():
                    res = fn(num_part)
                    if res:
                        return res

        return None

    def all(self) -> list[tuple[str, str]]:
        return list(self._snippets)

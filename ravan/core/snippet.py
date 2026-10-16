"""Text expansion snippets with dynamic templates, date/time macros, math evaluation, and cursor placement."""

from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime, timedelta
from typing import Callable

from .config import Config, Snippet
from .jalali import JalaliDate, current_time_str
from .normalizer import en_to_fa_digits


def get_macro_values() -> dict[str, str]:
    """Calculate current values for template placeholders."""
    j = JalaliDate.today()
    today_g = date.today()
    yesterday_j = JalaliDate.from_gregorian(today_g - timedelta(days=1))
    tomorrow_j = JalaliDate.from_gregorian(today_g + timedelta(days=1))
    now = datetime.now()

    return {
        # Jalali dates
        "today": j.isoformat_fa(),
        "shamsi": j.isoformat_fa(),
        "shamsi_en": j.isoformat(),
        "tarikh": j.format_persian(include_weekday=False),
        "tarikh_fa": j.format_persian(include_weekday=False),
        "tarikh_full": j.format_persian(include_weekday=True),
        "yesterday": yesterday_j.isoformat_fa(),
        "yesterday_en": yesterday_j.isoformat(),
        "dirooz": yesterday_j.isoformat_fa(),
        "دیروز": yesterday_j.isoformat_fa(),
        "tomorrow": tomorrow_j.isoformat_fa(),
        "tomorrow_en": tomorrow_j.isoformat(),
        "farda": tomorrow_j.isoformat_fa(),
        "فردا": tomorrow_j.isoformat_fa(),
        # Date components
        "year": str(j.year),
        "year_fa": en_to_fa_digits(str(j.year)),
        "saal": str(j.year),
        "سال": en_to_fa_digits(str(j.year)),
        "month": j.month_name,
        "mah": j.month_name,
        "ماه": j.month_name,
        "month_num": f"{j.month:02d}",
        "month_num_fa": en_to_fa_digits(f"{j.month:02d}"),
        "day": str(j.day),
        "day_fa": en_to_fa_digits(str(j.day)),
        "rooz": str(j.day),
        "روز": en_to_fa_digits(str(j.day)),
        "weekday": j.weekday_name(),
        "hafteh": j.weekday_name(),
        "روز_هفته": j.weekday_name(),
        # Gregorian dates
        "date": today_g.isoformat(),
        "date_en": today_g.isoformat(),
        "gregorian": today_g.isoformat(),
        "gregorian_year": str(today_g.year),
        # Times
        "time": current_time_str(persian_digits=False),
        "time_fa": current_time_str(persian_digits=True),
        "time_sec": now.strftime("%H:%M:%S"),
        "time_sec_fa": en_to_fa_digits(now.strftime("%H:%M:%S")),
        "timestamp": str(int(now.timestamp())),
        # Identifiers
        "uuid": str(uuid.uuid4()),
        "guid": str(uuid.uuid4()),
    }


def render_template(template: str) -> str:
    """Replace {{placeholder}} with dynamic date/time/uuid/math values."""
    if "{{" not in template:
        return template

    from ravan.core.calc import calculate

    def _eval_math(match: re.Match[str]) -> str:
        expr = match.group(1).strip()
        res = calculate(expr)
        return res if res is not None else match.group(0)

    # First evaluate math/calc expressions: {{calc: 100 * 1.09}} or {{math: 50 + 2}}
    rendered = re.sub(
        r"\{\{\s*(?:math|calc|eval)\s*:\s*([^}]+)\s*\}\}",
        _eval_math,
        template,
    )

    # Then substitute named macros
    values = get_macro_values()
    rendered = re.sub(
        r"\{\{\s*([^\s}]+)\s*\}\}",
        lambda m: values.get(m.group(1).lower(), m.group(0)),
        rendered,
    )
    return rendered


def parse_cursor_placeholder(text: str) -> tuple[str, int | None]:
    """Extract $0 or {{cursor}} from text.

    Returns:
        (clean_text, cursor_offset)
        where cursor_offset is the character offset from the END of clean_text
        to position the cursor, or None if no cursor placeholder was present.
    """
    for marker in ("$0", "{{cursor}}", "{{0}}"):
        pos = text.find(marker)
        if pos != -1:
            clean = text[:pos] + text[pos + len(marker) :]
            offset = len(clean) - pos
            return clean, offset
    return text, None


def snippets_to_json(snippets: list[Snippet], indent: int = 2) -> str:
    """Serialize snippet list to a UTF-8 JSON string."""
    data = [{"trigger": s.trigger, "replacement": s.replacement} for s in snippets]
    return json.dumps(data, ensure_ascii=False, indent=indent)


def snippets_from_json(json_str: str) -> list[Snippet]:
    """Parse JSON string into a list of validated Snippet instances."""
    data = json.loads(json_str)
    if not isinstance(data, list):
        raise ValueError("Snippets JSON must be an array of objects")
    snippets: list[Snippet] = []
    for item in data:
        if isinstance(item, dict) and "trigger" in item and "replacement" in item:
            trig = str(item["trigger"]).strip()
            repl = str(item["replacement"])
            if trig:
                snippets.append(Snippet(trigger=trig, replacement=repl))
    return snippets


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

    def expand_with_cursor(self, word: str) -> tuple[str, int | None] | None:
        """Expand word into (replacement_text, cursor_offset_from_end) or None."""
        for trigger, replacement in self._snippets:
            if trigger == word:
                rendered = render_template(replacement)
                clean_text, cursor_offset = parse_cursor_placeholder(rendered)
                return clean_text, cursor_offset

        if word in self._macros:
            val = self._macros[word]()
            clean_text, cursor_offset = parse_cursor_placeholder(val)
            return clean_text, cursor_offset

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
                        return res, None

        return None

    def expand(self, word: str) -> str | None:
        """Expand word into clean replacement string (cursor marker removed) or None."""
        res = self.expand_with_cursor(word)
        return res[0] if res is not None else None

    def all(self) -> list[tuple[str, str]]:
        return list(self._snippets)

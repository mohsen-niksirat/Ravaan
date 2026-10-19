"""Text expansion snippets with dynamic templates, date/time macros, math evaluation, and cursor placement."""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from .config import Config, Snippet
from .jalali import JalaliDate, current_time_str
from .snippet_macros import BUILTIN_PLACEHOLDERS, fetch_clipboard, get_macro_values

_fetch_clipboard = fetch_clipboard

log = logging.getLogger(__name__)


@dataclass
class FormField:
    name: str
    label: str
    default: str = ""
    choices: list[str] = field(default_factory=list)
    field_type: str = "text"  # "text" | "choice" | "date"


def safe_regex_match(
    pattern: str, text: str, max_len: int = 100, timeout_sec: float = 0.005
) -> re.Match[str] | None:
    """Evaluate regex match with input length bound and timeout to prevent ReDoS."""
    if len(text) > max_len:
        return None
    try:
        regex = re.compile(pattern)
        t0 = time.perf_counter()
        m = regex.fullmatch(text)
        if (time.perf_counter() - t0) > timeout_sec:
            log.warning("Regex evaluation exceeded timeout (%s)", pattern)
            return None
        return m
    except Exception as exc:  # noqa: BLE001
        log.debug("Regex match failed for %r: %s", pattern, exc)
        return None


def expand_capture_groups(template: str, match: re.Match[str]) -> str:
    """Expand $1, $2, etc., using capture groups from regex match."""
    res = template
    for i in range(1, len(match.groups()) + 1):
        val = match.group(i) or ""
        res = res.replace(f"${i}", val).replace(f"\\{i}", val)
    return res


def extract_form_fields(template: str) -> list[FormField]:
    """Extract interactive user form fields from template."""
    fields: list[FormField] = []
    seen: set[str] = set()

    for m in re.finditer(r"\{\{\s*([^}]+)\s*\}\}", template):
        content = m.group(1).strip()
        low = content.lower()
        if (
            low in BUILTIN_PLACEHOLDERS
            or low.startswith("calc:")
            or low.startswith("math:")
            or low.startswith("eval:")
        ):
            continue

        if content.lower().startswith("choice:"):
            raw_choices = content[7:].strip()
            opts = [o.strip() for o in raw_choices.split("|") if o.strip()]
            name = f"choice_{len(fields) + 1}"
            fields.append(
                FormField(
                    name=name,
                    label="Select Option",
                    default=opts[0] if opts else "",
                    choices=opts,
                    field_type="choice",
                )
            )
        elif content.lower().startswith("date:"):
            fmt = content[5:].strip()
            name = f"date_{len(fields) + 1}"
            fields.append(
                FormField(
                    name=name,
                    label=f"Date ({fmt})",
                    default=JalaliDate.today().isoformat_fa(),
                    field_type="date",
                )
            )
        else:
            if ":" in content:
                key, default = content.split(":", 1)
                key, default = key.strip(), default.strip()
            else:
                key, default = content, ""
            if key not in seen:
                seen.add(key)
                fields.append(
                    FormField(
                        name=key,
                        label=key.replace("_", " ").title(),
                        default=default,
                        field_type="text",
                    )
                )
    return fields


def render_form_template(template: str, values: dict[str, str]) -> str:
    """Substitute user form field inputs into template."""
    choice_idx = 1
    date_idx = 1

    def _sub(m: re.Match[str]) -> str:
        nonlocal choice_idx, date_idx
        content = m.group(1).strip()
        if content.lower().startswith("choice:"):
            key = f"choice_{choice_idx}"
            choice_idx += 1
            return values.get(key, values.get(content, ""))
        if content.lower().startswith("date:"):
            key = f"date_{date_idx}"
            date_idx += 1
            return values.get(key, values.get(content, ""))
        key = content.split(":", 1)[0].strip()
        return values.get(key, m.group(0))

    rendered = re.sub(r"\{\{\s*([^}]+)\s*\}\}", _sub, template)
    return render_template(rendered)


def render_template(template: str) -> str:
    """Replace {{placeholder}} with dynamic date/time/uuid/math values."""
    if "{{" not in template:
        return template

    from ravan.core.calc import calculate

    def _eval_math(match: re.Match[str]) -> str:
        expr = match.group(1).strip()
        res = calculate(expr)
        return res if res is not None else match.group(0)

    if "{{clipboard}}" in template.lower() or "{{clip}}" in template.lower():
        clip_val = _fetch_clipboard()
        template = re.sub(
            r"\{\{\s*(?:clipboard|clip)\s*\}\}",
            lambda _: clip_val,  # lambda prevents backref interpretation of clipboard content
            template,
            flags=re.IGNORECASE,
        )

    rendered = re.sub(
        r"\{\{\s*(?:math|calc|eval)\s*:\s*([^}]+)\s*\}\}",
        _eval_math,
        template,
    )

    values = get_macro_values()
    rendered = re.sub(
        r"\{\{\s*([^\s}]+)\s*\}\}",
        lambda m: values.get(m.group(1).lower(), m.group(0)),
        rendered,
    )
    return rendered


def parse_cursor_placeholder(text: str) -> tuple[str, int | None]:
    for marker in ("$0", "{{cursor}}", "{{0}}"):
        pos = text.find(marker)
        if pos != -1:
            clean = text[:pos] + text[pos + len(marker) :]
            return clean, len(clean) - pos
    if "|" in text:
        pos = text.find("|")
        clean = text[:pos] + text[pos + 1 :]
        return clean, len(clean) - pos
    return text, None


def snippets_to_json(snippets: list[Snippet], indent: int = 2) -> str:
    data = [
        {
            "trigger": s.trigger,
            "replacement": s.replacement,
            "enabled": getattr(s, "enabled", True),
            "is_regex": getattr(s, "is_regex", False),
            "app_filter": getattr(s, "app_filter", ""),
            "is_image": getattr(s, "is_image", False),
        }
        for s in snippets
    ]
    return json.dumps(data, ensure_ascii=False, indent=indent)


def snippets_from_json(json_str: str) -> list[Snippet]:
    data = json.loads(json_str)
    if not isinstance(data, list):
        raise ValueError("Snippets JSON must be an array of objects")
    snippets: list[Snippet] = []
    for item in data:
        if isinstance(item, dict) and "trigger" in item and "replacement" in item:
            trig = str(item["trigger"]).strip()
            repl = str(item["replacement"])
            enabled = bool(item.get("enabled", True))
            if trig:
                snippets.append(
                    Snippet(
                        trigger=trig,
                        replacement=repl,
                        enabled=enabled,
                        is_regex=bool(item.get("is_regex", False)),
                        app_filter=str(item.get("app_filter", "")),
                        is_image=bool(item.get("is_image", False)),
                    )
                )
    return snippets


class SnippetEngine:
    def __init__(
        self,
        snippets: list[Snippet | tuple[str, str]],
        include_default_macros: bool = True,
    ) -> None:
        self._raw_snippets: list[Snippet] = []
        for s in snippets:
            if isinstance(s, Snippet):
                self._raw_snippets.append(s)
            elif isinstance(s, (tuple, list)) and len(s) >= 2:
                self._raw_snippets.append(Snippet(trigger=s[0], replacement=s[1]))
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
        return cls([s for s in cfg.snippets if getattr(s, "enabled", True)])

    def find_matching_snippet(
        self, word: str, app_name: str | None = None
    ) -> tuple[Snippet, str] | None:
        """Find matching snippet accounting for per-app filters and regex triggers."""
        app_low = app_name.lower().strip() if app_name else ""

        for s in self._raw_snippets:
            if not getattr(s, "enabled", True):
                continue

            filt = getattr(s, "app_filter", "")
            if filt and app_low:
                allowed = [a.strip().lower() for a in filt.split(",") if a.strip()]
                base = os.path.basename(app_low)
                base_no_ext = os.path.splitext(base)[0]
                if allowed and not any(a in (app_low, base, base_no_ext) for a in allowed):
                    continue

            is_reg = getattr(s, "is_regex", False) or s.trigger.startswith("re:")
            if is_reg:
                pat = s.trigger[3:] if s.trigger.startswith("re:") else s.trigger
                m = safe_regex_match(pat, word)
                if m is not None:
                    expanded_repl = expand_capture_groups(s.replacement, m)
                    return s, expanded_repl
            elif s.trigger == word:
                return s, s.replacement

        return None

    def expand_with_cursor(
        self, word: str, app_name: str | None = None
    ) -> tuple[str, int | None] | None:
        """Expand word into (replacement_text, cursor_offset_from_end) or None."""
        match = self.find_matching_snippet(word, app_name)
        if match is not None:
            snippet, repl_text = match
            rendered = render_template(repl_text)
            clean_text, cursor_offset = parse_cursor_placeholder(rendered)
            return clean_text, cursor_offset

        if word in self._macros:
            val = self._macros[word]()
            clean_text, cursor_offset = parse_cursor_placeholder(val)
            return clean_text, cursor_offset

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

    def expand(self, word: str, app_name: str | None = None) -> str | None:
        res = self.expand_with_cursor(word, app_name=app_name)
        return res[0] if res is not None else None

    def all(self) -> list[tuple[str, str]]:
        return [(s.trigger, s.replacement) for s in self._raw_snippets]

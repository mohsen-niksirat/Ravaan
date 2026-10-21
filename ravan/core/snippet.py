"""Text expansion snippets with dynamic templates, date/time macros, math evaluation, and cursor placement."""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import Callable
from datetime import date

from .config import Config, Snippet
from .jalali import JalaliDate, current_time_str
from .snippet_forms import (
    FormController,
    FormFieldSpec,
    clear_remembered_values,
    get_remembered_value,
    parse_form_fields,
    render_form_template_with_specs,
    save_remembered_value,
)
from .snippet_groups import (
    SnippetGroup,
    group_matches_app,
    resolve_image_snippet,
    snippet_matches_app,
    validate_image_path,
)
from .snippet_macros import fetch_clipboard, get_macro_values
from .snippet_regex import (
    expand_capture_groups,
    extract_regex_pattern,
    preview_regex_expansion,
    safe_regex_match,
    validate_regex_trigger,
)

# Backward-compatible alias
FormField = FormFieldSpec

_fetch_clipboard = fetch_clipboard

log = logging.getLogger(__name__)

__all__ = [
    "FormController",
    "FormField",
    "FormFieldSpec",
    "SnippetEngine",
    "SnippetGroup",
    "clear_remembered_values",
    "expand_capture_groups",
    "extract_form_fields",
    "extract_regex_pattern",
    "get_remembered_value",
    "group_matches_app",
    "parse_cursor_placeholder",
    "parse_form_fields",
    "preview_regex_expansion",
    "render_form_template",
    "render_form_template_with_specs",
    "render_template",
    "resolve_image_snippet",
    "safe_regex_match",
    "save_remembered_value",
    "snippet_matches_app",
    "snippets_from_json",
    "snippets_to_json",
    "validate_image_path",
    "validate_regex_trigger",
]


def extract_form_fields(
    template: str, snippet_trigger: str = ""
) -> list[FormFieldSpec]:
    """Extract interactive user form fields from template (Snippets 3.0)."""
    return parse_form_fields(template, snippet_trigger=snippet_trigger)


def render_form_template(template: str, values: dict[str, str]) -> str:
    """Substitute user form field inputs into template."""
    fields = parse_form_fields(template)
    return render_form_template_with_specs(template, values, fields)


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
            "groups": getattr(s, "groups", []),
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
                        groups=[str(g).strip() for g in item.get("groups", []) if str(g).strip()],
                    )
                )
    return snippets


class SnippetEngine:
    def __init__(
        self,
        snippets: list[Snippet | tuple[str, str]],
        include_default_macros: bool = True,
        groups: list[SnippetGroup] | None = None,
    ) -> None:
        self._raw_snippets: list[Snippet] = []
        for s in snippets:
            if isinstance(s, Snippet):
                self._raw_snippets.append(s)
            elif isinstance(s, (tuple, list)) and len(s) >= 2:
                self._raw_snippets.append(Snippet(trigger=s[0], replacement=s[1]))
        self._groups: list[SnippetGroup] = list(groups or [])
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
        return cls(
            [s for s in cfg.snippets if getattr(s, "enabled", True)],
            groups=getattr(cfg, "snippet_groups", None),
        )

    def find_matching_snippet(
        self,
        word: str,
        app_name: str | None = None,
        include_regex: bool = True,
        window_class: str | None = None,
    ) -> tuple[Snippet, str] | None:
        """Find matching snippet accounting for per-app filters and regex triggers."""
        for s in self._raw_snippets:
            if not getattr(s, "enabled", True):
                continue

            if not snippet_matches_app(s, app_name, window_class=window_class, groups=self._groups):
                continue

            is_reg = getattr(s, "is_regex", False) or s.trigger.startswith("re:")
            if is_reg:
                if not include_regex:
                    continue
                pat = s.trigger[3:] if s.trigger.startswith("re:") else s.trigger
                m = safe_regex_match(pat, word)
                if m is not None:
                    expanded_repl = expand_capture_groups(s.replacement, m)
                    return s, expanded_repl
            elif s.trigger == word:
                return s, s.replacement

        return None

    def find_matching_regex_snippet(
        self,
        word: str,
        app_name: str | None = None,
        window_class: str | None = None,
    ) -> tuple[Snippet, str] | None:
        """Find matching regex snippet only (used when regex runs after auto-fix/translit)."""
        for s in self._raw_snippets:
            if not getattr(s, "enabled", True):
                continue

            is_reg = getattr(s, "is_regex", False) or s.trigger.startswith("re:")
            if not is_reg:
                continue

            if not snippet_matches_app(s, app_name, window_class=window_class, groups=self._groups):
                continue

            pat = s.trigger[3:] if s.trigger.startswith("re:") else s.trigger
            m = safe_regex_match(pat, word)
            if m is not None:
                expanded_repl = expand_capture_groups(s.replacement, m)
                return s, expanded_repl

        return None

    def expand_with_cursor(
        self,
        word: str,
        app_name: str | None = None,
        include_regex: bool = True,
        window_class: str | None = None,
    ) -> tuple[str, int | None] | None:
        """Expand word into (replacement_text, cursor_offset_from_end) or None."""
        match = self.find_matching_snippet(
            word, app_name, include_regex=include_regex, window_class=window_class
        )
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

    def expand(
        self,
        word: str,
        app_name: str | None = None,
        include_regex: bool = True,
        window_class: str | None = None,
    ) -> str | None:
        res = self.expand_with_cursor(
            word, app_name=app_name, include_regex=include_regex, window_class=window_class
        )
        return res[0] if res is not None else None

    def all(self) -> list[tuple[str, str]]:
        return [(s.trigger, s.replacement) for s in self._raw_snippets]

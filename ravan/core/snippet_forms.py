"""Interactive snippet placeholder forms parser, state controller, and persistent remember cache."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from ravan.core.snippet_macros import BUILTIN_PLACEHOLDERS

log = logging.getLogger(__name__)

# Known modifiers that are keywords rather than literal default values
_MODIFIER_KEYWORDS = {"remember", "multiline", "required", "choice", "date"}

# In-memory store for remembered fields: (snippet_trigger, field_name) -> value
_REMEMBERED_FIELDS: dict[tuple[str, str], str] = {}
_REMEMBER_CACHE_FILE: Path | None = None


def get_remember_cache_path() -> Path:
    global _REMEMBER_CACHE_FILE
    if _REMEMBER_CACHE_FILE is None:
        try:
            from ravan.core.config import config_dir

            _REMEMBER_CACHE_FILE = config_dir() / "snippet_forms_remember.json"
        except Exception:
            _REMEMBER_CACHE_FILE = Path.home() / ".ravaan" / "snippet_forms_remember.json"
    return _REMEMBER_CACHE_FILE


def load_remember_cache() -> None:
    path = get_remember_cache_path()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for key_str, val in data.items():
                if "::" in key_str:
                    trig, name = key_str.split("::", 1)
                    _REMEMBERED_FIELDS[(trig, name)] = str(val)
        except Exception as exc:  # noqa: BLE001
            log.debug("Failed to load snippet form remember cache: %s", exc)


def save_remember_cache() -> None:
    path = get_remember_cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {f"{trig}::{name}": val for (trig, name), val in _REMEMBERED_FIELDS.items()}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        log.debug("Failed to save snippet form remember cache: %s", exc)


def get_remembered_value(snippet_trigger: str, field_name: str) -> str | None:
    if not _REMEMBERED_FIELDS:
        load_remember_cache()
    return _REMEMBERED_FIELDS.get((snippet_trigger.strip(), field_name.strip()))


def save_remembered_value(snippet_trigger: str, field_name: str, value: str) -> None:
    _REMEMBERED_FIELDS[(snippet_trigger.strip(), field_name.strip())] = value
    save_remember_cache()


def clear_remembered_values() -> None:
    _REMEMBERED_FIELDS.clear()
    path = get_remember_cache_path()
    if path.is_file():
        try:
            path.unlink()
        except Exception:  # noqa: BLE001
            pass


@dataclass
class FormFieldSpec:
    name: str
    label: str
    default: str = ""
    choices: list[str] = field(default_factory=list)
    field_type: str = "text"  # "text" | "multiline" | "choice" | "date"
    remember: bool = False
    required: bool = True  # Required by default for form integrity


def find_balanced_placeholders(text: str) -> list[tuple[str, int, int]]:
    """Find all top-level {{...}} placeholders with support for nested {{...}} inside defaults."""
    results: list[tuple[str, int, int]] = []
    i = 0
    n = len(text)
    while i < n:
        start = text.find("{{", i)
        if start == -1:
            break
        depth = 1
        pos = start + 2
        while pos < n and depth > 0:
            if text.startswith("{{", pos):
                depth += 1
                pos += 2
            elif text.startswith("}}", pos):
                depth -= 1
                if depth == 0:
                    results.append((text[start + 2 : pos], start, pos + 2))
                    pos += 2
                    break
                pos += 2
            else:
                pos += 1
        i = pos
    return results


def parse_form_fields(
    template: str, snippet_trigger: str = ""
) -> list[FormFieldSpec]:
    """Parse dynamic form fields from template string preserving trigger order."""
    fields: list[FormFieldSpec] = []
    seen: dict[str, FormFieldSpec] = {}

    placeholders = find_balanced_placeholders(template)
    for content, _s, _e in placeholders:
        content = content.strip()
        low = content.lower()
        if (
            low in BUILTIN_PLACEHOLDERS
            or low in ("$0", "0", "cursor")
            or low.startswith("calc:")
            or low.startswith("math:")
            or low.startswith("eval:")
        ):
            continue

        raw_default: str | None = None
        if "=" in content:
            pre_eq, post_eq = content.split("=", 1)
            raw_default = post_eq.strip()
            content = pre_eq.strip()

        parts = [p.strip() for p in content.split(":") if p.strip()]
        if not parts:
            continue

        raw_name = parts[0]
        modifiers = set(p.lower() for p in parts[1:])

        field_type = "text"
        choices: list[str] = []
        is_remember = "remember" in modifiers
        is_multiline = "multiline" in modifiers

        if is_multiline:
            field_type = "multiline"

        if (
            raw_name.lower() == "choice"
            or "choice" in modifiers
            or any(p.lower().startswith("choice") for p in parts[1:])
        ):
            field_type = "choice"
            for p in parts[1:]:
                if "|" in p:
                    choices = [c.strip() for c in p.split("|") if c.strip()]
                    break
        elif raw_name.lower() == "date" or "date" in modifiers:
            field_type = "date"

        if raw_default is None:
            if field_type != "date":
                for p in parts[1:]:
                    p_low = p.lower()
                    if (
                        p_low not in _MODIFIER_KEYWORDS
                        and not p_low.startswith("choice")
                        and "|" not in p
                    ):
                        raw_default = p
                        break

        default_val = ""
        if raw_default is not None:
            from ravan.core.snippet import render_template

            default_val = render_template(raw_default)
        elif field_type == "choice" and choices:
            default_val = choices[0]
        elif field_type == "date":
            from ravan.core.jalali import JalaliDate

            default_val = JalaliDate.today().isoformat_fa()

        if is_remember and snippet_trigger:
            cached = get_remembered_value(snippet_trigger, raw_name)
            if cached is not None:
                default_val = cached

        if raw_name in seen:
            existing = seen[raw_name]
            if is_remember:
                existing.remember = True
            if is_multiline:
                existing.field_type = "multiline"
            continue

        label = raw_name.replace("_", " ").title()
        spec = FormFieldSpec(
            name=raw_name,
            label=label,
            default=default_val,
            choices=choices,
            field_type=field_type,
            remember=is_remember,
            required=True,
        )
        seen[raw_name] = spec
        fields.append(spec)

    return fields


def render_form_template_with_specs(
    template: str, values: dict[str, str], fields: list[FormFieldSpec]
) -> str:
    """Substitute user-supplied form values into template placeholders."""
    from ravan.core.snippet import render_template

    placeholders = find_balanced_placeholders(template)
    # Replace from back to front so character indices remain valid
    res = template
    date_count = 1
    choice_count = 1
    for content, start, end in reversed(placeholders):
        content_stripped = content.strip()
        low = content_stripped.lower()
        if (
            low in BUILTIN_PLACEHOLDERS
            or low in ("$0", "0", "cursor")
            or low.startswith("calc:")
            or low.startswith("math:")
            or low.startswith("eval:")
        ):
            continue

        base = content_stripped.split("=", 1)[0].split(":", 1)[0].strip()
        val = None
        if base in values:
            val = values[base]
        elif base == "choice" and f"choice_{choice_count}" in values:
            val = values[f"choice_{choice_count}"]
            choice_count += 1
        elif base == "date" and f"date_{date_count}" in values:
            val = values[f"date_{date_count}"]
            date_count += 1

        if val is not None:
            res = res[:start] + val + res[end:]

    return render_template(res)


class FormController:
    """Headless state controller for interactive snippet placeholder forms."""

    def __init__(
        self,
        template: str,
        snippet_trigger: str = "",
        initial_values: dict[str, str] | None = None,
    ) -> None:
        self.template = template
        self.snippet_trigger = snippet_trigger
        self.fields = parse_form_fields(template, snippet_trigger=snippet_trigger)
        self.values: dict[str, str] = {}
        self.errors: dict[str, str] = {}

        # Initialize defaults
        for fld in self.fields:
            self.values[fld.name] = fld.default

        if initial_values:
            self.values.update(initial_values)

    def set_value(self, name: str, value: str) -> None:
        self.values[name] = value
        if name in self.errors:
            del self.errors[name]

    def validate(self) -> bool:
        self.errors.clear()
        for fld in self.fields:
            val = self.values.get(fld.name, "").strip()
            if fld.required and not val:
                self.errors[fld.name] = f"Field '{fld.label}' cannot be empty"
        return len(self.errors) == 0

    def confirm(self) -> tuple[bool, str]:
        """Validate form inputs, commit remembered fields, and render template.

        Returns:
            (is_valid, rendered_text_or_error)
        """
        if not self.validate():
            first_err = next(iter(self.errors.values()))
            return False, first_err

        # Save opt-in remembered values
        for fld in self.fields:
            if fld.remember and self.snippet_trigger:
                save_remembered_value(
                    self.snippet_trigger, fld.name, self.values.get(fld.name, "")
                )

        rendered = render_form_template_with_specs(
            self.template, self.values, self.fields
        )
        return True, rendered

    def cancel(self) -> None:
        pass

"""Builtin macro values and placeholder calculations for snippet templates."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timedelta

from .jalali import JalaliDate, current_time_str
from .normalizer import en_to_fa_digits, fa_to_en_digits

BUILTIN_PLACEHOLDERS = {
    "today", "shamsi", "shamsi_en", "tarikh", "tarikh_fa", "tarikh_full",
    "yesterday", "yesterday_en", "dirooz", "دیروز", "tomorrow", "tomorrow_en",
    "farda", "فردا", "year", "year_fa", "saal", "سال", "month", "mah", "ماه",
    "month_num", "month_num_fa", "day", "day_fa", "rooz", "روز", "weekday",
    "hafteh", "روز_هفته", "date", "date_en", "gregorian", "gregorian_year",
    "time", "time_fa", "time_sec", "time_sec_fa", "timestamp", "uuid", "guid",
    "clipboard", "clip", "cursor", "0",
    "greeting", "greeting_fa", "greeting_en", "وقت_بخیر", "سلام_وقت", "app",
}

_REL_DATE_RE = re.compile(
    r"^(jalali|shamsi|shamsi_en|tarikh|tarikh_fa|tarikh_full|date|date_en|gregorian|weekday|روز_هفته)\s*:\s*([+-]?\s*[0-9۰-۹]+)\s*(d|w|m|y|day|days|week|weeks|month|months|year|years|روز|هفته|ماه|سال)?$",
    re.IGNORECASE,
)

_IF_APP_RE = re.compile(
    r"^\{\{\s*if_app\s*:\s*([^:}]+)\s*:\s*([^|}]+)(?:\|([^}]*))?\}\}$",
    re.IGNORECASE,
)


def is_builtin_macro_expr(expr: str) -> bool:
    """Return True if a {{...}} inner expression is a built-in dynamic or relative macro."""
    low = expr.strip().lower()
    if low in BUILTIN_PLACEHOLDERS or low in ("$0", "0", "cursor"):
        return True
    if low.startswith(("calc:", "math:", "eval:", "if_app:")):
        return True
    return _REL_DATE_RE.match(low) is not None


def get_time_greeting(lang: str = "fa", hour: int | None = None) -> str:
    """Return context-aware time-of-day greeting in Persian or English."""
    h = datetime.now().hour if hour is None else (hour % 24)
    if lang == "en":
        if 5 <= h < 12:
            return "Good morning"
        if 12 <= h < 17:
            return "Good afternoon"
        if 17 <= h < 22:
            return "Good evening"
        return "Good night"
    if 5 <= h < 12:
        return "صبح بخیر"
    if 12 <= h < 15:
        return "ظهر بخیر"
    if 15 <= h < 21:
        return "عصر بخیر"
    return "شب بخیر"


def _eval_relative_date(kind: str, amount_str: str, unit_str: str | None, base_date: date | None = None) -> str:
    amt = int(fa_to_en_digits(amount_str).replace(" ", ""))
    u = (unit_str or "d").lower()
    if u in ("w", "week", "weeks", "هفته"):
        days = amt * 7
    elif u in ("m", "month", "months", "ماه"):
        days = amt * 30
    elif u in ("y", "year", "years", "سال"):
        days = amt * 365
    else:
        days = amt
    target_g = (base_date or date.today()) + timedelta(days=days)
    j = JalaliDate.from_gregorian(target_g)
    k = kind.lower()
    if k in ("jalali", "shamsi"):
        return j.isoformat_fa()
    if k == "shamsi_en":
        return j.isoformat()
    if k in ("tarikh", "tarikh_fa"):
        return j.format_persian(include_weekday=False)
    if k == "tarikh_full":
        return j.format_persian(include_weekday=True)
    if k in ("weekday", "روز_هفته"):
        return j.weekday_name()
    return target_g.isoformat()


def expand_dynamic_macros(template: str, app_name: str | None = None) -> str:
    """Expand relative dates ({{jalali:+3d}}) and app conditionals ({{if_app:telegram:A|B}})."""
    if "{{" not in template:
        return template

    app_clean = (app_name or "").strip().lower()

    def _replace_token(match: re.Match[str]) -> str:
        full = match.group(0)
        inner = match.group(1).strip()

        if_m = _IF_APP_RE.match(full)
        if if_m:
            targets = [t.strip().lower() for t in if_m.group(1).split(",") if t.strip()]
            true_val = if_m.group(2)
            false_val = if_m.group(3) or ""
            matched = any(
                app_clean == t or app_clean.removesuffix(".exe") == t.removesuffix(".exe") or (t and t in app_clean)
                for t in targets
            ) if app_clean else False
            return true_val if matched else false_val

        rel_m = _REL_DATE_RE.match(inner)
        if rel_m:
            return _eval_relative_date(rel_m.group(1), rel_m.group(2), rel_m.group(3))

        return full

    return re.sub(r"\{\{\s*([^}]+)\s*\}\}", _replace_token, template)


def fetch_clipboard() -> str:
    """Safely obtain current clipboard text without hard-failing on non-Windows platforms."""
    try:
        from ravan.platform.clipboard import get_clipboard_text

        return get_clipboard_text() or ""
    except Exception:
        return ""


def get_macro_values(app_name: str | None = None) -> dict[str, str]:
    """Calculate current values for template placeholders."""
    j = JalaliDate.today()
    today_g = date.today()
    yesterday_j = JalaliDate.from_gregorian(today_g - timedelta(days=1))
    tomorrow_j = JalaliDate.from_gregorian(today_g + timedelta(days=1))
    now = datetime.now()
    greet_fa = get_time_greeting("fa", now.hour)
    greet_en = get_time_greeting("en", now.hour)

    return {
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
        "date": today_g.isoformat(),
        "date_en": today_g.isoformat(),
        "gregorian": today_g.isoformat(),
        "gregorian_year": str(today_g.year),
        "time": current_time_str(persian_digits=False),
        "time_fa": current_time_str(persian_digits=True),
        "time_sec": now.strftime("%H:%M:%S"),
        "time_sec_fa": en_to_fa_digits(now.strftime("%H:%M:%S")),
        "timestamp": str(int(now.timestamp())),
        "uuid": str(uuid.uuid4()),
        "guid": str(uuid.uuid4()),
        "greeting": greet_fa,
        "greeting_fa": greet_fa,
        "وقت_بخیر": greet_fa,
        "سلام_وقت": greet_fa,
        "greeting_en": greet_en,
        "app": (app_name or "").strip(),
    }

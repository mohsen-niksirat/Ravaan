"""Builtin macro values and placeholder calculations for snippet templates."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from .jalali import JalaliDate, current_time_str
from .normalizer import en_to_fa_digits

BUILTIN_PLACEHOLDERS = {
    "today", "shamsi", "shamsi_en", "tarikh", "tarikh_fa", "tarikh_full",
    "yesterday", "yesterday_en", "dirooz", "دیروز", "tomorrow", "tomorrow_en",
    "farda", "فردا", "year", "year_fa", "saal", "سال", "month", "mah", "ماه",
    "month_num", "month_num_fa", "day", "day_fa", "rooz", "روز", "weekday",
    "hafteh", "روز_هفته", "date", "date_en", "gregorian", "gregorian_year",
    "time", "time_fa", "time_sec", "time_sec_fa", "timestamp", "uuid", "guid",
    "clipboard", "clip", "cursor", "0",
}


def fetch_clipboard() -> str:
    """Safely obtain current clipboard text without hard-failing on non-Windows platforms."""
    try:
        from ravan.platform.clipboard import get_clipboard_text

        return get_clipboard_text() or ""
    except Exception:
        return ""


def get_macro_values() -> dict[str, str]:
    """Calculate current values for template placeholders."""
    j = JalaliDate.today()
    today_g = date.today()
    yesterday_j = JalaliDate.from_gregorian(today_g - timedelta(days=1))
    tomorrow_j = JalaliDate.from_gregorian(today_g + timedelta(days=1))
    now = datetime.now()

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
    }

"""Offline unit, currency (Rial/Toman/Words), and timezone converter for Ravaan Calc v3."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ravan.core.normalizer import en_to_fa_digits, fa_to_en_digits, normalize_arabic_chars
from ravan.core.num2words import num_to_persian_words


@dataclass(frozen=True)
class UnitSpec:
    category: str
    factor: float  # Multiplier to base unit (m, g, B, sqm, L)
    label_en: str
    label_fa: str


# Base units: length="m", mass="g", data="B", area="sqm", volume="L"
_UNITS: dict[str, UnitSpec] = {
    # Length (base: meter)
    "km": UnitSpec("length", 1000.0, "km", "کیلومتر"),
    "kilometer": UnitSpec("length", 1000.0, "km", "کیلومتر"),
    "kilometers": UnitSpec("length", 1000.0, "km", "کیلومتر"),
    "کیلومتر": UnitSpec("length", 1000.0, "km", "کیلومتر"),
    "m": UnitSpec("length", 1.0, "m", "متر"),
    "meter": UnitSpec("length", 1.0, "m", "متر"),
    "meters": UnitSpec("length", 1.0, "m", "متر"),
    "متر": UnitSpec("length", 1.0, "m", "متر"),
    "cm": UnitSpec("length", 0.01, "cm", "سانتی‌متر"),
    "centimeter": UnitSpec("length", 0.01, "cm", "سانتی‌متر"),
    "سانتیمتر": UnitSpec("length", 0.01, "cm", "سانتی‌متر"),
    "سانتی‌متر": UnitSpec("length", 0.01, "cm", "سانتی‌متر"),
    "سانت": UnitSpec("length", 0.01, "cm", "سانتی‌متر"),
    "mm": UnitSpec("length", 0.001, "mm", "میلی‌متر"),
    "millimeter": UnitSpec("length", 0.001, "mm", "میلی‌متر"),
    "میلیمتر": UnitSpec("length", 0.001, "mm", "میلی‌متر"),
    "میلی‌متر": UnitSpec("length", 0.001, "mm", "میلی‌متر"),
    "mi": UnitSpec("length", 1609.344, "mi", "مایل"),
    "mile": UnitSpec("length", 1609.344, "mi", "مایل"),
    "miles": UnitSpec("length", 1609.344, "mi", "مایل"),
    "مایل": UnitSpec("length", 1609.344, "mi", "مایل"),
    "yd": UnitSpec("length", 0.9144, "yd", "یارد"),
    "yard": UnitSpec("length", 0.9144, "yd", "یارد"),
    "یارد": UnitSpec("length", 0.9144, "yd", "یارد"),
    "ft": UnitSpec("length", 0.3048, "ft", "فوت"),
    "foot": UnitSpec("length", 0.3048, "ft", "فوت"),
    "feet": UnitSpec("length", 0.3048, "ft", "فوت"),
    "فوت": UnitSpec("length", 0.3048, "ft", "فوت"),
    "in": UnitSpec("length", 0.0254, "in", "اینچ"),
    "inch": UnitSpec("length", 0.0254, "in", "اینچ"),
    "inches": UnitSpec("length", 0.0254, "in", "اینچ"),
    "اینچ": UnitSpec("length", 0.0254, "in", "اینچ"),
    # Mass (base: gram)
    "ton": UnitSpec("mass", 1_000_000.0, "ton", "تن"),
    "tons": UnitSpec("mass", 1_000_000.0, "ton", "تن"),
    "تن": UnitSpec("mass", 1_000_000.0, "ton", "تن"),
    "kg": UnitSpec("mass", 1000.0, "kg", "کیلوگرم"),
    "kilogram": UnitSpec("mass", 1000.0, "kg", "کیلوگرم"),
    "کیلوگرم": UnitSpec("mass", 1000.0, "kg", "کیلوگرم"),
    "کیلو": UnitSpec("mass", 1000.0, "kg", "کیلوگرم"),
    "g": UnitSpec("mass", 1.0, "g", "گرم"),
    "gr": UnitSpec("mass", 1.0, "g", "گرم"),
    "gram": UnitSpec("mass", 1.0, "g", "گرم"),
    "grams": UnitSpec("mass", 1.0, "g", "گرم"),
    "گرم": UnitSpec("mass", 1.0, "g", "گرم"),
    "mg": UnitSpec("mass", 0.001, "mg", "میلی‌گرم"),
    "میلیگرم": UnitSpec("mass", 0.001, "mg", "میلی‌گرم"),
    "میلی‌گرم": UnitSpec("mass", 0.001, "mg", "میلی‌گرم"),
    "lb": UnitSpec("mass", 453.59237, "lb", "پوند"),
    "lbs": UnitSpec("mass", 453.59237, "lb", "پوند"),
    "pound": UnitSpec("mass", 453.59237, "lb", "پوند"),
    "pounds": UnitSpec("mass", 453.59237, "lb", "پوند"),
    "پوند": UnitSpec("mass", 453.59237, "lb", "پوند"),
    "oz": UnitSpec("mass", 28.349523125, "oz", "اونس"),
    "ounce": UnitSpec("mass", 28.349523125, "oz", "اونس"),
    "اونس": UnitSpec("mass", 28.349523125, "oz", "اونس"),
    "mesghal": UnitSpec("mass", 4.6083, "mesghal", "مثقال"),
    "مثقال": UnitSpec("mass", 4.6083, "mesghal", "مثقال"),
    "soot": UnitSpec("mass", 0.001, "soot", "سوت"),
    "سوت": UnitSpec("mass", 0.001, "soot", "سوت"),
    # Digital Storage (base: byte, decimal/binary standard 1024)
    "b": UnitSpec("data", 1.0, "B", "بایت"),
    "byte": UnitSpec("data", 1.0, "B", "بایت"),
    "bytes": UnitSpec("data", 1.0, "B", "بایت"),
    "بایت": UnitSpec("data", 1.0, "B", "بایت"),
    "kb": UnitSpec("data", 1024.0, "KB", "کیلوبایت"),
    "کیلوبایت": UnitSpec("data", 1024.0, "KB", "کیلوبایت"),
    "mb": UnitSpec("data", 1024.0**2, "MB", "مگابایت"),
    "مگابایت": UnitSpec("data", 1024.0**2, "MB", "مگابایت"),
    "gb": UnitSpec("data", 1024.0**3, "GB", "گیگابایت"),
    "گیگابایت": UnitSpec("data", 1024.0**3, "GB", "گیگابایت"),
    "گیگ": UnitSpec("data", 1024.0**3, "GB", "گیگابایت"),
    "tb": UnitSpec("data", 1024.0**4, "TB", "ترابایت"),
    "ترابایت": UnitSpec("data", 1024.0**4, "TB", "ترابایت"),
    # Area (base: square meter)
    "sqm": UnitSpec("area", 1.0, "m²", "مترمربع"),
    "مترمربع": UnitSpec("area", 1.0, "m²", "مترمربع"),
    "ha": UnitSpec("area", 10_000.0, "ha", "هکتار"),
    "hectare": UnitSpec("area", 10_000.0, "ha", "هکتار"),
    "هکتار": UnitSpec("area", 10_000.0, "ha", "هکتار"),
    "sqft": UnitSpec("area", 0.09290304, "ft²", "فوت‌مربع"),
    # Volume (base: liter)
    "l": UnitSpec("volume", 1.0, "L", "لیتر"),
    "liter": UnitSpec("volume", 1.0, "L", "لیتر"),
    "liters": UnitSpec("volume", 1.0, "L", "لیتر"),
    "لیتر": UnitSpec("volume", 1.0, "L", "لیتر"),
    "ml": UnitSpec("volume", 0.001, "mL", "میلی‌لیتر"),
    "میلیلیتر": UnitSpec("volume", 0.001, "mL", "میلی‌لیتر"),
    "میلی‌لیتر": UnitSpec("volume", 0.001, "mL", "میلی‌لیتر"),
    "gal": UnitSpec("volume", 3.785411784, "gal", "گالن"),
    "gallon": UnitSpec("volume", 3.785411784, "gal", "گالن"),
    "گالن": UnitSpec("volume", 3.785411784, "gal", "گالن"),
    # Currency (base: Rial)
    "rial": UnitSpec("currency", 1.0, "Rial", "ریال"),
    "rials": UnitSpec("currency", 1.0, "Rial", "ریال"),
    "irr": UnitSpec("currency", 1.0, "Rial", "ریال"),
    "ریال": UnitSpec("currency", 1.0, "Rial", "ریال"),
    "toman": UnitSpec("currency", 10.0, "Toman", "تومان"),
    "tomans": UnitSpec("currency", 10.0, "Toman", "تومان"),
    "irt": UnitSpec("currency", 10.0, "Toman", "تومان"),
    "تومان": UnitSpec("currency", 10.0, "Toman", "تومان"),
    "تومن": UnitSpec("currency", 10.0, "Toman", "تومان"),
}

_TEMP_ALIASES: dict[str, tuple[str, str, str]] = {
    "c": ("c", "°C", "°C"),
    "celsius": ("c", "°C", "°C"),
    "سانتیگراد": ("c", "°C", "°C"),
    "سانتی‌گراد": ("c", "°C", "°C"),
    "سیلسیوس": ("c", "°C", "°C"),
    "f": ("f", "°F", "°F"),
    "fahrenheit": ("f", "°F", "°F"),
    "فارنهایت": ("f", "°F", "°F"),
    "k": ("k", "K", "K"),
    "kelvin": ("k", "K", "K"),
    "کلوین": ("k", "K", "K"),
}

# Offline UTC offsets in minutes for major cities & timezones
_TZ_OFFSETS_MIN: dict[str, tuple[int, str, str]] = {
    "tehran": (210, "Tehran", "تهران"),
    "irst": (210, "Tehran", "تهران"),
    "iran": (210, "Tehran", "تهران"),
    "تهران": (210, "Tehran", "تهران"),
    "ایران": (210, "Tehran", "تهران"),
    "utc": (0, "UTC", "UTC"),
    "gmt": (0, "GMT", "GMT"),
    "london": (0, "London", "لندن"),
    "لندن": (0, "London", "لندن"),
    "paris": (60, "Paris", "پاریس"),
    "پاریس": (60, "Paris", "پاریس"),
    "berlin": (60, "Berlin", "برلین"),
    "برلین": (60, "Berlin", "برلین"),
    "cet": (60, "CET", "اروپای مرکزی"),
    "istanbul": (180, "Istanbul", "استانبول"),
    "استانبول": (180, "Istanbul", "استانبول"),
    "moscow": (180, "Moscow", "مسکو"),
    "مسکو": (180, "Moscow", "مسکو"),
    "dubai": (240, "Dubai", "دبی"),
    "دبی": (240, "Dubai", "دبی"),
    "baku": (240, "Baku", "باکو"),
    "باکو": (240, "Baku", "باکو"),
    "kabul": (270, "Kabul", "کابل"),
    "کابل": (270, "Kabul", "کابل"),
    "ist": (330, "India", "هند"),
    "india": (330, "India", "هند"),
    "هند": (330, "India", "هند"),
    "beijing": (480, "Beijing", "پکن"),
    "پکن": (480, "Beijing", "پکن"),
    "tokyo": (540, "Tokyo", "توکیو"),
    "توکیو": (540, "Tokyo", "توکیو"),
    "sydney": (600, "Sydney", "سیدنی"),
    "سیدنی": (600, "Sydney", "سیدنی"),
    "nyc": (-300, "New York", "نیویورک"),
    "newyork": (-300, "New York", "نیویورک"),
    "est": (-300, "EST", "شرق آمریکا"),
    "نیویورک": (-300, "New York", "نیویورک"),
    "toronto": (-300, "Toronto", "تورنتو"),
    "تورنتو": (-300, "Toronto", "تورنتو"),
    "chicago": (-360, "Chicago", "شیکاگو"),
    "cst": (-360, "CST", "مرکز آمریکا"),
    "la": (-480, "Los Angeles", "لس‌آنجلس"),
    "pst": (-480, "PST", "غرب آمریکا"),
    "لس‌آنجلس": (-480, "Los Angeles", "لس‌آنجلس"),
    "لسانجلس": (-480, "Los Angeles", "لس‌آنجلس"),
}

_UNIT_QUERY_RE = re.compile(
    r"([+-]?\d[\d,٫]*(?:\.\d+)?)\s*([a-zA-Z\u0600-\u06FF\u200c]+)\s+(?:to|in|به)\s+([a-zA-Z\u0600-\u06FF\u200c]+)$",
    re.IGNORECASE,
)

_TZ_QUERY_RE = re.compile(
    r"(\d{1,2}):(\d{2})\s*([a-zA-Z\u0600-\u06FF\u200c]+)\s+(?:to|in|به)\s+([a-zA-Z\u0600-\u06FF\u200c]+)$",
    re.IGNORECASE,
)


def _format_num(val: float, use_fa: bool) -> str:
    if abs(val - round(val)) < 1e-9:
        s = f"{int(round(val)):,}"
    elif abs(val) >= 100:
        s = f"{val:,.2f}".rstrip("0").rstrip(".")
    else:
        s = f"{val:.4f}".rstrip("0").rstrip(".")
    return en_to_fa_digits(s) if use_fa else s


def _convert_temp(val: float, src: str, dst: str) -> float:
    if src == dst:
        return val
    # Convert to Celsius first
    if src == "f":
        c = (val - 32.0) * (5.0 / 9.0)
    elif src == "k":
        c = val - 273.15
    else:
        c = val
    # Convert from Celsius to target
    if dst == "f":
        return (c * 9.0 / 5.0) + 32.0
    if dst == "k":
        return c + 273.15
    return c


def evaluate_conversion(query: str) -> str | None:
    """Evaluate a unit, currency, or timezone conversion query string."""
    raw = normalize_arabic_chars(query.strip().rstrip("=").strip())
    if not raw:
        return None
    use_fa = any("\u06f0" <= c <= "\u06f9" for c in raw) or any("\u0600" <= c <= "\u06ff" for c in raw)
    norm = fa_to_en_digits(raw)

    # 1. Timezone conversion e.g. "18:30 tehran in london"
    tz_m = _TZ_QUERY_RE.search(norm)
    if tz_m and tz_m.start() == 0:
        hh, mm = int(tz_m.group(1)), int(tz_m.group(2))
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            src_key = tz_m.group(3).lower().replace("\u200c", "")
            dst_key = tz_m.group(4).lower().replace("\u200c", "")
            src_tz = _TZ_OFFSETS_MIN.get(src_key) or _TZ_OFFSETS_MIN.get(tz_m.group(3).lower())
            dst_tz = _TZ_OFFSETS_MIN.get(dst_key) or _TZ_OFFSETS_MIN.get(tz_m.group(4).lower())
            if src_tz and dst_tz:
                total_min = (hh * 60 + mm) - src_tz[0] + dst_tz[0]
                day_shift = total_min // 1440
                rem_min = total_min % 1440
                out_h, out_m = rem_min // 60, rem_min % 60
                time_str = f"{out_h:02d}:{out_m:02d}"
                city_lbl = dst_tz[2] if use_fa else dst_tz[1]
                day_tag = ""
                if day_shift == 1:
                    day_tag = " (روز بعد)" if use_fa else " (+1d)"
                elif day_shift == -1:
                    day_tag = " (روز قبل)" if use_fa else " (-1d)"
                res = f"{time_str} {city_lbl}{day_tag}"
                return en_to_fa_digits(res) if use_fa else res

    # 2. Unit or currency conversion e.g. "150km to mi", "45000000 rial to toman", "1250000 toman to words"
    u_m = _UNIT_QUERY_RE.search(norm)
    if not u_m or u_m.start() != 0:
        return None

    num_str = u_m.group(1).replace(",", "").replace("٫", ".")
    try:
        val = float(num_str)
    except ValueError:
        return None

    src_u = u_m.group(2).lower()
    dst_u = u_m.group(3).lower()

    # Temperature check
    if src_u in _TEMP_ALIASES and dst_u in _TEMP_ALIASES:
        s_code, _, _ = _TEMP_ALIASES[src_u]
        d_code, d_en, d_fa = _TEMP_ALIASES[dst_u]
        out_val = _convert_temp(val, s_code, d_code)
        lbl = d_fa if use_fa else d_en
        return f"{_format_num(out_val, use_fa)} {lbl}"

    # Words conversion e.g. "1250000 toman to words" or "۱۲۵۰۰۰۰ ریال به حروف"
    if dst_u in ("words", "word", "حروف") and src_u in _UNITS:
        spec = _UNITS[src_u]
        words = num_to_persian_words(int(round(val)))
        return f"{words} {spec.label_fa}"

    src_spec = _UNITS.get(src_u)
    dst_spec = _UNITS.get(dst_u)
    if not src_spec or not dst_spec or src_spec.category != dst_spec.category:
        return None

    out_val = val * (src_spec.factor / dst_spec.factor)
    lbl = dst_spec.label_fa if use_fa else dst_spec.label_en
    return f"{_format_num(out_val, use_fa)} {lbl}"


def extract_conversion_expression(text: str) -> str | None:
    """Extract a trailing unit/currency/timezone conversion expression preceding '='."""
    if not text:
        return None
    cleaned = normalize_arabic_chars(text.rstrip())
    norm = fa_to_en_digits(cleaned)

    for pat in (_TZ_QUERY_RE, _UNIT_QUERY_RE):
        m = pat.search(norm)
        if m:
            candidate = cleaned[m.start() :].strip()
            if evaluate_conversion(candidate) is not None:
                return candidate
    return None

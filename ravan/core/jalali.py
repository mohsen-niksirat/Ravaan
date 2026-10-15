"""Persian (Jalali / Solar Hijri) calendar calculations and date formatting.

Zero-dependency, mathematically exact algorithm for astronomical dates
between 1800 and 3000 AD.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Tuple

from ravan.core.normalizer import en_to_fa_digits

JALALI_MONTH_NAMES = [
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
]

PERSIAN_WEEKDAYS = [
    "شنبه",
    "یکشنبه",
    "دوشنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنج‌شنبه",
    "جمعه",
]


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> Tuple[int, int, int]:
    """Convert Gregorian (year, month, day) to Jalali (year, month, day)."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy if gm > 2 else gy - 1
    days = (
        365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        - 80
        + gd
        + g_d_m[gm - 1]
    )
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> Tuple[int, int, int]:
    """Convert Jalali (year, month, day) to Gregorian (year, month, day)."""
    if jy > 979:
        gy = 1600
        jy -= 979
    else:
        gy = 621
    days = (
        365 * jy
        + (jy // 33) * 8
        + ((jy % 33) + 3) // 4
        + 78
        + jd
        + ((jm - 1) * 31 if jm < 7 else ((jm - 7) * 30) + 186)
    )
    gy += 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    sal_a = [
        0,
        31,
        29 if ((gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ]
    gm = 0
    while gm < 13 and gd > sal_a[gm]:
        gd -= sal_a[gm]
        gm += 1
    return gy, gm, gd


@dataclass(frozen=True)
class JalaliDate:
    year: int
    month: int
    day: int

    @classmethod
    def from_gregorian(cls, g_date: date) -> JalaliDate:
        jy, jm, jd = gregorian_to_jalali(g_date.year, g_date.month, g_date.day)
        return cls(year=jy, month=jm, day=jd)

    @classmethod
    def today(cls) -> JalaliDate:
        return cls.from_gregorian(date.today())

    @property
    def month_name(self) -> str:
        if 1 <= self.month <= 12:
            return JALALI_MONTH_NAMES[self.month - 1]
        return ""

    def weekday_name(self, g_date: date | None = None) -> str:
        if g_date is None:
            gy, gm, gd = jalali_to_gregorian(self.year, self.month, self.day)
            g_date = date(gy, gm, gd)
        idx = (g_date.weekday() + 2) % 7
        return PERSIAN_WEEKDAYS[idx]

    def isoformat(self) -> str:
        """Format as standard YYYY/MM/DD with English digits."""
        return f"{self.year:04d}/{self.month:02d}/{self.day:02d}"

    def isoformat_fa(self) -> str:
        """Format as YYYY/MM/DD with Persian digits."""
        return en_to_fa_digits(self.isoformat())

    def format_persian(self, include_weekday: bool = False) -> str:
        """Format as e.g. '۲۳ مهر ۱۴۰۵' or 'پنج‌شنبه ۲۳ مهر ۱۴۰۵'."""
        day_str = en_to_fa_digits(str(self.day))
        year_str = en_to_fa_digits(str(self.year))
        body = f"{day_str} {self.month_name} {year_str}"
        if include_weekday:
            return f"{self.weekday_name()} {body}"
        return body


def current_time_str(persian_digits: bool = False) -> str:
    """Format current time as HH:MM."""
    now = datetime.now()
    s = f"{now.hour:02d}:{now.minute:02d}"
    return en_to_fa_digits(s) if persian_digits else s

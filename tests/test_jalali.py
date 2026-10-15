from datetime import date

from ravan.core.jalali import (
    JalaliDate,
    current_time_str,
    gregorian_to_jalali,
    jalali_to_gregorian,
)


def test_gregorian_to_jalali_known_dates():
    # Nowruz 1403
    assert gregorian_to_jalali(2024, 3, 21) == (1403, 1, 1)
    # End of 1402 (leap year previous)
    assert gregorian_to_jalali(2024, 3, 20) == (1402, 12, 29)
    # 2026-10-15 -> 1405-07-23
    assert gregorian_to_jalali(2026, 10, 15) == (1405, 7, 23)


def test_jalali_to_gregorian_known_dates():
    assert jalali_to_gregorian(1403, 1, 1) == (2024, 3, 20)
    assert jalali_to_gregorian(1405, 7, 23) == (2026, 10, 15)


def test_jalali_date_formatting():
    d = JalaliDate(year=1403, month=1, day=1)
    assert d.isoformat() == "1403/01/01"
    assert d.isoformat_fa() == "۱۴۰۳/۰۱/۰۱"
    assert d.month_name == "فروردین"
    assert d.format_persian(include_weekday=False) == "۱ فروردین ۱۴۰۳"

    d2 = JalaliDate.from_gregorian(date(2024, 3, 21))
    assert d2.year == 1403
    assert d2.month == 1
    assert d2.day == 1


def test_jalali_weekday():
    # 2026-10-15 is Thursday (پنج‌شنبه)
    d = JalaliDate(year=1405, month=7, day=23)
    assert d.weekday_name(date(2026, 10, 15)) == "پنج‌شنبه"


def test_current_time_str():
    t_en = current_time_str(persian_digits=False)
    t_fa = current_time_str(persian_digits=True)
    assert ":" in t_en
    assert ":" in t_fa
    assert len(t_en) == 5

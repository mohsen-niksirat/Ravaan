# وضعیت جاری — Ravaan

*(ثبت‌شده در تاریخ بازرسی: 2026-11-05)*

## Git
- شاخه: `main` — بدون تغییر کاری (`git status` تمیز) و هم‌گام با `origin/main`.
- HEAD: `636ec2ebfb1d10a68b0d08904795d5bcc7b734f2` — «feat: add click language indicator, disable autocorrect by default, restrict suggestion acceptance to digits, and update app icon» (2026-11-02).
- آخرین تگ: `v2.6.0` (نسخه pyproject نیز 2.6.0 — هم‌خوان).
- مخزن: https://github.com/mohsen-niksirat/Ravaan

## وضعیت مشاهده‌شده
- نسخه پایدار منتشرشده 2.6.0 با تمرکز روی بازطراحی Fluent 2 ویندوز ۱۱، فونت همراه Vazirmatn، نشانگر زبان با کلیک ماوس، پذیرش پیشنهاد فقط با ارقام ۱–۵ و غیرفعال‌بودن پیش‌فرض اصلاح خودکار (منبع: CHANGELOG.md).
- فایل‌های untracked: هیچ (`.agents/` و `ravaan-agent-skill.md` عمداً gitignored هستند).
- `AI_CONTEXT/` پیش از این بازرسی وجود نداشت؛ با همین نسخه ساخته شد.

## بررسی‌های اجراشده در این بازرسی
- `python -m ravan --version` → خروجی `2.6.0` ✅ (با `.venv` پروژه)
- `pytest tests/test_calc.py tests/test_transform.py tests/test_jalali.py -q` → **16 passed** در ~۴.۸s ✅
- کل مجموعه تست‌ها (~۸۵ فایل) اجرا نشد؛ CI مخزن (`ci.yml`) مرجع وضعیت کامل است: ruff + pytest کامل روی windows-latest (پایتون 3.10–3.12) و زیرمجموعه ۱۳ فایل core روی ubuntu-latest.

## مسائل/محدودیت‌های شناخته‌شده (از مستندات خود پروژه)
- برنامه فقط روی ویندوز اجرا می‌شود؛ تست‌های دارای مارک `windows` روی OS دیگر به‌طور خودکار skip می‌شوند (`tests/conftest.py`).
- پنجره‌های Run as Administrator از UIA/تزریق خارج‌اند مگر خود Ravaan هم elevated باشد — محدودیت اعلام‌شده، در diagnostics گزارش می‌شود.
- SmartScreen برای نسخه‌های تازه بدون امضا هشدار می‌دهد (`docs/SMARTSCREEN.md`).
- زنجیره caret در برنامه‌های خاص (ترمینال، سلول اکسل، آدرس‌بار مرورگر) best-effort است.

## اولویت‌های فنی بعدی (طبق ROADMAP/BACKLOG مخزن)
- مرجع رسمی: `ROADMAP.md` و `docs/BACKLOG.md` — از v2.0/v1.0 همه فازها Complete ثبت شده‌اند؛ پس از 2.6.0 آیتم Unreleased خالی است، یعنی سیکل بعدی هنوز برنامه‌ریزی عمومی نشده است.
- قاعده جریان کار مخزن (از `ravaan-agent-skill.md`): تک‌شاخه‌ای روی `main`، کامیت‌های کوچک، pytest سبز قبل از هر کامیت، به‌روزرسانی README/ROADMAP همراه هر فاز.

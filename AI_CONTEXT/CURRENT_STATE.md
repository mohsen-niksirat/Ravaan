# وضعیت جاری — Ravaan

*(ثبت‌شده در تاریخ بازرسی: 2026-11-06 — به‌روزرسانی UPDATE برای v2.7.1)*

## Git
- شاخه: `main` — بدون تغییر کاری و هم‌گام با `origin/main`.
- HEAD: `512352673ea963a276c5b023f5fbdd5d25b9f23f` — «docs: refresh AI_CONTEXT for v2.7.1» (2026-11-06)؛ کامیت‌های اخیر: `c775176` chore(release): v2.7.1، `70930b6` fix پیش‌نمایش استایل، `8a57beb` feat v2.7.0.
- آخرین تگ: `v2.7.1` (نسخه pyproject نیز 2.7.1 — هم‌خوان).
- مخزن: https://github.com/mohsen-niksirat/Ravaan

## وضعیت مشاهده‌شده
- نسخه 2.7.1: فیکس متمایزسازی بصری استایل‌ها در پیش‌نمایش زنده تنظیمات (دسکتاپ شبیه‌سازی‌شده + ترکیب شفافیت: macos 0.82، glass 0.55، classic مات) و غیرفعال‌سازی صریح accent آکریلیک هنگام خروج از استایل macos (`_disable_acrylic_blur` در theme.py).
- نسخه 2.7.0: جای‌گذاری قابل‌تنظیم چیپ زبان (پیش‌فرض پایین-راست بالای تری، `lang_indicator_placement`)، ماندگاری sticky جعبه پیشنهاد (timeout 8s با مهاجرت از 4s)، رفع ریشه کندی تایپ (ذخیره تعلیقی مدل یادگیری/کلیپ‌بورد + throttle Tk update + dedup رندر)، استایل پیشنهاد `macos` با acrylic (پیش‌فرض جدید `prediction_ui_style`، مهاجرت از modern)، تنظیمات با پیش‌نمایش زنده + apply-on-change + save بدون بستن + close-with-change.
- معماری `core/platform/ui` و قواعد `ravaan-agent-skill.md` پابرجاست؛ ماژول‌های جدیدی اضافه نشده.
- فایل‌های untracked: `test.txt` (فایل خالی سرگردان در ریشه — متعلق به کاربر، کامیت نشده).
- `AI_CONTEXT/` از v2.6.1 در گیت نگهداری می‌شود و با هر ریلیز refresh می‌گردد.

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

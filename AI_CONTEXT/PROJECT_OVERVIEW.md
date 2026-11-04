# نمای کلی پروژه — Ravaan (روان)

## هدف و شکل محصول
Ravaan (روان) یک **دستیار تایپ دوزبانه فارسی/انگلیسی برای ویندوز** است با اولویت حریم خصوصی و **صفر تلمتری**. برنامه به‌صورت آیکون در system tray اجرا می‌شود، کلیدهای تایپ‌شده را با یک hook سراسری رصد می‌کند و امکانات زیر را ارائه می‌دهد:

- **اصلاح خودکار چیدمان اشتباه** (`sghl` ↔ `سلام`) در مرز واژه
- **تایپوگرافی فارسی و نیم‌فاصله (ZWNJ)** — نرمال‌سازی «ي/ك» به «ی/ک»، گذاشتن خودکار نیم‌فاصله
- **تایپ فونتیک Finglish** (`salam` → `سلام`) با واژه‌نامه ۱۶۲ هزار+ واژه
- **اسنیپت‌های 3.0** — متن، فرم تعاملی، تریگر regex، تصویر، گروه per-app، بسته `.ravaanpack` با تأیید SHA-256
- **ماشین‌حساب درون‌خطی** (`125*8=` → `1000`)، اعداد به حروف فارسی، تاریخ جلالی
- **پیشنهاد زنده واژه** با یادگیری سبک تایپ کاربر (n-gram با decay)
- **دستیار متن هوش مصنوعی** (Ollama محلی / OpenAI)، **دیکتیشن صوتی**، **تاریخچه کلیپ‌بورد**، **Quick Accent**

## پشته فناوری
| لایه | فناوری |
|---|---|
| زبان | Python ≥ 3.10 (فقط ویندوز برای اجرا؛ هسته روی هر OS تست می‌شود) |
| UI | Tkinter (TTK) + پنجره‌های no-activate با `WS_EX_NOACTIVATE` |
| Tray | pystray (فقط win32) |
| Win32 | ctypes + comtypes — `WH_KEYBOARD_LL`، SendInput، UIA، DPAPI |
| ساخت | setuptools + PyInstaller (`ravan.spec`)، Inno Setup، اسکریپت `scripts/build_release.py` |
| تست/لینت | pytest، ruff |

وابستگی‌های runtime: `comtypes`، `Pillow`، `pystray` (هر سه/دو مورد اخیر با مارکر `win32`) — عمداً سبک. (منبع: `pyproject.toml`)

## دستورات تأییدشده
```powershell
pip install -e .[dev]        # نصب توسعه (pyproject.toml)
python -m ravan              # اجرای برنامه (فقط win32) — ravan/__main__.py
python -m ravan --version    # چاپ نسخه (هر OS)
ravan-cli / python -m ravan.cli ...   # ابزارهای تشخیصی CLI — ravan/cli.py
pytest                       # کل مجموعه تست‌ها (testpaths = tests)
ruff check .                 # لینت (خطا E,W,F,I,UP,B؛ خط طولانی نادیده)
```
مثال‌های CLI مستندشده در `ravaan-agent-skill.md`: `python -m ravan.cli convert o,vn` → `خورد`، `predict pro`، `selftest`، `soak`.

## محدودیت‌های اصلی (قراردادهای معماری)
- `ravan/core/` باید **محض و چندسکویی** بماند: هرگز از `platform/` یا `ui/` import نمی‌کند؛ رفتار ویندوزی با پارامتر/callback تزریق می‌شود. (منبع: `ravaan-agent-skill.md` — قواعد طلایی)
- امنیت/حریم خصوصی: بافر کلید فقط در RAM (حداکثر ~32 کاراکتر)، بدون لاگ کلید روی دیسک، رمزگذاری اعتبارنامه‌ها با DPAPI، پروتکل `ravan://` سندباکس‌شده، خروج از کارِ مدیران رمز عبور در تاریخچه کلیپ‌بورد.
- قرارداد safe-mode اصلاح خودکار: فقط وقتی واژهٔ تایپ‌شده در واژه‌نامه نیست، نامزد ۱–۲ فاصلهٔ Damerau-Levenshtein دارد و به‌طور معناداری پرتکرارتر است.
- از ویرایش‌گر/لینتر اجازه دهید نویسهٔ نامرئی ZWNJ (`\u200c`) در واژه‌نامه‌ها و fixtureها حذف نشود؛ در تست‌ها از escape صریح استفاده شود.

## نسخه و انتشار
- نسخه جاری: **2.6.0** (`pyproject.toml`، تگ `v2.6.0`).
- کانال‌های توزیع: Winget (`MohsenNiksirat.Ravaan`)، Scoop، Chocolatey، نصاب Inno Setup per-user، ZIP پرتابل. مانیفست‌ها در `packaging/`.
- UI رشته‌ها دوزبانه EN/FA است (`ravan/data/locales/en.json`، `fa.json`، موتور `ravan/core/i18n.py`).

## نامعلوم‌ها / نکات باز
- کل مجموعه تست‌ها در این بازرسی اجرا نشد؛ فقط زیرمجموعه (۱۶ تست پاس شد). وضعیت CI را از بج GitHub بگیرید.
- جزئیات داخلی چند ماژول (مثلاً `core/dict.py`، `core/learning.py`، `ui/wizard.py`) فقط از docstring و docهای پروژه خوانده شده، نه خط‌به‌خط.
- فایل `ravaan-agent-skill.md` (قواعد طلایی برای عامل‌ها) توسط `.gitignore` نادیده گرفته می‌شود — محلی است و در مخزن نیست.

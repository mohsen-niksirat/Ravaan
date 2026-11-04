# دامنه شناخت (Index Scope)

**تاریخ تحلیل:** 2026-11-05 — **حالت:** INITIALIZE — **HEAD مبنا:** `636ec2ebfb1d10a68b0d08904795d5bcc7b734f2`

## بازرسی‌شده (خوانش واقعی)
- `pyproject.toml`، `README.md`، `ravaan-agent-skill.md`، `CHANGELOG.md` (بخش 2.6.0/2.5.0)، `ROADMAP.md` (بخش ابتدایی)
- `.github/workflows/ci.yml`، `tests/conftest.py`
- `ravan/__main__.py` (کامل)، `ravan/ui/app.py` (۹۰ خط اول)، importها و docstringهای تک‌خطی **تمام ماژول‌های core/platform/ui**
- فهرست کامل فایل‌های tracked (`git ls-files`)، وضعیت ignored و تگ‌ها
- اجرای دودی: `python -m ravan --version` و سه فایل تست سریع (۱۶ تست پاس)

## کنارگذاشته عمداً (طبق قواعد مهارت)
- `build/`، `dist/`، `.venv/`، `ravan.egg-info/`، کش‌ها (`__pycache__`، `.mypy_cache`، `.pytest_cache`، `.ruff_cache`)، `media/` — خروجی/کش/محلی و gitignored
- محتوای داده‌های باینری: `ravan/data/*.bin`، `*.ttf`، `*.ico`، `*.png` (ساختار شناخته شد، محتوا خوانده نشد)
- مانیفست‌های تکراری winget نسخه‌های قدیمی (1.0.0 تا 2.5.0) — فقط الگو بررسی شد
- `dist/`، خروجی‌های `tools/` و اسکریپت‌های build به‌جز نام/نقش آن‌ها
- متن کامل مستندات `docs/*`، `COMPARISON.md`، `SECURITY.md`، `CONTRIBUTING.md`، `DATA.md`، قالب‌های issue — عناوین و نقش‌ها شناخته شد
- ~۸۰ فایل تست و بدنه کامل ماژول‌های core/platform/ui (فقط docstring و وابستگی‌های سطح بالا)

## نامعلوم‌ها و محدودیت‌های پوشش
- صحت خط‌به‌خط منطق موتورها (autofix، predictor، translit، learning) تأیید نشد؛ ادعاهای عملکردی (مثلاً «۱۰۰٪ دقت corpus») از خود مستندات پروژه نقل شده‌اند.
- کل مجموعه تست‌ها و `ruff` اجرا نشدند؛ وضعیت CI را بج/Actions گیت‌هاب تعیین می‌کند.
- رفتار زمان اجرا (hook، overlay، tray) روی سخت‌افزار واقعی آزموده نشد.
- `.github/workflows/release.yml` فقط از فهرست فایل‌ها شناخته شد، نه خوانش کامل.
- هیچ راز/شناسه‌ای در مستندات context ثبت نشده است.

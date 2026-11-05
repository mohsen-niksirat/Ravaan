# دامنه شناخت (Index Scope)

**تاریخ تحلیل اولیه:** 2026-11-05 — **حالت:** INITIALIZE — **HEAD مبنا:** `636ec2ebfb1d10a68b0d08904795d5bcc7b734f2`

---

## به‌روزرسانی UPDATE — 2026-11-06 (مبنا: `636ec2e` → HEAD `5123526`)

**حالت:** UPDATE — دیفا ۴۶ فایل (+۲۴۵۷/−۹۱۵) از آخرین ایندکس کامل تا HEAD.

### بازرسی‌شده در این UPDATE
- `git diff --name-status 636ec2e..HEAD` (کل ۴۶ فایل) + خوانش مستقیم کدهای تغییر یافته در دو session قبلی (دیباگ 2.6.1 و فیچرهای 2.7.0/2.7.1)
- مسیرهای سورس: `ravan/ui/{overlay,theme,settings,settings_builder,settings_save,app,app_actions,app_polling,app_accent,key_handler}.py`، `ravan/platform/{hook,protocol}.py`، `ravan/core/{config,config_migration,calc,normalizer,cliphistory,learning,predictor,autofix,journal,translit,zwnj}.py`، `ravan/data/locales/*.json`، `tests/test_debug_fixes.py`، `tests/test_v2_7_features.py`
- مستندات context به‌روزشده: PROJECT_MAP، MODULES، ARCHITECTURE، PROJECT_OVERVIEW، CURRENT_STATE، همین فایل

### به‌روزرسانی‌شده در مستندات
- استایل macos/آکریلیک، sticky پیشنهادها، جای‌گذاری چیپ زبان، ذخیره تعلیقی، throttle تک، dedup رندر، UX تنظیمات (پیش‌نمایش زنده/apply-on-change/close-with-change)، فیکس‌های 2.6.1 (حسابداری کلید، allowlist wincred، فیلتر کلید خصوصی)
- شمارش تست‌ها: ~۹۰ فایل، ۵۶۸ تست پاس (2026-11-06)

### پوشش‌نداده/محدودیت‌ها
- رفتار acrylic روی سخت‌افزار/تم‌های دیگر و پنجره‌های elevated آزموده نشده
- هش‌های واقعی آرتیفکت‌ها در مانیفست‌های winget/scoop/choco placeholder هستند (الگوی خود مخزن)
- فایل `test.txt` خالی در ریشه (untracked، متعلق به کاربر) وارد مستندات نشده

---

## بازرسی اولیه (INITIALIZE — 2026-11-05)

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

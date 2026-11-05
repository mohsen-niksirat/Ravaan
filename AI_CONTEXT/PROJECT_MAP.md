# نقشه پروژه — Ravaan

## ریشه مخزن
| مسیر | نقش |
|---|---|
| `pyproject.toml` | مانیفست اصلی: نسخه، وابستگی‌ها، اسکریپت‌های ورودی، پیکربندی pytest/ruff |
| `ravan.spec` / `scripts/build_release.py` | ساخت باینری PyInstaller و بسته انتشار |
| `installer/setup.iss` | اسکریپت Inno Setup نصاب ویندوز |
| `packaging/winget|scoop|chocolatey/` | مانیفست‌های مدیر بسته ویندوز (winget تا نسخه 2.6.0) |
| `run_ravan.bat` / `stop_ravan.bat` | اجرا/توقف سریع در ویندوز (محلی، tracked) |
| `requirements.txt` | وابستگی‌ها (موازی با pyproject) |
| `ravaan-agent-skill.md` | قواعد طلایی توسعه برای عامل‌های AI — **gitignored، محلی** |
| `.agents/skills/project-intelligence/` | همین مهارت شناخت پروژه — gitignored، محلی |
| `docs/` | BACKLOG، DEMO، PACKAGES، QA-MATRIX، SECURITY_FAQ، SMARTSCREEN، RELEASE_NOTES_TEMPLATE |
| `tests/` | ~۹۰ فایل تست pytest + `tests/data/` (corpus و golden cases)؛ شامل `test_v2_7_features.py` (جای‌گذاری چیپ، sticky، ذخیره تعلیقی، UX تنظیمات) و `test_debug_fixes.py` (رگرسیون فیکس‌های 2.6.1) |
| `AI_CONTEXT/` | مستندات شناخت پروژه (این پوشه) — از v2.6.1 در گیت نگهداری می‌شود و با هر ریلیز refresh می‌گردد |
| `data/config.example.json` | نمونه پیکربندی کاربر |
| `examples/persian-dates.ravaanpack` | نمونه بسته اسنیپت |

## بسته اصلی `ravan/` — سه لایه با مرز سخت
```
ravan/
  __main__.py   → نقطه ورود `python -m ravan` (بررسی win32، SingleInstance، راه‌اندازی RavanApp)
  cli.py        → نقطه ورود `ravan-cli` (تشخیص زبان، caret، تبدیل چیدمان، selftest، soak، benchmark)
  core/         → منطق محض OS-agnostic (معماری: هرگز از platform/ui import نمی‌کند)
  platform/     → تمام ctypes/Win32 پشت توابع کوچک
  ui/           → Tkinter: پنجره اصلی RavanApp به‌صورت ترکیب Mixinها، tray، overlay، تنظیمات
  data/         → واژه‌نامه‌ها (words_fa/en .txt/.bin)، finglish_dict.json، locales، zwnj_rules.json، فونت Vazirmatn، آیکون
```

## نقاط ورود و جریان‌های رایج
- **شروع برنامه:** `ravan/__main__.py:main` → `platform/winapi.enable_dpi_awareness` → `platform/singleinstance.SingleInstance("Ravaan")` → `ui/app.RavanApp().start()`
- **تغییر رفتار کلیدها/هات‌کی:** `ravan/ui/key_handler.py` (dispatch هات‌کی و تریگرهای درون‌خطی) + `ravan/platform/hook.py` (WH_KEYBOARD_LL)
- **اصلاح خودکار چیدمان:** `ravan/core/autofix.py` + `ravan/core/journal.py` + اعمال در `ravan/ui/app_autofix.py`؛ برگرداندن با `ravan/platform/inject.py`
- **پیشنهاد زنده/یادگیری:** `ravan/core/predictor.py` + `ravan/core/dict.py` + `ravan/core/learning.py`؛ نمایش در `ravan/ui/overlay.py`؛ نظرسنجی در `ravan/ui/app_polling.py`
- **نیم‌فاصله/نرمال‌سازی:** `ravan/core/zwnj.py`، `ravan/core/normalizer.py`، `ravan/core/grammar.py`
- **تبدیل چیدمان F12:** `ravan/core/layout.py` (نقشه ISIRI 9147) + `ravan/ui/app_actions.py`
- **اسنیپت‌ها:** هسته در `ravan/core/snippet*.py` (snippet، forms، groups، macros، regex) + `ravan/core/package.py` (.ravaanpack) + UI در `ravan/ui/snippet_editor*.py`، `form_dialog.py`
- **همگام‌سازی ابری:** `ravan/core/sync.py` (GitHub Gist) + `ravan/core/webdav.py`؛ UI در `ravan/ui/settings_sync*.py`؛ رمزنگاری اعتبارنامه در `ravan/core/crypto.py` (DPAPI)
- **به‌روزرسانی:** `ravan/core/updater.py` + `ravan/ui/update_dialog.py`؛ جریان انتشار در `.github/workflows/release.yml`
- **تنظیمات:** `ravan/ui/settings.py` + builder/save/reset در `settings_builder.py`، `settings_save.py`، `settings_reset.py`؛ ذخیره با `ravan/core/config.py`
- **تشخیص خودتشخیصی:** `ravan/platform/selftest.py` + `ravan/ui/diagnostics.py` + `ravan/cli.py`
- **متریال/تم پاپ‌آپ‌ها:** `ravan/ui/theme.py` — پالت‌های `get_macos_palette`، acrylic helpers (`_enable_acrylic_blur` / `_disable_acrylic_blur`)، حاشیه DWM و `apply_popup_window_attributes(..., acrylic=, border_color=)`
- **پیش‌نمایش زنده تنظیمات:** `ravan/ui/settings.py:_render_style_preview` (دسکتاپ شبیه‌سازی‌شده + ترکیب شفافیت) + `on_prediction_style_changed` / `on_lang_placement_changed` (apply-on-change) + `_save_then_close` (close-with-change) + `flash_saved`

## داده و ماندگاری
- کد محلی برنامه: `ravan/data/` (tracked) — واژه‌نامه، فونت، لوکال، آیکون.
- داده کاربر: `%APPDATA%\Ravaan\` — `config.json`، `user_words.txt`، `clipboard_history.json` (منبع: `core/config.py:config_dir`، `ui/app.py`).
- جریان‌های تغییر رایج: افزودن قابلیت → معمولاً یک ماژول core + یک Mixin در ui + تست جدید + به‌روزرسانی CHANGELOG/ROADMAP (الگوی کامیت‌های قبلی).

## مشخصاً خارج از نقشه
`build/`، `dist/`، `.venv/`، `.mypy_cache|pytest_cache|ruff_cache/`، `__pycache__/`، `ravan.egg-info/`، `media/` — خروجی ساخت/کش/محلی و gitignored.

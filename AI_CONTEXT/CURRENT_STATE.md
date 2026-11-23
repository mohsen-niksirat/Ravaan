# وضعیت جاری — Ravaan

*(به‌روزرسانی نهایی: نسخه v3.1.0 — 2026-11-23)*

## Git
- شاخه: `main`
- مخزن: https://github.com/mohsen-niksirat/Ravaan

## خلاصه تغییرات نسخه 3.0.0 (فازهای ۱ تا ۵)
- **فاز ۱ (Fluent 2 UI & Modularization):** پیاده‌سازی کیت ویجت‌های برداری 2x-AA (`ravan/ui/widgets/` شامل `FluentToggleSwitch`, `FluentPillButton`, `FluentSegmentedControl`, `FluentEntry`, `FluentBadge`, `FluentCard`, `FluentSectionBanner` و ۲۲ آیکون برداری)، ماژولارسازی کامل `theme*.py` و `settings*.py` و lookup نقطه‌ای `i18n.py`.
- **فاز ۲ (Voice 2.0):** ضبط صوت 16kHz WinMM تماماً در رم (`ravan/platform/audio.py`)، مدیریت مدل Whisper آفلاین با SHA-256 (`ravan/core/model_manager.py`)، موتور هیبرید (`ravan/core/voice.py`) و کپسول موج صوتی زنده غیرفعال‌نکننده (`ravan/ui/waveform_pill.py`).
- **فاز ۳ (AI 2.0):** استریم واقعی NDJSON/SSE در `ravan/core/ai.py`، ۷ پیش‌تنظیم دوزبانه، پالت فرمان Spotlight با مقایسه قبل/بعد (`ravan/ui/ai_popup.py`, `ravan/ui/ai_diff.py`)، ارتقای `SelectionToolbarWindow` و تب جدید «هوش مصنوعی و صدا» در تنظیمات (`ravan/ui/settings_ai_voice.py`, `ravan/ui/settings_voice_panel.py`).
- **فاز ۴ (Ravaan Hub):** مخزن آنلاین بسته‌های `.ravaanpack` با کش محلی، ۴ دسته‌بندی آماده، تاییدیه SHA-256، مرورگر کارتی جستجوپذیر و مودال پیش‌نمایش (`ravan/core/hub.py`, `ravan/ui/hub_browser.py`, `ravan/ui/hub_preview_modal.py`).
- **فاز ۵ (Hardening & v3.0.0 Release):** تست چندسکویی و قید ۳ لایه AST (`tests/test_v3_core_parity.py`) در CI ابونتو و ویندوز، به‌روزرسانی بسته‌بندها (`Winget`, `Scoop`, `Chocolatey`, `Inno Setup`, `pyproject.toml`) و مستندات رسمی.

## معماری و محدودیت‌های شناخته‌شده
- رعایت دقیق جداسازی ۳ لایه (`core/` هرگز به `platform/` یا `ui/` وابسته نیست) که با تست AST خودکار بررسی می‌شود.
- برنامه برای اجرا روی ویندوز طراحی شده و تست‌های نیازمند Win32 به‌طور خودکار در لینوکس skip می‌شوند (`tests/conftest.py`).
- کلیدهای API همگام‌سازی، AI و صوت با Windows DPAPI / Credential Manager رمزنگاری می‌شوند و هیچ تلمتری یا ثبت کلید در دیسک وجود ندارد.

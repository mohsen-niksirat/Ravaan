# ماژول‌ها — Ravaan

مسئولیت‌ها از docstring فایل‌ها و خوانش گزینشی استخراج شده‌اند. `core/` هرگز از `platform/` یا `ui/` import نمی‌کند.

## core/ — منطق محض
| ماژول | مسئولیت |
|---|---|
| `config.py` (۵۳۷ل) | بارگذاری/ذخیره `%APPDATA%\Ravaan\config.json`، مقدارهای پیش‌فرض (مثلاً `autocorrect_enabled=False` از 2.6.0) |
| `config_types.py` / `config_migration.py` | دیتاکلاس‌های پیکربندی / مهاجرت اسکیما |
| `layout.py` | نقشه چیدمان فارسی↔انگلیسی (استاندارد ISIRI 9147)، `LayoutMapper` |
| `journal.py` | `KeystrokeJournal` — ردیابی کاراکترهای تایپ‌شده اخیر برای تبدیل چیدمان |
| `autofix.py` | موتور اصلاح خودکار چیدمان اشتباه (سبک Punto/Caramba) — قرارداد safe-mode |
| `dict.py` (۷۹۴ل) | فهرست‌های فرکانس واژه، تطبیق فازی، بارگذاری واژه‌نامه (۱۶۲k+) |
| `predictor.py` | `DictPredictor` — جستجوی واژه‌نامه و رتبه‌بندی نامزدهای پیشنهاد |
| `learning.py` | یادگیری سبک تایپ کاربر v2 — n-gram با stupid-backoff، decay، وزن per-app؛ **ذخیره تعلیقی** (`save(lazy=True)` حداقل هر ۳۰ ثانیه + `flush()`) تا هر واژه دیسک ننویسد |
| `user_dict.py` | واژه‌نامه سفارشی کاربر (`user_words.txt`) |
| `translit.py` | موتور آوانگاری Finglish→فارسی (۹.۷k+ ورودی، پیشوند/پسوند پویا) |
| `zwnj.py` | موتور نیم‌فاصله — پیشوندهای «می‌/نمی‌» و پسوندهای «‌ها/‌تر/‌ترین/‌مند» |
| `normalizer.py` | نرمال‌ساز فارسی — «ي/ك→ی/ک»، علائم نگارشی، ارقام متنی |
| `grammar.py` | کمک‌گرامر فارسی — جداسازی حرف اضافه، تنوین، تایپوگرافی |
| `snippet.py` | موتور بسط متن — قالب پویا، ماکرو تاریخ/زمان، محاسبه، جای‌گذاری مکان‌نما |
| `snippet_forms.py` / `snippet_groups.py` / `snippet_macros.py` / `snippet_regex.py` | فرم‌های تعاملی، گروه per-app + اسنیپت تصویری، ماکروهای داخلی، تریگر regex با گارد ReDoS |
| `package.py` | بسته `.ravaanpack` — بسته‌بندی/بررسی صحت SHA-256 |
| `calc.py` | ارزیاب امن عبارت ریاضی بدون وابستگی (`125*8=`) |
| `num2words.py` | عدد به حروف فارسی + تریگرهای ارز (تومان/ریال) |
| `jalali.py` | تقویم جلالی و قالب‌بندی تاریخ شمسی |
| `text_stats.py` | آمار سریع متن (واژه/زمان مطالعه/نسبت زبان) |
| `transform.py` | تبدیل‌های متنی (چرخش بزرگ/کوچکی حروف، نرمال‌سازی) |
| `accent.py` | Quick Accent — تنوع حروف فارسی/عربی و ارقام |
| `cliphistory.py` | حلقه تاریخچه کلیپ‌بورد با پالایش امنیتی (مدیران رمز، آنتروپی، انقضا)؛ ذخیره تعلیقی (`save(lazy=True)` هر ~۱۰ ثانیه + `flush()`) |
| `crypto.py` | رمزنگاری DPAPI برای اعتبارنامه‌ها |
| `sync.py` / `webdav.py` | همگام‌سازی ابری GitHub Gist / WebDAV |
| `updater.py` | بررسی نسخه جدید از GitHub Releases + نصب درون‌برنامه‌ای |
| `ai.py` | دستیار متن AI — Ollama محلی یا endpoint سازگار OpenAI |
| `voice.py` | دیکتیشن صوتی آفلاین — بافر حافظه، بدون نشت به دیسک |
| `backup_zip.py` | خروجی/ورودی ZIP از همه داده‌های کاربر |
| `data_manifest.py` | مانیفست لایه داده — ثبت فایل‌ها/اسکیما/سیاست حریم خصوصی |
| `benchmark.py` / `soak.py` | بنچمارک موتور پیشنهاد (hit-rate، p95) / تست فرسایش حافظه و تأخیر |
| `events.py` | نوع‌های رویداد مشترک بین نخ‌ها (`Candidate` و …) |
| `i18n.py` | بومی‌سازی دوزبانه EN/FA (کاتالوگ: `ravan/data/locales/*.json`) |
| `macro.py` | ضبط/پخش ماکروی کلید |

## platform/ — پوشش Win32 (فقط ویندوز)
| ماژول | مسئولیت |
|---|---|
| `winapi.py` | بایندهای ctypes مشترک، `enable_dpi_awareness` |
| `hook.py` | `KeyboardHook` — هوک سراسری `WH_KEYBOARD_LL`، `set_popup_visible` |
| `inject.py` | تزریق متن با SendInput یونیکد — `replace_last_n_with` |
| `caret.py` | موقعیت caret: زنجیره UIA → GetGUIThreadInfo → ماوس |
| `focus.py` / `lang.py` | ردیابی پنجره/پروسه پیش‌زمینه / تشخیص زبان کیبورد |
| `keys.py` | ترجمه یونیکد VK و تطبیق هات‌کی |
| `clipboard.py` | خواندن/نوشتن امن Win32 clipboard (نخ‌ایمن) |
| `protocol.py` | ثبت/تجزیه دیپ‌لینک `ravan://` با whitelist |
| `singleinstance.py` | `SingleInstance` با named mutex |
| `startup.py` / `sound.py` / `selftest.py` | اجرای خودکار (HKCU Run) / بازخورد صوتی / تشخیص خودکار PASS-FAIL |

## ui/ — رابط Tkinter
| ماژول | مسئولیت |
|---|---|
| `app.py` | `RavanApp` — حلقه اصلی؛ ترکیب Mixinهای زیر |
| `key_handler.py` (۴۳۲ل) | dispatch هات‌کی و تریگرهای درون‌خطی روی رویدادهای هوک |
| `app_autofix.py` / `app_actions.py` | اعمال/برگرداندن اصلاح‌ها؛ تبدیل‌های متنی و undo |
| `app_polling.py` (به‌روزشده) | نظرسنجی فوکوس/زبان/کلیپ‌بورد، چیپ زبان (با `lang_indicator_placement`)، نمایش پیشنهاد؛ **sticky popup** (شکاف نامزد وسط کلمه باکس را نمی‌بندد) + `_poll_learning_flush` (flush دوره‌ای ذخیره‌های تعلیقی) |
| `overlay.py` (به‌روزشده) | پنجره شفاف no-activate: چیپ زبان (جای‌گذاری گوشه‌ای `corner_position` + حالت caret) + پاپ‌آپ پیشنهاد؛ **استایل macos** (آکریلیک + رنگ‌کلید، `_row_bg` غیر-کلید برای سطوح تعاملی)، throttle تک (update کامل ~۴۰Hz)، dedup رندر (`_last_render_key`) |
| `app_tray.py` / `tray.py` | ساخت آیکون tray، منوی راست‌کلیک با toggleهای سریع |
| `settings*.py` / `settings.py` | پنجره تنظیمات دوزبانه مدرن با هدر برند، جستجوی پیشرفته، اکشن‌بار: builder، ذخیره، ریست، تب Auto-Fix، همگام‌سازی؛ **پیش‌نمایش زنده استایل** (`_render_style_preview` روی دسکتاپ شبیه‌سازی‌شده)، **apply-on-change** (استایل/جای‌گذاری)، **Save بدون بستن** (`flash_saved`)، **close-with-change** (`_save_then_close`)؛ کمبوی ۱۰ استایل `prediction_ui_style` و `lang_indicator_placement` |
| `snippet_editor*.py` / `form_dialog.py` / `package*_dialog.py` | ویرایشگر اسنیپت، فرم جای‌نگهدار، دیالوگ‌های .ravaanpack |
| `wizard.py` (۶۱۷ل) / `quick_tips.py` | جادوگر اجرای اول / راهنمای میانبرها |
| `theme.py` | پالت‌ها (dark/light/high-contrast + macos/fluent/material/ios/minimal/neon)، توکن‌های تایپوگرافی Vazirmatn/Segoe UI، گوشه‌های گرد DWM، توکن‌های طراحی `PredictionStyleTokens` و هلپر `get_prediction_style()`، **متریال acrylic** (`_enable_acrylic_blur` / `_disable_acrylic_blur` با SetWindowCompositionAttribute) و حاشیه مویی DWM در `apply_popup_window_attributes` |
| `crash_dialog.py` / `log_setup.py` | دیالوگ کرش دوزبانه / لاگ چرخشی محدود |
| `ai_popup.py` / `app_ai.py` / `stats_popup.py` / `accent_bar.py` | پاپ‌آپ دستیار AI / آمار سریع / نوار انتخاب حرف |
| `diagnostics.py` / `window_picker.py` / `update_dialog.py` / `hint_manager.py` | پنجره تشخیص / انتخاب پنجره برای استثنا / به‌روزرسانی / راهنمای قابلیت‌ها |

## نمادهای حیاتی (رفرنس سریع)
- `ravan/__main__.py:main` — نقطه ورود GUI؛ `ravan/cli.py:main` — نقطه ورود CLI.
- `ravan/ui/app.py:RavanApp` — کلاس ریشه برنامه (۹۰ خط اول خوانده شد؛ constructor موتورها را می‌سازد).
- `ravan/platform/hook.py:KeyboardHook`، `ravan/platform/inject.py:replace_last_n_with` — حلقه ورودی/خروجی متن.
- `ravan/core/layout.py:LayoutMapper`، `ravan/core/predictor.py:DictPredictor`، `ravan/core/snippet.py:SnippetEngine`، `ravan/core/journal.py:KeystrokeJournal` — موتورهای اصلی که `RavanApp` می‌سازد.
- `ravan/core/config.py:load_config` / `config_dir` — منبع یگانه پیکربندی و مسیر داده کاربر.

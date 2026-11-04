# معماری — Ravaan

## اجزا و مرزها
سه لایه با قانون وابستگی یک‌طرفه (منبع قواعد: `ravaan-agent-skill.md`، تأییدشده با importهای `ui/app.py`):

```
ui/  ──▶  core/          (منطق محض، چندسکویی، قابل تست روی هر OS)
ui/  ──▶  platform/      (پوشش ctypes/Win32 پشت توابع کوچک)
platform/ ──▶ (فقط Win32 API)
core/ ──▶ هیچ‌کدام از ui/platform  ← قانون مطلق
```

- **core/** (~۴۰ ماژول): موتورهای خالص — config، layout، dict/predictor، learning، translit، zwnj/normalizer/grammar، snippet*، calc، jalali، num2words، crypto (DPAPI)، sync/webdav، updater، cliphistory، voice، package، benchmark، soak.
- **platform/** (~۱۴ ماژول): hook (`WH_KEYBOARD_LL`)، inject (SendInput یونیکد)، caret (زنجیره UIA → GetGUIThreadInfo → نشانگر ماوس)، clipboard، focus، lang، keys، protocol (`ravan://`)، singleinstance (نام‌گذاری mutex)، startup (HKCU Run)، sound، selftest، winapi (بایندهای ctypes مشترک).
- **ui/** (~۴۰ ماژول): `RavanApp` در `ui/app.py` کلاس مرکزی است که با **ترکیب ۸ Mixin** ساخته می‌شود: `AppAccentMixin`, `AppActionsMixin`, `AppAIMixin`, `AppAutofixMixin`, `AppDialogsMixin`, `AppPollingMixin`, `AppVoiceMixin`, `KeyHandlerMixin`. بقیه: overlay (چیپ زبان + پاپ‌آپ پیشنهاد، `WS_EX_NOACTIVATE`)، tray (pystray)، settings (چند ماژول)، snippet_editor، wizard، theme (پالت Fluent 2 و فونت Vazirmatn)، toast/tooltip و پنجره‌های کمکی.

## جریان کنترل اصلی (تایپ کاربر)
1. `platform/hook.KeyboardHook` هر رویداد کلید را در نخ خودش می‌گیرد (WH_KEYBOARD_LL).
2. رویداد از طریق صف داخلی به `RavanApp` می‌رسد؛ `ui/key_handler.py` dispatch می‌کند: هات‌کی‌ها (F12، Shift+Space، Alt+V، Ctrl+Shift+Z، …) و تریگرهای درون‌خطی.
3. `core/journal.KeystrokeJournal` کاراکترهای اخیر را نگه می‌دارد (RAM، مرز واژه‌ای).
4. موتورهای core تصمیم می‌گیرند: `core/autofix.py` (چیدمان اشتباه)، `core/translit.py` (فینگلیش)، `core/snippet.py` (بسط)، `core/calc.py`/`num2words.py` (محاسبه/عدد)، `core/zwnj.py`/`normalizer.py` (تایپوگرافی)، `core/predictor.py` (پیشنهاد).
5. اعمال نتیجه با `platform/inject.py` (جایگزینی n کاراکتر آخر با SendInput)؛ بازخورد بصری در `ui/overlay.py` (بدون دزدیدن فوکوس)؛ صدا در `platform/sound.py`.
6. `ui/app_polling.py` وضعیت فوکوس/زبان/کلیپ‌بورد را دوره‌ای نظرسنجی می‌کند و چیپ زبان را هنگام کلیک نشان می‌دهد (ویژگی 2.6.0).
7. `Ctrl+Shift+Z` / Backspace بازگردانی از پشته undo (≈۵۰ مرحله، در `ui/app_actions.py` + `app_autofix.py`).

## نخ‌ها و هم‌زمانی
- نخ hook، نخ UI (Tkinter mainloop)، نخ tray (pystray) و نخ‌های نظرسنجی/پس‌زمینه. ارتباط از طریق `queue.Queue` (`RavanApp._ui_queue`) و `core/events.py` (نوع‌های رویداد مشترک مثل `Candidate`).
- محافظ تک‌نمونه با named mutex (`platform/singleinstance.py`) قبل از ساخت UI.

## سیستم‌های بیرونی (اختیاری، خاموش به‌طور پیش‌فرض)
- **GitHub Gist** و **WebDAV** برای همگام‌سازی واژه‌ها/اسنیپت‌ها (`core/sync.py`, `core/webdav.py`) — اعتبارنامه با DPAPI رمز می‌شود.
- **GitHub Releases** برای بررسی/نصب به‌روزرسانی (`core/updater.py`) — تنها اتصال شبکه دیگر.
- **Ollama/OpenAI-compatible** برای دستیار متن AI (`core/ai.py`)، فقط با درخواست کاربر.
- ادعای «صفر تلمتری» با این ساختار سازگار است: هیچ کانال اطلاع‌رسانی خودکار دیگری در core وجود ندارد. (راستی‌آزمایی کامل شبکه انجام نشد — نکته در INDEX_SCOPE)

## ماندگاری داده
| داده | مسیر | رمز |
|---|---|---|
| پیکربندی | `%APPDATA%\Ravaan\config.json` (`core/config.py`) | متن + مهاجرت اسکیما (`config_migration.py`) |
| واژه‌نامه کاربر | `%APPDATA%\Ravaan\user_words.txt` | متن |
| تاریخچه کلیپ‌بورد | `%APPDATA%\Ravaan\clipboard_history.json` | فیلتر رمز عبور، انقضای ۷ روزه (`core/cliphistory.py`) |
| اعتبارنامه‌های sync/AI | درون config | DPAPI (`core/crypto.py`) |
| مدل یادگیری | مسیر config | n-gram با decay (`core/learning.py`) |
| بسته‌های اسنیپت | فایل `.ravaanpack` | SHA-256 (`core/package.py`) |

## تصمیم‌های کلیدی طراحی (مشاهده‌شده)
1. **هسته محض / پوسته ویندوزی** — تست‌پذیری چندسکویی هسته؛ CI روی ubuntu زیرمجموعه core را اجرا می‌کند.
2. **Mixin به‌جای ارث‌بری تک‌کلاسه** — جداسازی وظایف RavanApp در فایل‌های ~۱۰۰–۴۳۰ خطی؛ قانون «بیش از ~۴۰۰ خط را بشکن» در قواعد طلایی.
3. **همه تعامل ویندوز پشت `platform/`** — هیچ ctypes پراکنده در core/ui نیست؛ mock پلتفرم در `tests/test_platform_mock.py`.
4. **زنجیره fallback برای caret** — UIA → GetGUIThreadInfo → ماوس؛ افت بی‌صدا با لاگ محدود.
5. **حریم خصوصی به‌عنوان قید معماری** — بافر RAM، نبود لاگ کلید، DPAPI، سندباکس `ravan://`، خروج پیش‌فرض از مدیران رمز.
6. **UI بدون فوکوس‌گیری** — overlayها با `WS_EX_NOACTIVATE`/`SW_SHOWNOACTIVATE` تا تایپ کاربر قطع نشود.

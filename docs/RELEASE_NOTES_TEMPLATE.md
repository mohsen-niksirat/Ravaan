# Ravaan (روان) v{{VERSION}}

---

## English

### Highlights
- Official **v2.0.0** major stable release of Ravaan (روان) with full competitive dominance over Punto, Caramba, Espanso, and PowerToys!
- **Automatic Wrong-Layout Correction**: Automatic detection and conversion of mistyped words (e.g. `o,vn` → `خورد`) with zero manual hotkeys.
- **Active Layout Switcher**: Seamlessly switches active Windows layout upon detection via `WM_INPUTLANGCHANGEREQUEST`.
- **Confidence & Undo Toast**: Floating toast with instant single-tap undo via `Backspace` or `Ctrl+Z`, and auto-blacklisting of false positives.
- **Transliteration Mode (Finglish → Persian)**: Real-time Finglish typing (`salam` → `سلام`) with a 9,700+ mapping engine.
- **Live Suggestions 2.0**: Fast Right Arrow suggestion acceptance and multi-word sentence continuations with `Shift+Enter`.
- **Snippets 3.0**: Dynamic form dialogs (`{{var:default}}`), regex expansion triggers with ReDoS safety, image snippets, and per-app filtering.
- **Quick Accent**: 300ms key-hold accent bar for diacritics, Arabic/Persian variants, and instant ZWNJ selection.
- **AI Text Assistant**: `Ctrl+Shift+G` floating popup for rewriting, grammar/ZWNJ correction, translation, and summarization via Ollama or OpenAI endpoints.
- **Voice Dictation**: Push-to-Talk `Ctrl+Alt+V` speech-to-text with local Whisper/Vosk and zero disk audio leaks.
- Windows DPAPI credential encryption, zero-telemetry policy, and local-only processing.

### Verification & Checksums (SHA256)
{{CHECKSUM_TABLE}}

### Known Limitations
- **Elevated Applications**: Windows User Interface Privilege Isolation (UIPI) strictly forbids standard user applications from sending synthesized keystrokes to elevated (Run as Administrator) processes. If you focus an elevated command prompt, PowerShell, or Task Manager, Ravaan will notify you once and safely pause injection rather than crashing.
- **Caret Tracking (Best-Effort)**: Caret coordinates are queried via Windows UI Automation (UIA) Text Pattern and native `GetGUIThreadInfo`. Applications with custom canvas rendering or non-standard caret implementations (e.g. legacy command prompt, specialized game text boxes) will fall back to mouse pointer position or centered monitor overlay.

### Upgrade Notes
- **Config Migration from 0.x**: Existing configurations (`config.json`), custom words (`user_words.txt`), snippets (`snippets.json`), and learned vocabulary are automatically migrated to current schema version losslessly upon first run.
- **Data Preservation**: Uninstalling previous versions leaves your `%APPDATA%\Ravaan` data directory intact.

### Installation Options
- **Recommended (Installer)**: Download `Ravaan-Setup-{{VERSION}}.exe`. Installs per-user without requiring Administrator UAC privileges, with optional desktop shortcut, auto-startup, and `ravan://` URL protocol handler.
- **Portable**: Download and extract `Ravaan-{{VERSION}}-portable.zip` anywhere and launch `Ravaan.exe` directly.

---

## فارسی (Persian)

### ویژگی‌های برجسته
- انتشار رسمی و پایدار نسخه بزرگ **v2.0.0** دستیار هوشمند تایپ روان با تسلط کامل رقابتی بر پونتو، کارامبا، اسپنکو و پاور‌تویز!
- **اصلاح خودکار هوشمند چیدمان اشتباه**: تشخیص و تصحیح فوری کلمات با زبان اشتباه (مانند `o,vn` → `خورد`) بدون نیاز به کلید میانبر.
- **تغییر خودکار چیدمان کیبورد ویندوز**: تغییر زبان فعال سیستم بلافاصله پس از اصلاح از طریق پیام `WM_INPUTLANGCHANGEREQUEST`.
- **اعلان Toast و بازگردانی سریع**: اعلان شناور با امکان بازگردانی تک‌کلیدی با Backspace یا Ctrl+Z و بلک‌لیست خودکار کلمات دارای خطای مکرر.
- **حالت فینگلیش به فارسی (Transliteration)**: تایپ زنده فینگلیش به فارسی (`salam` → `سلام`) با موتور نگاشت ۹۷۰۰ کلمه‌ای.
- **پیشنهادهای زنده نسخه ۲.۰**: پذیرش فوری با کلید جهت‌نمای راست (`→`) و ادامهٔ جملات چندکلمه‌ای با `Shift+Enter`.
- **اسنیپت‌های پیشرفته نسخه ۳.۰**: فرم‌های تعاملی (`{{var:default}}`)، عبارات باقاعده (Regex) با ایمنی ضد ReDoS، اسنیپت‌های تصویری و فیلتر برنامه.
- **انتخابگر سریع نشانه‌ها (Quick Accent)**: بار افقی انتخاب اعراب، همزه، تنوین، ه/ة/ھ، ی/ي/ئ، ک/ك و نیم‌فاصله با نگه‌داشتن کلید برای ۳۰۰ میلی‌ثانیه.
- **دستیار متنی هوش مصنوعی**: فراخوانی با `Ctrl+Shift+G` برای بازنویسی، تصحیح گرامر و نیم‌فاصله، ترجمه و خلاصه‌سازی با Ollama و OpenAI بدون لاگ متنی دیسک.
- **تایپ صوتی فشاری (Push-to-Talk)**: تبدیل گفتار به متن فارسی (`Ctrl+Alt+V`) با موتور Whisper محلی بدون نشت صدا به دیسک.
- امنیت پیشرفته: رمزنگاری اعتبارات با Windows DPAPI، سیاست عدم ارسال تله‌متری و پردازش ۱۰۰٪ محلی داده‌ها.

### اعتبارسنجی و جدول چک‌سام‌ها (SHA256)
{{CHECKSUM_TABLE}}

### محدودیت‌های شناخته‌شده
- **برنامه‌های دارای دسترسی مدیر (Elevated / Run as Administrator)**: سازوکار امنیتی ویندوز (UIPI) اجازه تزریق کلید از یک برنامه کاربر عادی به برنامه‌های دارای دسترسی مدیریتی را نمی‌دهد. در صورت فوکوس روی پنجره‌های مدیریتی (مانند CMD یا PowerShell ادمین)، روان پیام هشدار تک‌مرحله‌ای نمایش داده و به صورت ایمن متوقف می‌شود.
- **تشخیص مکان نشانگر متن (Caret Tracking)**: مختصات مکان‌نما بر پایه رابط UIA و Win32 به شکل Best-Effort استخراج می‌شود. در نرم‌افزارهایی که مکان‌نمای غیراستاندارد دارند، پنجره راهنما در مجاورت نشانگر ماوس یا مرکز مانیتور ظاهر می‌شود.

### نکات ارتقا و سازگاری
- **مهاجرت خودکار از نسخه 0.x**: کلیه تنظیمات، واژه‌نامه‌های شخصی، اسنیپت‌ها و داده‌های یادگیری قبلی بدون کوچک‌ترین اتلاف داده به ساختار جدید ارتقا می‌یابند.
- **حفظ داده‌ها هنگام حذف یا نصب مجدد**: پوشه داده‌های کاربر در `%APPDATA%\Ravan` همواره دست‌نخورده باقی می‌ماند.

### راهنمای نصب
- **پیشنهادی (فایل نصبی)**: دریافت `Ravaan-Setup-{{VERSION}}.exe`. نصب بدون نیاز به دسترسی Administrator با امکان فعال‌سازی شروع خودکار و ثبت پروتکل `ravan://`.
- **نسخه پرتابل**: دریافت و استخراج `Ravaan-{{VERSION}}-portable.zip` و اجرای مستقیم فایل `Ravaan.exe`.

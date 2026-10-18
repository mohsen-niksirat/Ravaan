# Ravaan (روان) v{{VERSION}}

---

## English

### Highlights
- Official **v1.0.0** stable public release of Ravaan (روان) for Windows typists!
- Complete release engineering pipeline with automated multi-artifact packaging (`Setup.exe` + portable `.zip`).
- In-app auto-updater hardened with pre-release channel awareness and 1-click update.
- Windows DPAPI credential encryption, zero-telemetry policy, and local-only processing.
- Real-World Windows QA Matrix: multi-monitor mixed-DPI popup clamping, elevated window degradation, and robust caret tracking fallbacks.
- UX Final Polish: unified theme palette tokens (dark/light/high-contrast), prediction confidence meter, first-run onboarding wizard, and upgraded system tray toggles.
- Data & Migration Completeness: central data manifest, learning profile sync, and lossless migration test harness from all prior versions.
- Bilingual UI (English & Persian) with complete RTL layout rendering and live language switching.
- Prediction Engine v2 with Stupid Backoff n-grams, exponential frequency decay, and app-context awareness.
- Cloud Sync 2.0 with WebDAV, GitHub Gist, 3-way dictionary merge, and schema versioning.
- Math v2 expression evaluator, Macro recorder, Power Mode, and CLI user data backup/restore.

### Verification & Checksums (SHA256)
{{CHECKSUM_TABLE}}

### Known Limitations
- **Elevated Applications**: Windows User Interface Privilege Isolation (UIPI) strictly forbids standard user applications from sending synthesized keystrokes to elevated (Run as Administrator) processes. If you focus an elevated command prompt, PowerShell, or Task Manager, Ravaan will notify you once and safely pause injection rather than crashing.
- **Caret Tracking (Best-Effort)**: Caret coordinates are queried via Windows UI Automation (UIA) Text Pattern and native `GetGUIThreadInfo`. Applications with custom canvas rendering or non-standard caret implementations (e.g. legacy command prompt, specialized game text boxes) will fall back to mouse pointer position or centered monitor overlay.

### Upgrade Notes
- **Config Migration from 0.x**: Existing configurations (`config.json`), custom words (`user_words.txt`), snippets (`snippets.json`), and learned vocabulary are automatically migrated to current schema version losslessly upon first run.
- **Data Preservation**: Uninstalling previous versions leaves your `%APPDATA%\Ravan` data directory intact.

### Installation Options
- **Recommended (Installer)**: Download `Ravaan-Setup-{{VERSION}}.exe`. Installs per-user without requiring Administrator UAC privileges, with optional desktop shortcut, auto-startup, and `ravan://` URL protocol handler.
- **Portable**: Download and extract `Ravaan-{{VERSION}}-portable.zip` anywhere and launch `Ravaan.exe` directly.

---

## فارسی (Persian)

### ویژگی‌های برجسته
- انتشار رسمی و پایدار نسخه **v1.0.0** دستیار هوشمند تایپ روان برای ویندوز!
- خط تولید خودکار پکیج‌های نصبی و پرتابل (`Setup.exe` و فایل فشرده `.zip`).
- سامانه بروزرسانی درون‌برنامه‌ای هوشمند و امن با امکان ارتقای ۱کلیکی.
- امنیت پیشرفته: رمزنگاری اعتبارات با Windows DPAPI، سیاست عدم ارسال تله‌متری و پردازش ۱۰۰٪ محلی داده‌ها.
- سازگاری کامل با ویندوز: مهار خطاهای چندمانیتوره و DPI ترکیبی، مدیریت برنامه‌های ادمین و سیستم بازگشتی ردگیری مکان‌نما.
- پالایش تجربه کاربری: تم‌های مدرن تیره/روشن/کنتراست بالا، درجه اطمینان پیش‌بینی، جادوگر راه‌اندازی اولیه و منوی ترای ارتقایافته.
- مانیفست متمرکز داده‌ها، همگام‌سازی پروفایل یادگیری و تضمین مهاجرت بی‌نقص از کلیه نسخه‌های قبلی.
- رابط کاربری دو زبانه (فارسی و انگلیسی) با پشتیبانی کامل از چینش راست‌به‌چپ (RTL) و تغییر آنی زبان.
- موتور پیش‌بینی هوشمند نگارش ۲ مجهز به الگوریتم Stupid Backoff، زوال نمایی فراوانی و درک بستر برنامه فعال.
- همگام‌سازی ابری ۲٫۰ پشتیبان سرویس‌های WebDAV و GitHub Gist همراه با ادغام ۳طرفه واژگان.
- ماشین‌حساب پیشرفته درون‌متنی، ضبط و اجرای ماکرو، حالت تایپ سریع (Power Mode) و پشتیبان‌گیری ZIP از طریق خط فرمان.

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

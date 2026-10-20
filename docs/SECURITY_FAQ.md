# Security, Privacy & Transparency FAQ
# پرسش‌های متداول امنیت، حریم خصوصی و شفافیت روان

> **Summary:** Ravaan is 100% open-source, local-only, and features zero keystroke logging, zero telemetry, and zero network calls by default.
>
> **خلاصه:** نرم‌افزار روان کاملاً متن‌باز و محلی است؛ هیچ کلیدی ذخیره نمی‌شود، هیچ اطلاعاتی ارسال نمی‌گردد و به طور پیش‌فرض هیچ اتصال شبکه‌ای برقرار نمی‌شود.

---

## English

### 1. Why does Ravaan require a low-level keyboard hook?
Ravaan operates as a background typing assistant that suggests completions, corrects typos, fixes wrong keyboard layouts (e.g., `sghl` $\leftrightarrow$ `سلام`), and manages Persian zero-width non-joiners (نیم‌فاصله) across any active Windows application.

Windows does not provide a system-wide keystroke prediction stream to desktop applications. To observe keystrokes in real time and replace text when needed, Ravaan registers a low-level Windows hook via `SetWindowsHookExW` with `WH_KEYBOARD_LL`.

- **Processing is instantaneous:** Keystroke evaluation completes in under 1 millisecond.
- **Immediate pass-through:** All keystrokes pass directly to the target application without delay or interruption.

### 2. Does Ravaan record, log, or transmit what I type?
**No. Absolutely not.**
- **Zero Keystroke Logging:** The typed buffer is kept solely in volatile memory (RAM) in a small circular buffer (maximum 32 characters) solely to match the immediate word being typed. Once a word delimiter (space, enter, tab) or backspace is pressed, or when you switch windows, the buffer is cleared. No keystrokes are ever saved to disk.
- **Zero Telemetry & Analytics:** Ravaan contains no analytics trackers, no tracking pixels, and no third-party telemetry SDKs.
- **Local-Only Operation:** Your settings, custom snippets, and personal dictionary reside exclusively in `%APPDATA%\Ravaan` on your computer.
- **Secure Credential Storage:** Sensitive configuration (such as WebDAV sync passwords) is encrypted with the Windows Data Protection API (DPAPI) or Windows Credential Manager.

### 3. Why do some antivirus scanners flag new releases? (False Positives)
Executable releases of Ravaan are packaged with PyInstaller, an open-source tool that bundles the Python runtime, dependencies, and application assets into standalone Windows executables.

Because certain malicious scripts also use PyInstaller to bundle payloads, generic antivirus heuristic scanners frequently trigger **false positive** alerts on new, unrecognized binaries that haven't yet accumulated thousands of downloads.

To guarantee that your binary is authentic:
1. **Verify the SHA256 Checksum:** Compare the file hash against `SHA256SUMS.txt` published on the [official GitHub Releases page](https://github.com/mohsen-niksirat/Ravaan/releases).
2. **Inspect the Code:** The entire codebase is open-source under the MIT license. You can review every line of code on GitHub.
3. **Build from Source:** You can build Ravaan yourself directly from source code using standard Python tools:
   ```powershell
   git clone https://github.com/mohsen-niksirat/Ravaan.git
   cd Ravaan
   pip install -e .
   pyinstaller ravan.spec
   ```

### 4. How can I independently verify Ravaan's privacy?
- **Network Activity:** Open Windows Resource Monitor (`resmon.exe`) or run `netstat -ano | findstr Ravaan` in PowerShell. You will observe 0 active outbound network connections.
- **Disk Activity:** Run Sysinternals Process Monitor (`ProcMon`). Filter by process `Ravaan.exe` and confirm that file writes are confined strictly to `%APPDATA%\Ravaan` and that no keystroke log files exist.

---

## فارسی (Persian)

### ۱. چرا روان به قلاب صفحه‌کلید (Keyboard Hook) نیاز دارد؟
روان به عنوان دستیار هوشمند تایپ عمل می‌کند که پیشنهاد واژگان، تصحیح اشتباهات تایپی، اصلاح خودکار زبان صفحه‌کلید (مانند تبدیل `sghl` به `سلام`) و درج نیم‌فاصله را در تمام برنامه‌های ویندوز (مانند ورد، مرورگر، تلگرام و...) فراهم می‌سازد.

سیستم‌عامل ویندوز رابط مستقیمی برای دریافت جریان تایپ به دستیارهای شخص ثالث ارائه نمی‌دهد. برای خواندن کلیدها و جایگزینی هوشمند در همان لحظه تایپ، روان از قلاب استاندارد ویندوز (`SetWindowsHookExW` با نوع `WH_KEYBOARD_LL`) استفاده می‌کند.
- **پردازش بی‌درنگ:** پردازش هر کلید کمتر از ۱ میلی‌ثانیه زمان می‌برد.
- **عدم ایجاد تاخیر:** کلیدها بلافاصله و بدون وقفه به نرم‌افزار مقصد تحویل داده می‌شوند.

### ۲. آیا روان کلیدها را ضبط می‌کند یا به جایی ارسال می‌نماید؟
**خیر، به هیچ عنوان.**
- **عدم ثبت کلیدها (Zero Keystroke Logging):** حروف تایپ‌شده تنها در حافظه موقت رم (RAM) در یک بافر چرخشی کوچک (حداکثر ۳۲ نویسه) نگهداری می‌شوند تا آخرین کلمه در حال تایپ تشخیص داده شود. با فشردن فاصله، اینتر، بک‌اسپیس یا تعویض پنجره، این بافر فوراً پاک می‌شود. هیچ فایلی از کلیدهای شما ذخیره نمی‌گردد.
- **عدم ارسال داده و تلمتری (Zero Telemetry):** هیچ ابزار آماری یا ردیابی در روان وجود ندارد و هیچ داده‌ای به هیچ سروری فرستاده نمی‌شود.
- **ذخیره‌سازی ۱۰۰٪ محلی:** واژه‌نامه یادگرفته‌شده، متن‌های آماده و تنظیمات شما فقط روی دیسک خودتان در مسیر `%APPDATA%\Ravaan` نگهداری می‌شوند.
- **رمزنگاری اطلاعات حساس:** اطلاعاتی مثل رمز عبور همگام‌سازی ابری به کمک سامانه امنیتی ویندوز (DPAPI / Credential Manager) رمزنگاری می‌شوند.

### ۳. علت هشدار آنتی‌ویروس‌ها برای نسخه‌های جدید چیست؟ (False Positive)
نسخه‌های اجرایی روان به کمک ابزار استاندارد و متن‌باز PyInstaller کامپایل می‌شوند که مفسر پایتون و فایل‌های موردنیاز را درون یک بسته اجرایی قرار می‌دهد.

از آنجا که برخی بدافزارها نیز متاسفانه از PyInstaller استفاده می‌کنند، موتورهای بررسی اکتشافی (Heuristic) آنتی‌ویروس‌ها گاهی فایل‌های جدید و ناشناخته را به اشتباه مشکوک تشخیص می‌دهند.

برای اطمینان از سلامت فایل:
۱. **بررسی هش SHA-256:** کد اعتبارسنجی فایل را با فایل `SHA256SUMS.txt` در [صفحه رسمی ریلیز گیت‌هاب](https://github.com/mohsen-niksirat/Ravaan/releases) مطابقت دهید.
۲. **بررسی کد منبع:** تمام کدهای روان به شکل متن‌باز در گیت‌هاب در دسترس همگان است.
۳. **ساخت مستقیم از کد:** در صورت تمایل می‌توانید با اجرای دستورات زیر خودتان نسخه اجرایی را بسازید:
   ```powershell
   git clone https://github.com/mohsen-niksirat/Ravaan.git
   cd Ravaan
   pip install -e .
   pyinstaller ravan.spec
   ```

### ۴. چطور خودم می‌توانم امنیت و عدم ارسال داده را بررسی کنم؟
- **بررسی شبکه:** برنامه Resource Monitor ویندوز را باز کنید یا دستور `netstat -ano | findstr Ravaan` را اجرا نمایید؛ هیچ اتصال خروجی پنهانی مشاهده نخواهید کرد.
- **بررسی دیسک:** به کمک ابزار رایگان Sysinternals Process Monitor می‌توانید ببینید روان به هیچ پوشه حساسی دسترسی ندارد و هیچ فایلی از کلیدهای تایپ‌شده ایجاد نمی‌کند.

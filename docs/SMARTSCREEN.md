# Bypassing Windows Defender SmartScreen
# راهنمای عبور از اخطار اسمارت‌اسکرین ویندوز (SmartScreen)

> **Quick Answer:** When Windows Defender SmartScreen shows *"Windows protected your PC"*, click **"More info"** $\to$ **"Run anyway"**.
>
> **راهنمای سریع:** هنگام مشاهده پیام آبی‌رنگ *"Windows protected your PC"* روی گزینه **"More info" (اطلاعات بیشتر)** کلیک کرده و سپس دکمه **"Run anyway" (در هر صورت اجرا شود)** را انتخاب کنید.

---

## English

### What is Windows Defender SmartScreen?
Microsoft Defender SmartScreen is a Windows security mechanism designed to flag newly released executables that do not yet have an established reputation or an expensive commercial Extended Validation (EV) code-signing certificate.

Because Ravaan is a community-driven, free, and open-source project, new version releases may trigger the SmartScreen blue banner until sufficient reputation has been built or until our automated SignPath Foundation signing is active.

### Step-by-Step Instructions

1. **SmartScreen Dialog Appears:**
   When you launch `Ravaan-Setup-1.0.0.exe` or `Ravaan.exe`, Windows displays a blue notification window stating:
   > *"Windows protected your PC"*
   > *"Microsoft Defender SmartScreen prevented an unrecognized app from starting. Running this app might put your PC at risk."*

2. **Click "More info":**
   Click the underlined link labeled **"More info"** located directly beneath the warning message.

3. **Verify and Run:**
   The window will now display additional details:
   - **App:** `Ravaan-Setup-1.0.0.exe` (or `Ravaan.exe`)
   - **Publisher:** Unknown publisher (or Mohsen Niksirat)
   
   A new button labeled **"Run anyway"** will appear in the lower right corner. Click **"Run anyway"** to launch the installer or application.

### Safety Verification Before Running
If you want to be 100% sure the downloaded file has not been tampered with:
1. Open PowerShell in the folder where the file was downloaded.
2. Run:
   ```powershell
   Get-FileHash .\Ravaan-Setup-1.0.0.exe -Algorithm SHA256
   ```
3. Verify that the displayed hash matches the official hash listed in `SHA256SUMS.txt` on the [official releases page](https://github.com/mohsen-niksirat/Ravaan/releases/tag/v1.0.0).

---

## فارسی (Persian)

### اخطار اسمارت‌اسکرین ویندوز چیست؟
سامانه SmartScreen مایکروسافت قابلیتی در ویندوز است که هنگام اجرای برنامه‌های تازه منتشرشده که هنوز توسط هزاران کاربر دانلود نشده‌اند یا دارای گواهی تجاری گران‌قیمت EV نیستند، یک پیام احتیاطی آبی‌رنگ نمایش می‌دهد.

با توجه به این‌که روان یک پروژه کاملاً رایگان، مستقل و متن‌باز است، در ابتدای انتشار هر نسخه ممکن است ویندوز این پنجره را به شما نشان دهد.

### راهنمای تصویری و گام‌به‌گام

۱. **مشاهده پنجره اخطار:**
   هنگام اجرای فایل نصب (`Ravaan-Setup-1.0.0.exe`) پنجره‌ای با عنوان زیر ظاهر می‌شود:
   > *"Windows protected your PC"*
   > *(ویندوز از رایانه شما محافظت کرد)*

۲. **کلیک روی گزینه More info:**
   روی لینک زیر خط‌دار **"More info"** (اطلاعات بیشتر) در زیر متن اخطار کلیک کنید.

۳. **تایید و اجرا:**
   نام فایل و ناشر نمایش داده شده و دکمه جدیدی به نام **"Run anyway"** (در هر صورت اجرا شود) در گوشه پایین پنجره فعال می‌گردد. روی این دکمه کلیک کنید تا نرم‌افزار اجرا شود.

### چگونه قبل از اجرا از سلامت فایل مطمئن شوم؟
برای اطمینان ۱۰۰٪ از اصالت فایل:
۱. محیط PowerShell را باز کنید و دستور زیر را اجرا نمایید:
   ```powershell
   Get-FileHash .\Ravaan-Setup-1.0.0.exe -Algorithm SHA256
   ```
۲. رشته ۶۴ حرفی نمایش داده شده را با فایل رسمی `SHA256SUMS.txt` در [صفحه رسمی انتشار روان در گیت‌هاب](https://github.com/mohsen-niksirat/Ravaan/releases/tag/v1.0.0) مقایسه کنید. یکسان بودن این دو کد به معنای دست‌نخورده بودن و سلامت کامل فایل است.

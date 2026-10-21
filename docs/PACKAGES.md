# Ravaan Snippet Packages (.ravaanpack)

A secure, offline, portable package format for sharing snippet bundles, templates, regex expansions, and image snippets across machines and team members.

---

## 1. Overview & Architecture

A `.ravaanpack` file is a standard ZIP archive containing:
1. `manifest.json`: Metadata, snippet definitions, application group filters, and cryptographic digests.
2. `images/`: Embedded image assets for rich image snippets (indexed by SHA-256 content hashes).

### Key Features
- **Offline & Private**: Zero external dependencies, no telemetry, and 100% local import/export.
- **Full Snippets 3.0 Support**: Handles plain text, dynamic placeholders (`{{shamsi}}`, `{{time}}`, `{{calc:...}}`, etc.), interactive forms (`[[label]]`), regex triggers (`re:...`), and image snippets (`image:...`).
- **App-Group Filters**: Bundles application context filters (`SnippetGroup`) so snippets only fire in designated apps (e.g., Slack, VS Code, Word).
- **Collision Protection**: Existing triggers are never silently overwritten. Collisions are flagged and skipped unless explicit replacement is requested.

---

## 2. Cryptographic Integrity & Tamper Protection

Every snippet replacement string and image binary in a `.ravaanpack` package is fingerprinted with an individual **SHA-256** hash recorded in `manifest.json`.

During `inspect_package()` or `import_package()`:
1. Every replacement string is re-hashed and verified against its `sha256` digest in the manifest.
2. Every image file inside the archive is extracted in memory and hashed.
3. If any snippet or image has been altered, tampered with, or corrupted, Ravaan immediately aborts and raises a `PackageIntegrityError`, refusing to import untrusted modifications.
4. **ZipSlip Traversal Guard**: Filenames and archive paths are strictly validated against directory traversal attacks (`../`).

---

## 3. Package Manifest Specification (`manifest.json`)

```json
{
  "format": "ravaanpack",
  "format_version": 2,
  "version": 2,
  "name": "Persian Dates & Calendar",
  "author": "Ravaan Community",
  "description_en": "Jalali (Shamsi) date, time, weekday, and UUID expansion snippets.",
  "description_fa": "مجموعه میانبرهای تاریخ خورشیدی (شمسی)، ساعت، روز هفته و شناسه یکتا.",
  "snippet_count": 7,
  "snippets": [
    {
      "trigger": ";;tarikh",
      "replacement": "{{tarikh}}",
      "enabled": true,
      "is_regex": false,
      "app_filter": "",
      "is_image": false,
      "groups": ["persian_dates"],
      "sha256": "aef789aa841e411b7fcf76eb1f8346e382d6da824c3dfcf70a3118cf674b0c23"
    },
    {
      "trigger": "re:;;d(\\d+)",
      "replacement": "Date: {{tarikh}}",
      "enabled": true,
      "is_regex": true,
      "app_filter": "",
      "is_image": false,
      "groups": [],
      "sha256": "6c15358c5c7ce1a5ba8296a1a117dcf49bfd5d7429188e0a37340ec594950ce4"
    }
  ],
  "groups": [
    {
      "id": "persian_dates",
      "name": "Persian Dates & Utilities",
      "matchers": ["*.exe"],
      "enabled": true
    }
  ],
  "word_list": []
}
```

---

## 4. Usage

### Graphical Interface (GUI)
1. **Importing**:
   - Go to **Settings > Snippets** and click **📦 Import Package…** (or open **Snippet Editor** and click **📦 Import Package…**).
   - Select any `.ravaanpack` file.
   - The preview dialog verifies cryptographic integrity and displays:
     - Package name, author, and description.
     - Snippet count and per-app groups.
     - Table of all triggers and expansions.
     - Collision warnings if any triggers already exist in your snippets.
   - Tick **Replace existing snippets on collision** if you wish to overwrite duplicates, then click **Import Package**.
2. **Exporting**:
   - Open **Snippet Editor** and click **📦 Export Package…**.
   - Fill in the title, author, and descriptions.
   - Check the snippets and groups you want to include.
   - Save your `.ravaanpack` bundle.

### Command Line Interface (CLI)

```powershell
# Export all snippets and groups to a package
python -m ravan.cli pack export ./my-pack.ravaanpack --title "My Snippets" --author "Me"

# Import a package safely (skipping colliding triggers)
python -m ravan.cli pack import ./examples/persian-dates.ravaanpack

# Import a package and replace existing triggers on collision
python -m ravan.cli pack import ./examples/persian-dates.ravaanpack --replace
```

---

## ۵. راهنمای بسته‌های روان (فارسی)

بسته‌های `.ravaanpack` روشی ساده، سریع و ۱۰۰٪ آفلاین برای اشتراک‌گذاری مجموعه‌های متنی، قالب‌های آماده، فرم‌ها و تصاویر بین رایانه‌ها یا اعضای تیم هستند.

### ویژگی‌های اصلی
- **امنیت بالا با هش رمزنگاری SHA-256**: هر قطعه‌متن و تصویر پیش از خروجی هش‌گذاری می‌شود. در صورتی که فایل بسته دستکاری شده باشد، روان بلافاصله متوجه شده و از ورود آن جلوگیری می‌کند.
- **محافظت در برابر رونویسی ناخواسته (Collision Protection)**: اگر میانبر موجود در بسته با میانبرهای از پیش تعریف‌شده شما یکسان باشد، بدون اجازه شما بازنویسی نمی‌شود مگر اینکه گزینه «جایگزینی در صورت تداخل» را انتخاب کنید.
- **پشتیبانی کامل از Snippets 3.0**: پشتیبانی از متغیرهای پویا (`{{shamsi}}`, `{{time}}`)، فیلدهای فرم (`[[label]]`)، عبارات باقاعده (`re:...`) و تصاویر کلیپ‌بورد.

### نحوه استفاده در خط فرمان
```powershell
# استخراج پکیج از میانبرهای فعلی
python -m ravan.cli pack export ./my-pack.ravaanpack --title "میانبرهای من"

# وارد کردن بسته به صورت امن
python -m ravan.cli pack import ./examples/persian-dates.ravaanpack

# وارد کردن بسته با جایگزینی موارد تداخل‌دار
python -m ravan.cli pack import ./examples/persian-dates.ravaanpack --replace
```

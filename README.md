# Ravaan (روان) — v1.0.0

> **The lightweight, privacy-first, bilingual Persian/English typing copilot for Windows.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078d4.svg)](https://microsoft.com/windows)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![Version: 1.0.0](https://img.shields.io/badge/Release-v1.0.0%20Stable-success.svg)](https://github.com/mohsen-niksirat/Ravaan/releases/tag/v1.0.0)

Ravaan helps typists with keyboard-language awareness, wrong-layout conversion (F12), real-time word/sentence prediction, intelligent half-spaces (ZWNJ), text snippets, math evaluation, and clipboard history — seamlessly in any Windows app.

[Features](#features) • [Installation](#installation) • [Privacy & Data (DATA.md)](DATA.md) • [Security (SECURITY.md)](SECURITY.md) • [Changelog](CHANGELOG.md) • [راهنمای فارسی](#فارسی)

---

## Installation

### 1. Windows Installer (`Ravaan-Setup-1.0.0.exe`) — Recommended
- **Non-admin per-user installation**: installs cleanly into `%LOCALAPPDATA%\Programs\Ravaan` without requiring UAC administrator prompts.
- **System integration**: creates Start Menu shortcuts, optional launch at startup, and registers `ravan://` deep links.
- **Safe uninstaller**: cleanly uninstalls while preserving your custom vocabulary and settings in `%APPDATA%\Ravan\`.

### 2. Portable Package (`Ravaan-1.0.0-portable.zip`)
- **Zero-installation portable build**: includes standalone `Ravaan.exe` and documentation.
- Simply extract to any folder or USB drive and run.

### 3. From Source (Developers)
```bash
git clone https://github.com/mohsen-niksirat/Ravaan.git
cd Ravaan
pip install -e .[dev]
python -m ravan
```

---

## Features

| Milestone | Feature | Hotkey (default) |
| :--- | :--- | :--- |
| M1 | Language chip near caret on layout switch | `Alt+L` on demand |
| M2 | Convert selection or last word Persian ↔ English layout | `F12` |
| M3 | Word prediction popup (with expanded corpus 1300+ words) | see below |
| M4 | Autocorrect + snippets | on word boundary |
| M5 | Smart Persian half-space (ZWNJ: می/نمی & ها/تر/ترین) | Auto or `Shift+Space` |
| M6 | Clipboard history ring buffer popup | `Alt+V` |
| M7 | Persian/Arabic text & number normalization | `Ctrl+F12` or CLI `norm` & `num` |
| M8 | Cycle text case (UPPER → lower → Title) | `Shift+F12` |
| M9 | Inline math calculator | Type e.g. `1200*1.09=` or `۱۲*۵=` |
| M10 | Dynamic Jalali (Shamsi) date & time expander | `/today`, `/shamsi`, `/tarikh` |
| M11 | Number to Persian Words & Toman converter | Type `1250000/w`, `5000000/t`, `1250000/s` |
| M12 | Keyboard layout audio feedback | tray → Settings… |
| M13 | User custom dictionary & word learning | tray → Settings… or CLI `dict` |
| M14 | Cloud Sync (GitHub Gist) for dictionary & snippets | tray → Settings… → Sync |
| M15 | Quick Text Stats floating card | `Alt+S` |
| M16 | Standalone PyInstaller build (`Ravaan.exe`) & GitHub Actions | downloadable release asset |
| M17 | Diagnostics window, rotating logs & DPI awareness | tray → Diagnostics… |
| M18 | Bilingual autocorrect & instant undo | `Ctrl+Shift+Z` / `Backspace` |
| M19 | Snippets 2.0 (GUI editor, `|` / `$0` cursor, `{{clipboard}}`) | tray → Snippet Editor… |
| M20 | Code Quality (Modular refactoring, Ruff linting, Win32 mock tests) | `pytest` & `ruff check` |
| M21 | Continuous Android-Style Prediction, Sentence Prediction & Adaptive Learning | `Space` / `Tab` / `Enter` / `1–5` |
| M22 | Elevated App Detection & Window Class Exclusions | Settings → Excluded Apps |
| M23 | Performance Profiling (< 500ms startup) & Hook Latency Monitoring | Diagnostic logs |
| M24 | Interactive Window Picker (3s countdown) | Settings → Excluded Apps |
| M25 | Automatic Update Checker & CLI flags | `--check-updates` & tray menu |
| M26 | Full Bilingual UI Localization (fa / en) & Mirrored RTL | Settings → General |
| M27 | Prediction Quality (Trigrams, Continuations, Learning Engine v2) | `python -m ravan.cli bench` |
| M28 | Cloud Sync 2.0 (Generic WebDAV, 3-way merge, conflict resolution) | Settings → Sync |
| M29 | Windows Installer (Inno Setup), Auto-Updater & `ravan://` Protocol | GitHub Releases |
| M30 | Power User (Math v2, Keystroke Macro, Focus Power Mode, Profile CLI) | `Ctrl+Alt+P` / CLI |
| M31 | Windows QA Matrix, Selftest Diagnostic, Soak Test Harness | `python -m ravan.cli selftest` |
| M32 | UX Polish (Design Tokens, Wizard, Tray Toggles, Confidence Meter) | First Launch / Tray |
| M33 | Data Manifest, Privacy Architecture & Migration Engine | [DATA.md](DATA.md) |

### Convert Selection or Last Word (`F12`)

- Select text anywhere and press `F12` to convert between Persian and English keyboard layouts in place.
- If no text is selected, automatically converts the last word you typed.

### Smart Persian Half-Space (ZWNJ / نیم‌فاصله)

- Automatically converts prefixes like `می ` and `نمی ` to `می‌` and `نمی‌`.
- Automatically attaches plural/comparative suffixes like `کتاب ها` → `کتاب‌ها`, `سریع تر` → `سریع‌تر`.
- Press `Shift+Space` anytime to insert an explicit zero-width non-joiner (`\u200c`).

### In-Place Text Normalization (`Ctrl+F12`) & Case Cycling (`Shift+F12`)

- Press `Ctrl+F12` to clean and normalize Persian text in selected text (standardizes 'ي' and 'ك', spacing, ZWNJ) or the last typed word.
- Press `Shift+F12` to cycle letter case (`UPPERCASE` → `lowercase` → `Title Case`) in selected text or the last typed word.

### Number to Persian Words & Toman Calculator

- Type numbers with quick suffix triggers anywhere:
  - `1250000/w ` → `یک میلیون و دویست و پنجاه هزار`
  - `5000000/t ` → `پانصد هزار تومان` (converts Rial to Toman words)
  - `1250000/s ` → `۱,۲۵۰,۰۰۰` (formats with thousands separators)
- Or via CLI: `python -m ravan.cli words 1250000 --toman`

### Keyboard Layout Audio Feedback

- Optional subtle audio cues when switching between Persian and English layouts:
  - Persian: warm, lower pitch (650 Hz)
  - English: crisp, bright pitch (1100 Hz)
- Enable in **tray → Settings… → Audio feedback on keyboard layout switch**.

### Caret Clipboard History (`Alt+V`)

- Press `Alt+V` to open a quick paste popup right next to your active cursor.
- Browse recent clipboard items with **↑ / ↓**, press **Enter** or **1–5** to instantly paste into the active window.

### Inline Math Calculator on `=`

- Type any arithmetic expression followed by `=` anywhere to compute the result:
  `1200*1.09=` → `1308`
  `(50+30)*2=` → `160`
  `۱۲*۵=` → `۶۰` (supports Persian numbers)

### Dynamic Jalali Date, Time & Macro Snippets

- Type `/today` or `/shamsi` or `/امروز` + space → expands to current Shamsi date (`۱۴۰۵/۰۷/۲۳`).
- Type `/tarikh` or `/تاریخ` + space → expands to worded Persian date (`۲۳ مهر ۱۴۰۵`).
- Type `/time` or `/saat` or `/ساعت` + space → expands to current time (`۱۶:۲۰`).
- Type `/uuid` + space → expands to a fresh UUID.
- Use placeholders like `{{shamsi}}`, `{{time}}`, `{{uuid}}` in custom snippet templates!

### User Custom Dictionary

- Add custom jargon, names, or terminology in **Settings → Custom words** or via CLI:
  ```bash
  python -m ravan.cli dict add "fastapi"
  python -m ravan.cli dict list
  ```
- Words in your custom dictionary immediately appear in word prediction completions!

### Continuous Android-Style Prediction & Adaptive Learning

1. **Immediate & Continuous Prediction**: Starts from the **1st letter** you type and stays active continuously without premature closing until you finalize the word with `Space` or punctuation.
2. **Android-Style Preview**: The top candidate is clearly highlighted with accented background and bold text.
3. **Sentence & Next-Word Prediction**: After completing a word and typing `Space`, Ravaan predicts plausible next words (`[بعدی]`) based on common Persian bigrams (`سلام` → `عزیز`, `با` → `احترام`, etc.) to let you compose full sentences effortlessly.
4. **Typing Style Learning Engine**: Ravaan silently learns the vocabulary and two-word transitions you use most frequently, automatically ranking your personal favorite words at the top.
5. **Atomic Injection**: Text replacements and backspaces occur in a single unified OS hardware batch, guaranteeing zero keystroke collisions even during ultra-fast typing.
6. **Choosing a candidate**:
   - **↑ / ↓** — move highlight
   - **Enter** or **Tab** — insert the highlighted suggestion
   - **1 … 5** — jump-insert that candidate row
   - **Esc** — dismiss without inserting

### Autocorrect (Safe Mode & Language Intelligence)

- **Safe Guard**: Autocorrect only fires when the typed word is **not** already a valid dictionary word.
- **Bilingual Awareness**: Strictly tracks the active layout hook so Persian and English words are never cross-corrected or mangled.
- **Persian Confusable Typos**: Automatically resolves Arabic/Persian confusable keys (`ي/ی`, `ك/ک`, `ة/ه`, `ة/ت`) with dictionary validation.
- **Undo Autocorrect**: Made a mistake or wanted the exact typed typo? Press `Ctrl+Shift+Z` or simply tap `Backspace` immediately to instantly revert to what you typed.
- **Punctuation Spacing**: Automatically strips accidental spaces preceding punctuation marks (`.` `,` `!` `?` `:` `;` `؛` `،` `؟`).

### Snippets 2.0 (Multi-line, Cursor Placement, Math, Clipboard & Toggles)

- **Dedicated Snippet Editor**: Access via **tray → Snippets…** or **Settings → Open Snippet Editor…** featuring a live expansion preview, search filter, and quick placeholder buttons.
- **Per-Snippet Toggle**: Enable or disable individual snippets with a single click without deleting them.
- **Multi-line Templates**: Create rich multi-line expansions (code boilerplate, email templates, addresses, standard notes).
- **Cursor Placement (`|` or `$0` or `{{cursor}}`)**: Position the typing cursor anywhere inside the inserted template (e.g. `console.log(|);` or `func($0)` places the caret right at the pipe position).
- **Clipboard Content Insertion (`{{clipboard}}`)**: Automatically embed the current clipboard text directly into the expanded snippet.
- **Extended Date Macros**:
  - `{{year}}`, `{{month}}`, `{{day}}`, `{{weekday}}`, `{{hafteh}}`, `{{gregorian}}`
  - `{{yesterday}}`, `{{tomorrow}}`, `{{time_sec}}`, `{{timestamp}}`
- **Embedded Math & Calculations**:
  - `{{calc: 100 * 1.09}}` → `109`
  - `{{math: (50 + 30) * 2}}` → `160`
  - `{{calc: ۱۲ * ۵}}` → `۶۰` (supports Persian digits)
- **JSON Import / Export**: Backup, restore, and share snippet libraries with 1-click JSON import (merge or replace) and export.
- **Excluded Apps Safety**: Snippet triggers are completely disabled inside excluded applications (password managers, games, terminal emulators).

### Quick Text Stats (`Alt+S`)

- Select any text in any Windows application and press `Alt+S` to display an instant, modern statistics card at your caret or mouse cursor.
- Displays:
  - **Words**: Total word count
  - **Characters**: Total characters (with and without whitespace)
  - **Reading time**: Estimated reading duration in minutes/seconds (~200 wpm)
  - **Persian / English ratio**: Language breakdown percentage (e.g. `85% فا / 15% EN`)
- Dismisses smoothly with **Esc** or when clicking outside.

### Cloud Sync (GitHub Gist)

- Opt-in synchronization for your custom dictionary (`user_words.txt`) and custom snippets across multiple computers.
- Configured via **tray → Settings… → Sync tab**:
  - Enter your GitHub Personal Access Token (PAT) with `gist` scope.
  - Automatically creates or links a private GitHub Gist (`ravaan-cloud-sync.json`).
  - Automatic timestamped local backups (`.bak`) before any remote pull/push.
  - Periodic background sync interval (optional) or manual 1-click **Sync Now**.

### Power-User Features: Math v2, Macro Recorder & Power Mode

1. **Inline Math v2 (`%`, `=N`, `=t`, `=r`)**:
   - **Percentages**: Evaluate discounts, markups, or multiplications inline (e.g. `500+10%=` → `550`, `100*20%=` → `20`, or Persian `۵۰۰+۱۰٪=` → `۵۵۰`).
   - **Rounding Macros (`=N`)**: Explicit decimal control e.g. `10/3=2` → `3.33`, `1200*1.09=2` → `1308.00`, `10/3=0` → `3`.
   - **Currency Formatting**: Format numbers directly into currency: `=t` or `=ت` formats as Toman (`12000=t` → `12,000 تومان`), `=r` or `=ر` formats as Rial (`120000=r` → `120,000 ریال`).
   - **Password Protection**: Inline math evaluation, autocorrect, and word prediction are automatically suspended inside password input fields for security.

2. **Macro Recorder (M23)**:
   - Record short keystroke sequences: start from System Tray → **Record Macro…**, type your keystrokes, and press **Esc** to finish.
   - Saves directly as a snippet trigger (e.g. `//m1`).
   - Choose whether to preserve actual typing delays/timings or replay instantly.
   - Built-in notification and safety notice regarding elevated applications.

3. **Power Mode / Focus Typing (`Ctrl+Alt+P`) (M24)**:
   - One-touch toggle via `Ctrl+Alt+P` or System Tray menu.
   - Suppresses all popups (prediction card, language chip, text statistics) for clean, distraction-free typing during meetings and screen sharing sessions.
   - Dims the tray icon and updates its tooltip. Supports optional timed duration.

4. **CLI Profile Backup & Migration (`export` / `import`)**:
   - Export your entire Ravaan profile (config, dictionary, snippets, and learned models) into a single compressed ZIP archive:
     ```bash
     python -m ravan.cli export my_backup.zip
     ```
   - Restore or merge on another PC:
     ```bash
     python -m ravan.cli import my_backup.zip --merge
     ```

### Interactive Window Picker & Elevated Process Detection

- **Pick Window (3s countdown)**: In Settings → Excluded Apps, click **Pick Window…** and switch to any target application window. Ravaan captures its `.exe` process name or window class (`class:<name>`) automatically.
- **Elevation Status Warning**: Real-time detection warns you if foreground apps run with Administrator privileges while Ravaan runs standard user, preventing unexpected hook deadlocks.

### Update Checker & Versioning

- Check for the latest releases directly from GitHub:
  - In System Tray: click **Check for updates…** to see the current version and any available update.
  - Via CLI: `python -m ravan --version` or `python -m ravan --check-updates`.


## Requirements

- Windows 10/11
- Python 3.10+

## Installation & Quick Start

### 1. Standalone Executable (Recommended for users, no Python required)

1. Download **`Ravaan.exe`** from [GitHub Releases](https://github.com/mohsen-niksirat/Ravaan/releases).
2. Double-click `Ravaan.exe` to run. A steelblue icon (ر) appears in your Windows system tray.
3. (Optional) In system tray → **Settings…**, check **Launch at Windows startup**.

### 2. From Source (Developers)

```bash
git clone https://github.com/mohsen-niksirat/Ravaan.git
cd Ravaan
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

**Run from source:**
- Double-click `run_ravan.bat` (launches windowless via `pythonw`), or run `python -m ravan`.

### 3. Build Executable Locally

```bash
pip install pyinstaller
pyinstaller --clean -y ravan.spec
# Executable is generated at: dist/Ravaan.exe
```

## Uninstallation

1. Right-click the Ravan tray icon and click **Quit**.
2. If startup launch was enabled, disable it in Settings before quitting (or remove the `Ravan` entry from Windows Startup apps).
3. (Optional) Remove user settings, custom words, and logs:
   Delete `%APPDATA%\Ravan` (`C:\Users\<Username>\AppData\Roaming\Ravan`).
4. Delete `Ravaan.exe` or your cloned repository directory.

### Tray menu

- **Show language (Alt+L)** — show the language chip now
- **Settings…** — hotkeys, toggles, snippets, excluded apps detector, sync, startup
- **Snippet Editor…** — manage custom snippets, cursor placeholder, and toggles
- **Check for updates…** — check GitHub releases for the latest version
- **Diagnostics…** — live status inspector (hook state, caret source, active app, last 50 events, copy markdown report)
- **Word prediction** — toggle on/off (persisted)
- **Quit**

System tray icon → Quit to exit. Logs: `%APPDATA%\Ravan\logs\ravan.log` (capped with automatic 5MB log rotation and 3 backups).
Config: `%APPDATA%\Ravan\config.json`

## CLI diagnostics & flags

```bash
python -m ravan --version              # display current version (v0.5.0)
python -m ravan --check-updates        # check GitHub for new releases
python -m ravan.cli lang                # current keyboard language
python -m ravan.cli caret               # caret / cursor position
python -m ravan.cli convert hjvfd       # convert a word EN↔FA layout
python -m ravan.cli convert "o,vn"
python -m ravan.cli predict pro         # show prediction candidates
python -m ravan.cli inject "hello روان" # inject text into the focused field (diagnostic)
python -m ravan.cli hook -t 5           # print raw captured hook events
python -m ravan.cli calc "1200*1.09"    # calculate math expression (supports Persian digits)
python -m ravan.cli words 1250000       # convert number to Persian words
python -m ravan.cli words 5000000 --toman  # convert Rial to Toman words
python -m ravan.cli words 1250000 --sep    # format with thousands separators
python -m ravan.cli jalali              # print current Jalali (Shamsi) date & time
python -m ravan.cli norm "متن عربي"     # normalize Persian text, ZWNJ, and punctuation
python -m ravan.cli num "09123456789"   # toggle digits Persian ↔ English
python -m ravan.cli dict list           # list user custom words
python -m ravan.cli dict add "fastapi"  # add custom word to prediction engine
python -m ravan.cli dict remove "word"  # remove custom word
```

> Each `python -m ravan` instance is single-instance-guarded (named mutex). Restarting
> after an update re-runs the new code (the tray icon of the old process must be quit first).

## Installation & Upgrade Guide

Ravaan provides three distribution channels depending on your workflow:

### 1. Windows Installer (`Ravaan-Setup-x.y.z.exe`) — Recommended
- **Non-admin install**: Installs per-user directly to `%LOCALAPPDATA%\Programs\Ravaan` without requiring UAC administrator privileges.
- **Strict filesystem containment**: Ravaan strictly confines all user settings and data to `%APPDATA%\Ravan` and writes nowhere else on the filesystem. See [SECURITY.md](SECURITY.md) for our detailed threat model and privacy policy.
- **Start Menu & Startup**: Adds a Start Menu shortcut and an optional Windows startup entry.
- **Protocol handler**: Automatically registers the `ravan://` URL protocol for deep links.
- **Clean uninstall**: Uninstaller removes the application cleanly while preserving your personal dictionaries, snippets, and settings in `%APPDATA%\Ravan`.

### 2. Standalone Portable ZIP (`Ravaan-x.y.z-portable.zip`)
- Zero-install portable package containing `Ravaan.exe`, documentation, and license.
- Download `Ravaan-x.y.z-portable.zip` from [GitHub Releases](https://github.com/mohsen-niksirat/Ravaan/releases), extract to any directory, and launch `Ravaan.exe` directly.

### 3. From Source (Development)
```bash
git clone https://github.com/mohsen-niksirat/Ravaan.git
cd Ravaan
python -m pip install --upgrade pip
pip install -e .[dev]
python -m ravan
```

### In-App Auto-Updater
- Ravaan automatically checks for new releases or on-demand via **tray → Check for updates…**.
- When an update is detected, a non-blocking notification displays the changelog summary.
- Clicking **Download & Install** downloads the new installer, smoothly releases the running instance mutex, launches the setup wizard, and exits the application cleanly.

### `ravan://` Deep Link Protocol
Ravaan registers a lightweight per-user URL protocol handler for desktop integrations:
- `ravan://settings` — Open Settings window
- `ravan://stats` — Open Quick Text Statistics
- `ravan://snippet?trigger=@@` — Open Snippet Editor focused on a trigger

## Tests

```bash
pytest
```

## Localization / Internationalization (i18n)

Ravaan features a full native bilingual UI (Persian and English) with live language switching in Settings, automatic Windows display language detection, and dynamic RTL/LTR layout adjustment.

### Supported Locales:
- `fa`: Persian (فارسی) — native phrasing, correct ZWNJ typography, and right-to-left layout.
- `en`: English — default international locale.
- `auto`: Automatically detects Windows display language via Win32 `GetUserDefaultUILanguage()`.

### Adding a New Language (e.g. German `de.json`):
1. **Copy catalog**: Copy `ravan/data/locales/en.json` to `ravan/data/locales/de.json`.
2. **Translate strings**: Translate string values in `de.json` while keeping placeholders (e.g. `{count}`, `{version}`, `{time}`) intact.
3. **Register locale (optional RTL)**: If your language is right-to-left (e.g. Arabic `ar`), add its code to `_RTL_LOCALES` in `ravan/core/i18n.py`.
4. **Select in UI**: Set `"ui_language": "de"` in `config.json` or choose it in the UI Language dropdown in Settings.

## Architecture

```
ravan/
  core/       # config, layout map, dictionary, predictor, snippets, sync, updater, text_stats, i18n
  data/       # locales (en.json, fa.json)
  platform/   # Win32 hook, language, caret (UIA), SendInput, focus, single-instance, startup
  ui/         # overlay, tray, settings window, stats popup, window picker, snippet editor, app loop
```

## فارسی

**روان** یک دستیار تایپ هوشمند و سبک برای ویندوز است:

- نمایش زبان صفحه‌کلید (EN / فا) کنار نشانگر متن هنگام تغییر چیدمان (یا با `Alt+L`)
- تبدیل چیدمان متن انتخاب‌شده یا آخرین کلمه تایپ شده بین فارسی و انگلیسی با `F12`
  مثال: `o,vn` → `خورد` یا انتخاب یک پاراگراف و زدن `F12`
- نیم‌فاصله‌گذاری هوشمند فارسی (ZWNJ): اتصال خودکار «می/نمی» و پسوندهای «ها/تر/ترین/مند/شناس» یا درج با `Shift+Space`
- آمار سریع متن (`Alt+S`): انتخاب هر متن و مشاهده فوری تعداد کلمات، حروف، زمان تقریبی مطالعه و درصد کلمات فارسی/انگلیسی در یک کارت شناور مدرن
- همگام‌سازی ابری اختیاری (Cloud Sync): همگام‌سازی امن واژگان شخصی و کلمات اختصاری بین سیستم‌های مختلف از طریق GitHub Gist با پشتیبان‌گیری خودکار محلی
- اسنیپت‌های پیشرفته ۲.۰: امکان تعیین محل دقیق نشانگر با نماد لوله `|` یا `$0`، درج خودکار محتوای کلیپ‌بورد با `{{clipboard}}` و فعال/غیرفعال‌سازی تک‌تک اسنیپت‌ها
- انتخاب‌گر هوشمند پنجره‌ها (Window Picker): تشخیص خودکار نام پردازه یا کلاس پنجره (`class:<name>`) با شمارش معکوس ۳ ثانیه‌ای برای افزودن به لیست برنامه‌های مستثنی
- تشخیص و هشدار برنامه‌های ادمین (Elevated): هشدار هوشمند در تنظیمات در صورت اجرای برنامه‌های فعال با دسترسی Administrator
- بررسی به‌روزرسانی: بررسی نسخه‌های جدید از گیت‌هاب از طریق منوی Tray و دستور `python -m ravan --check-updates`
- نرمال‌سازی درجا و پاکسازی متن فارسی (اصلاح «ي» و «ك»، نیم‌فاصله‌ها و علائم) با `Ctrl+F12`
- تغییر چرخشی وضعیت حروف لاتین (UPPERCASE → lowercase → Title Case) با `Shift+F12`
- تبدیل خودکار عدد به حروف فارسی و تومان (تایپ `1250000/w`، `5000000/t`، `1250000/s` و دستور CLI `words`)
- بازخورد صوتی ملایم هنگام تغییر زبان صفحه‌کلید (صدای زیر برای انگلیسی و صدای بم برای فارسی)
- تاریخچه کلیپ‌بورد در محل نشانگر (`Alt+V`) با امکان چسباندن سریع با شماره‌های ۱ تا ۵
- ماشین‌حساب ریاضی درون‌خطی هنگام تایپ با فشردن کلید `=` (مانند `1200*1.09=` یا با اعداد فارسی `۱۲*۵=`)
- درج تاریخ روز هجری شمسی و زمان با ماکروهای داینامیک (`/today`، `/shamsi`، `/تاریخ`، `/time`، `/uuid`)
- واژه‌نامه شخصی کاربر (`user_words.txt`) برای یادگیری اصطلاحات، نام‌ها و کلمات خاص کاربر
- پیشنهاد تکمیل کلمه نزدیک نشانگر (با واژه‌نامه بیش از ۱۳۰۰ کلمه پرکاربرد و یادگیری مستمر)
- اصلاح خودکار امن و کلمات اختصاری (Snippets) شخصی‌سازی‌شده
- نرمال‌سازی حروف عربی/فارسی و تبدیل اعداد فارسی و انگلیسی (ابزار CLI)
- پنجره تنظیمات تب‌بندی شده مدرن، ضبط کلیدهای میانبر، منوی Tray، اجرای خودکار با ویندوز و مدیریت برنامه‌های مستثنی

### راهنمای نصب و به‌روزرسانی (فارسی)

برنامهٔ روان از سه روش در دسترس است:

1. **فایل نصب‌کننده ویندوز (`Ravaan-Setup-x.y.z.exe`) — روش پیشنهادی:**
   - نصب اختصاصی کاربر (Per-User) بدون نیاز به دسترسی ادمین (Administrator/UAC).
   - مسیر نصب در `%LOCALAPPDATA%\Programs\Ravaan`.
   - ایزولاسیون کامل داده‌ها: برنامه به جز پوشهٔ `%APPDATA%\Ravan` در هیچ کجای دیسک فایلی ذخیره نمی‌کند (مستندات امنیتی کامل در [SECURITY.md](SECURITY.md)).
   - ایجاد خودکار میانبر منوی استارت و امکان فعال‌سازی اجرای خودکار هنگام روشن شدن ویندوز.
   - ثبت خودکار پروتکل اینترنتی `ravan://` جهت باز کردن سریع بخش‌ها و پیوندهای مستقیم.
   - حذف کامل و امن (Uninstall) بدون دست‌خوردن تنظیمات، واژگان شخصی و کلمات اختصاری در `%APPDATA%\Ravan`.
2. **نسخهٔ پرتابل بدون نیاز به نصب (`Ravaan-x.y.z-portable.zip`):**
   - بسته فشرده بدون نیاز به نصب شامل فایل اجرایی `Ravaan.exe`، مستندات و لایسنس.
   - فایل zip را از صفحهٔ انتشار گیت‌هاب دانلود کرده، در هر پوشه‌ای استخراج نموده و `Ravaan.exe` را مستقیماً اجرا کنید.
3. **نصب از سورس کد (محیط توسعه):**
   ```bash
   git clone https://github.com/mohsen-niksirat/Ravaan.git
   cd Ravaan
   pip install -e .[dev]
   python -m ravan
   ```
4. **به‌روزرسانی خودکار درون‌برنامه‌ای:**
   - برنامه به‌صورت خودکار یا از طریق منوی Tray (گزینهٔ Check for updates…) نسخه‌های جدید را بررسی می‌کند.
   - در صورت وجود نسخهٔ جدید، بالن اعلانی همراه با خلاصهٔ تغییرات نمایش داده می‌شود و با کلیک روی «دریافت و نصب»، فایل نصبی جدید دانلود و جایگزین می‌شود.

## Known limitations

- Elevated (admin) apps may block UIA / injection unless Ravan also runs elevated.
- Prediction dictionaries ship as curated samples; enlarge under `ravan/core/dict.py` or load external lists later.
- Overlay uses Tk with `WS_EX_NOACTIVATE` best-effort; some apps may still flicker focus rarely.
- UIA caret path is best-effort; fallback is `GetGUIThreadInfo` then mouse cursor.

## License

MIT

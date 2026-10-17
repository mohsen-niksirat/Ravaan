# Ravan (روان)

Windows typing assistant for bilingual Persian/English typists.

Helps with keyboard-language awareness, wrong-layout conversion, autocomplete, autocorrect, and text snippets — in any app.

## Features

| Milestone | Feature | Hotkey (default) |
|-----------|---------|------------------|
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

## Tests

```bash
pytest
```

## Architecture

```
ravan/
  core/       # config, layout map, dictionary, predictor, snippets, sync, updater, text_stats
  platform/   # Win32 hook, language, caret (UIA), SendInput, focus, single-instance, startup
  ui/         # overlay, tray, settings window, stats popup, window picker, app loop
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

## Known limitations

- Elevated (admin) apps may block UIA / injection unless Ravan also runs elevated.
- Prediction dictionaries ship as curated samples; enlarge under `ravan/core/dict.py` or load external lists later.
- Overlay uses Tk with `WS_EX_NOACTIVATE` best-effort; some apps may still flicker focus rarely.
- UIA caret path is best-effort; fallback is `GetGUIThreadInfo` then mouse cursor.

## License

MIT

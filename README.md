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
| M14 | Settings window, tray menu, startup, exclusions | tray → Settings… |
| M15 | External UTF-8 dictionary (12,500+ words) & adaptive boost | automatic learning |

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

### How to pick a suggestion

1. Type at least **2 letters** in Notepad (or any text field), e.g. `pro`
2. A popup appears near the caret with numbered candidates
3. Choose one:
   - **↑ / ↓** — move highlight
   - **Enter** or **Tab** — insert the highlighted word
   - **1 … 5** — jump-insert that row
   - **Esc** — close without inserting

### Autocorrect (Safe Mode & Language Intelligence)

- **Safe Guard**: Autocorrect only fires when the typed word is **not** already a valid dictionary word.
- **Bilingual Awareness**: Strictly tracks the active layout hook so Persian and English words are never cross-corrected or mangled.
- **Persian Confusable Typos**: Automatically resolves Arabic/Persian confusable keys (`ي/ی`, `ك/ک`, `ة/ه`, `ة/ت`) with dictionary validation.
- **Undo Autocorrect**: Made a mistake or wanted the exact typed typo? Press `Ctrl+Shift+Z` or simply tap `Backspace` immediately to instantly revert to what you typed.
- **Punctuation Spacing**: Automatically strips accidental spaces preceding punctuation marks (`.` `,` `!` `?` `:` `;` `؛` `،` `؟`).

### Snippets 2.0 (Multi-line, Cursor Placement, Math & Date Macros)

- **Dedicated Snippet Editor**: Access via **tray → Snippets…** or **Settings → Open Snippet Editor…** featuring a live expansion preview, search filter, and quick placeholder buttons.
- **Multi-line Templates**: Create rich multi-line expansions (code boilerplate, email templates, addresses, standard notes).
- **Cursor Placement (`$0` or `{{cursor}}`)**: Position the typing cursor anywhere inside the inserted template (e.g. `console.log($0);` places the caret inside the parentheses).
- **Extended Date Macros**:
  - `{{year}}`, `{{month}}`, `{{day}}`, `{{weekday}}`, `{{hafteh}}`, `{{gregorian}}`
  - `{{yesterday}}`, `{{tomorrow}}`, `{{time_sec}}`, `{{timestamp}}`
- **Embedded Math & Calculations**:
  - `{{calc: 100 * 1.09}}` → `109`
  - `{{math: (50 + 30) * 2}}` → `160`
  - `{{calc: ۱۲ * ۵}}` → `۶۰` (supports Persian digits)
- **JSON Import / Export**: Backup, restore, and share snippet libraries with 1-click JSON import (merge or replace) and export.
- **Excluded Apps Safety**: Snippet triggers are completely disabled inside excluded applications (password managers, games, terminal emulators).

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
- **Settings…** — hotkeys, toggles, snippets, excluded apps detector, startup
- **Diagnostics…** — live status inspector (hook state, caret source, active app, last 50 events, copy markdown report)
- **Word prediction** — toggle on/off (persisted)
- **Quit**

System tray icon → Quit to exit. Logs: `%APPDATA%\Ravan\logs\ravan.log` (capped with automatic 2MB log rotation and 3 backups).
Config: `%APPDATA%\Ravan\config.json`

## CLI diagnostics

```bash
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
  core/       # config, layout map, dictionary, predictor, snippets, journal
  platform/   # Win32 hook, language, caret (UIA), SendInput, focus, single-instance, startup
  ui/         # overlay, tray, settings window, app loop
```

## فارسی

**روان** یک دستیار تایپ هوشمند و سبک برای ویندوز است:

- نمایش زبان صفحه‌کلید (EN / فا) کنار نشانگر متن هنگام تغییر چیدمان (یا با `Alt+L`)
- تبدیل چیدمان متن انتخاب‌شده یا آخرین کلمه تایپ شده بین فارسی و انگلیسی با `F12`
  مثال: `o,vn` → `خورد` یا انتخاب یک پاراگراف و زدن `F12`
- نیم‌فاصله‌گذاری هوشمند فارسی (ZWNJ): اتصال خودکار «می/نمی» و پسوندهای «ها/تر/ترین/مند/شناس» یا درج با `Shift+Space`
- نرمال‌سازی درجا و پاکسازی متن فارسی (اصلاح «ي» و «ك»، نیم‌فاصله‌ها و علائم) با `Ctrl+F12`
- تغییر چرخشی وضعیت حروف لاتین (UPPERCASE → lowercase → Title Case) با `Shift+F12`
- تبدیل خودکار عدد به حروف فارسی و تومان (تایپ `1250000/w`، `5000000/t`، `1250000/s` و دستور CLI `words`)
- بازخورد صوتی ملایم هنگام تغییر زبان صفحه‌کلید (صدای زیر برای انگلیسی و صدای بم برای فارسی)
- تاریخچه کلیپ‌بورد در محل نشانگر (`Alt+V`) با امکان چسباندن سریع با شماره‌های ۱ تا ۵
- ماشین‌حساب ریاضی درون‌خطی هنگام تایپ با فشردن کلید `=` (مانند `1200*1.09=` یا با اعداد فارسی `۱۲*۵=`)
- درج تاریخ روز هجری شمسی و زمان با ماکروهای داینامیک (`/today`، `/shamsi`، `/تاریخ`، `/time`، `/uuid`)
- واژه‌نامه شخصی کاربر (`user_words.txt`) برای یادگیری اصطلاحات، نام‌ها و کلمات خاص کاربر
- پیشنهاد تکمیل کلمه نزدیک نشانگر (با واژه‌نامه بیش از ۱۳۰۰ کلمه پرکاربرد)
- اصلاح خودکار امن و کلمات اختصاری (Snippets) شخصی‌سازی‌شده
- نرمال‌سازی حروف عربی/فارسی و تبدیل اعداد فارسی و انگلیسی (ابزار CLI)
- پنجره تنظیمات کامل، منوی Tray، اجرای خودکار با ویندوز و مدیریت برنامه‌های مستثنی

## Known limitations

- Elevated (admin) apps may block UIA / injection unless Ravan also runs elevated.
- Prediction dictionaries ship as curated samples; enlarge under `ravan/core/dict.py` or load external lists later.
- Overlay uses Tk with `WS_EX_NOACTIVATE` best-effort; some apps may still flicker focus rarely.
- UIA caret path is best-effort; fallback is `GetGUIThreadInfo` then mouse cursor.

## License

MIT

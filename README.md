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
| M7 | Persian/Arabic text & number normalization | CLI `norm` & `num` |
| M8 | Settings window, tray menu, startup, exclusions | tray → Settings… |

### Convert Selection or Last Word (`F12`)

- Select text anywhere and press `F12` to convert between Persian and English keyboard layouts in place.
- If no text is selected, automatically converts the last word you typed.

### Smart Persian Half-Space (ZWNJ / نیم‌فاصله)

- Automatically converts prefixes like `می ` and `نمی ` to `می‌` and `نمی‌`.
- Automatically attaches plural/comparative suffixes like `کتاب ها` → `کتاب‌ها`, `سریع تر` → `سریع‌تر`.
- Press `Shift+Space` anytime to insert an explicit zero-width non-joiner (`\u200c`).

### Caret Clipboard History (`Alt+V`)

- Press `Alt+V` to open a quick paste popup right next to your active cursor.
- Browse recent clipboard items with **↑ / ↓**, press **Enter** or **1–5** to instantly paste into the active window.

### Persian / Arabic Normalizer & Numbers

CLI utilities for cleaning and standardizing text:
```bash
python -m ravan.cli num 12345        # Output: ۱۲۳۴۵
python -m ravan.cli num ۱۲۳۴۵ --to en # Output: 12345
python -m ravan.cli norm "ي ك ٪"     # Output: "ی ک ٪" (standardizes Arabic chars & spacing)
```

### How to pick a suggestion

1. Type at least **2 letters** in Notepad (or any text field), e.g. `pro`
2. A popup appears near the caret with numbered candidates
3. Choose one:
   - **↑ / ↓** — move highlight
   - **Enter** or **Tab** — insert the highlighted word
   - **1 … 5** — jump-insert that row
   - **Esc** — close without inserting

### Autocorrect (safe mode)

Autocorrect only fires when the typed word is **not** already a dictionary word,
the candidate is 1–2 edits away (Damerau-Levenshtein, so `teh → the` works),
and the candidate is far more frequent. It never rewrites valid words.

### Snippets

Edit in **tray → Settings…**, e.g. `@@ => you@example.com`.
Type the trigger, then space/enter/punctuation → it expands.

## Requirements

- Windows 10/11
- Python 3.10+

## Install

```bash
cd Ravaan
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Run

**Easiest:** double-click `run_ravan.bat` (no console window).

**Command Prompt (cmd):**
```bat
cd /d "C:\Users\MOHSEN\Desktop\Github Projects\Ravaan"
set PYTHONPATH=%CD%
python -m ravan
```

**PowerShell:**
```powershell
cd "C:\Users\MOHSEN\Desktop\Github Projects\Ravaan"
$env:PYTHONPATH = "$PWD"
python -m ravan
```

If the package is already installed (`pip install -e .`), just `python -m ravan`.

Single-instance enforced — running it twice just exits the second copy.

### Tray menu

- **Show language (Alt+L)** — show the language chip now
- **Settings…** — hotkeys, toggles, snippets, excluded apps, startup
- **Word prediction** — toggle on/off (persisted)
- **Quit**

System tray icon → Quit to exit. Logs: `%APPDATA%\Ravan\logs\ravan.log`
Config: `%APPDATA%\Ravan\config.json`

## CLI diagnostics

```bash
python -m ravan.cli lang          # current keyboard language
python -m ravan.cli caret         # caret / cursor position
python -m ravan.cli convert hjvfd # convert a word EN↔FA layout
python -m ravan.cli convert "o,vn"
python -m ravan.cli predict pro   # show prediction candidates
python -m ravan.cli inject "hello از روان"  # inject text into the focused field (diagnostic)
python -m ravan.cli hook -t 5     # print raw captured hook events
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
- تاریخچه کلیپ‌بورد در محل نشانگر (Alt+V) با امکان چسباندن سریع با شماره‌های ۱ تا ۵
- پیشنهاد تکمیل کلمه نزدیک نشانگر (با واژه‌نامه گسترش‌یافته بیش از ۱۳۰۰ کلمه پرکاربرد)
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

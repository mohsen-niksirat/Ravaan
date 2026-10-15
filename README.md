# Ravan (روان)

Windows typing assistant for bilingual Persian/English typists.

Helps with keyboard-language awareness, wrong-layout conversion, autocomplete, autocorrect, and text snippets — in any app.

## Features

| Milestone | Feature | Hotkey (default) |
|-----------|---------|------------------|
| M1 | Language chip near caret on layout switch | `Alt+L` on demand |
| M2 | Convert last word Persian ↔ English layout | `F12` |
| M3 | Word prediction popup | see below |
| M4 | Autocorrect + snippets | on word boundary |
| M5 | Settings window, tray menu, startup, exclusions | tray → Settings… |

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

**روان** یک دستیار تایپ برای ویندوز است:

- نمایش زبان صفحه‌کلید (EN / فا) کنار نشانگر متن
- تبدیل کلمهٔ آخر بین چیدمان فارسی و انگلیسی با `F12`
  مثال: `o,vn` → `خورد`
- پیشنهاد تکمیل کلمه نزدیک caret
- اصلاح خودکار امن (فقط کلمه‌های غلط اصلاح می‌شوند) و snippetهای کاربر
- پنجره تنظیمات، منوی tray، اجرای خودکار با ویندوز، لیست برنامه‌های مستثنی

## Known limitations

- Elevated (admin) apps may block UIA / injection unless Ravan also runs elevated.
- Prediction dictionaries ship as curated samples; enlarge under `ravan/core/dict.py` or load external lists later.
- Overlay uses Tk with `WS_EX_NOACTIVATE` best-effort; some apps may still flicker focus rarely.
- UIA caret path is best-effort; fallback is `GetGUIThreadInfo` then mouse cursor.

## License

MIT

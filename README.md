# Ravaan (روان) — Windows Bilingual Typing Assistant

> **Intelligent, privacy-first, bilingual Persian/English typing assistant for Windows with zero telemetry.**  
> دستیار هوشمند، بومی، و کاملاً امن تایپ دوزبانه فارسی و انگلیسی در ویندوز.

[![CI Status](https://github.com/mohsen-niksirat/Ravaan/actions/workflows/ci.yml/badge.svg)](https://github.com/mohsen-niksirat/Ravaan/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/mohsen-niksirat/Ravaan?include_prereleases&label=release&color=blue)](https://github.com/mohsen-niksirat/Ravaan/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078d4.svg)](https://microsoft.com/windows)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![Zero Telemetry](https://img.shields.io/badge/Telemetry-0%25%20(Local%20Only)-success.svg)](docs/SECURITY_FAQ.md)
[![Winget](https://img.shields.io/badge/Winget-MohsenNiksirat.Ravaan-blue)](packaging/winget/)
[![Persian Docs](https://img.shields.io/badge/%D8%B1%D8%A7%D9%87%D9%86%D9%85%D8%A7%DB%8C%20%D9%81%D8%A7%D8%B1%D8%B3%DB%8C-README.fa.md-green)](README.fa.md)

---

## Highlights

- ⚡ **Wrong Keyboard Layout Auto-Fix:** Automatically converts mistakenly typed text between Persian and English (e.g. `sghl` $\leftrightarrow$ `سلام`) as soon as you press space or punctuation.
- ✍️ **Persian Typography & ZWNJ (نیم‌فاصله):** Automatic normalization of Arabic characters (`ي`/`ك` $\to$ `ی`/`ک`) and intelligent zero-width non-joiner placement for prefixes (`می‌`, `نمی‌`) and suffixes (`‌ها`, `‌تر`, `‌ترین`, `‌مند`).
- 🔤 **Finglish Phonetic Typing:** Converts Latin transliteration into canonical Persian (`salam` $\to$ `سلام`, `khosh amadid` $\to$ `خوش آمدید`) using a 162k+ Persian lexicon trie.
- 🚀 **Text Snippets & Expansions:** Type shortcuts like `;em` to instantly expand your email or `;date` / `;jdate` for Gregorian / Jalali dates.
- 🧮 **Inline Math Calculator:** Evaluate expressions directly in any text box by typing `125*8=` $\to$ `1000`.
- 🛡️ **Zero Telemetry & Local-Only Privacy:** Ephemeral RAM buffers (max 32 characters), no keystroke logging to disk, and no background outbound network connections.
- 📦 **Modern Windows Packaging:** Available via **Winget**, **Scoop**, **Chocolatey**, Inno Setup per-user installer, or standalone Portable ZIP.

[Explore Interactive Visual Demos](docs/DEMO.md) • [Security & Privacy FAQ](docs/SECURITY_FAQ.md) • [SmartScreen Guide](docs/SMARTSCREEN.md) • [Contributing](CONTRIBUTING.md)

---

## Installation

### 1. Windows Package Managers

#### Winget (Windows Package Manager)
```powershell
winget install MohsenNiksirat.Ravaan
```

#### Scoop
```powershell
scoop install https://raw.githubusercontent.com/mohsen-niksirat/Ravaan/main/packaging/scoop/ravaan.json
```

#### Chocolatey
```powershell
choco install ravaan
```

---

### 2. Windows Installer (`Ravaan-Setup-1.0.0.exe`)
Download the latest installer from [GitHub Releases](https://github.com/mohsen-niksirat/Ravaan/releases/latest).
- **Per-User Non-Admin Installation:** Installs into `{autopf}\Ravaan` without requiring UAC administrator prompts.
- **Data Preservation:** Keeps `%APPDATA%\Ravaan` intact across upgrades.
- **Clean Uninstall Option:** Prompts during uninstallation if you wish to permanently wipe personal data or keep it for future installs.
- *Note on SmartScreen:* If Windows Defender SmartScreen shows a warning on new releases, see our [SmartScreen Bypass Guide](docs/SMARTSCREEN.md).

---

### 3. Portable Archive (`Ravaan-Portable-1.0.0.zip`)
- Zero-installation standalone package containing `Ravaan.exe` and documentation.
- Extract anywhere and run immediately (great for USB drives and restricted environments).

---

### 4. From Source (Developers)
```powershell
git clone https://github.com/mohsen-niksirat/Ravaan.git
cd Ravaan
pip install -e .[dev]
python -m ravan
```

---

## Quick Keyboard Shortcuts

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| `Space` / `Punctuation` | **Auto-Fix** | Auto-corrects wrong layout or typos on word boundaries |
| `Backspace` (< 4.0s) | **Instant Undo** | Immediately reverts auto-fixed or transliterated word |
| `Ctrl+Shift+Z` | **Global Undo** | Reverts the last layout or text transformation |
| `F12` | **Manual Layout Switch** | Converts selected text or last typed word (EN $\leftrightarrow$ FA) |
| `Shift+Space` | **Manual ZWNJ** | Inserts standard Persian Zero-Width Non-Joiner (نیم‌فاصله) |
| `Alt+V` | **Clipboard Ring** | Opens local clipboard history overlay |
| `Alt+S` | **Quick Text Stats** | Displays word count, reading time, and language breakdown |
| `Ctrl+F12` | **Persian Normalizer** | Cleans Arabic yeh/kaf and standardizes punctuation |
| `Shift+F12` | **Cycle Case** | Cycles Latin text between `lowercase`, `UPPERCASE`, and `Title Case` |
| `Alt+Shift+F` | **Toggle Finglish** | Enables / disables phonetic Finglish-to-Persian typing |

---

## Interactive Demos

Curious how Ravaan looks in action? Check out our [Interactive Demos & Walkthroughs](docs/DEMO.md) featuring:
- **Scenario 1:** Wrong Keyboard Layout Auto-Fix (`sghl` $\to$ `سلام`)
- **Scenario 2:** Persian Typography & ZWNJ Engine (`می روم` $\to$ `می‌روم`)
- **Scenario 3:** Text & Image Snippets (`;em` $\to$ `user@example.com`, `re:;d(\d+)` $\to$ `Day $1 report`, interactive forms `{{name}}`, `image:logo.png`, and per-app groups)
- **Scenario 4:** Finglish Phonetic Typing (`khosh` $\to$ `خوش`)
- **Scenario 5:** Inline Math Calculator (`125*8=` $\to$ `1000`)
- **Scenario 6:** Privacy Guard & Local-Only Architecture

---

## Security, Privacy & Verifiability

Ravaan is engineered with privacy as a foundational principle:
- **No Keystroke Logging:** Buffered characters exist only in volatile RAM (up to 32 characters) to analyze the immediate word. Flushed upon word delimiters or application switching.
- **Zero Telemetry:** No analytics, tracking pixels, or diagnostic telemetry sent over the internet.
- **Local-Only Storage:** User dictionaries and snippets reside strictly in `%APPDATA%\Ravaan`.
- **Credential Protection:** Cloud sync credentials are encrypted via Windows Data Protection API (DPAPI) and Windows Credential Manager.
- **Independent Auditing:** Read our [Security & Privacy FAQ](docs/SECURITY_FAQ.md) for step-by-step instructions on auditing network and disk activity with Process Monitor and Resource Monitor.

---

## Architecture Overview

```text
ravan/
  ├── core/       # Prediction trie, layout converter, translit transducer, ZWNJ normalizer, snippets
  ├── data/       # Persian lexicon (162k words), i18n catalogs (en.json, fa.json), icons
  ├── platform/   # Win32 LL hooks (SetWindowsHookExW), SendInput injection, UIA caret detection, DPAPI
  └── ui/         # Modern Tkinter overlays, system tray, wizard, settings, and diagnostics
```

---

## Contributing

We welcome contributions from the community!
- See [CONTRIBUTING.md](CONTRIBUTING.md) for local development setup, coding standards, and running tests.
- Report issues or request features using our [GitHub Issue Templates](https://github.com/mohsen-niksirat/Ravaan/issues/new/choose).
- Please adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## License

Ravaan is licensed under the [MIT License](LICENSE).  
Copyright (c) 2026 Mohsen Niksirat and Ravaan Contributors.

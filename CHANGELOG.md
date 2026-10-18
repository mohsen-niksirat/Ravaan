# Changelog

All notable changes to Ravaan (روان) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2026-10-18

### Added
- **Power-User Features (M22–M24)**:
  - **Inline Math v2**: full percentage arithmetic (`500+10%=` → `550`, `100*20%=` → `20`, `۵۰۰+۱۰٪=` → `۵۵۰`), explicit rounding macros (`10/3=2` → `3.33`), and instant currency formatting (`12000=t` → `12,000 تومان`, `120000=r` → `120,000 ریال`).
  - **Password Input Shield**: Automatic detection and suppression of math evaluation, autocorrect, and word prediction inside password fields across classic Win32 and UI Automation.
  - **Keystroke Macro Recorder (M23)**: Record arbitrary key sequences from System Tray or hotkey, stop with `Esc`, and save with custom snippet trigger (e.g. `//m1`) with optional delay preservation. Includes safety notices for elevated apps.
  - **Power Mode / Focus Typing (M24)**: Instant `Ctrl+Alt+P` toggle that suppresses all floating popups (predictions, language chip, text statistics) with dimmed tray icon and optional duration timer for distraction-free typing.
  - **CLI Backup & Migration**: `python -m ravan.cli export` archives all user configuration, custom vocabulary, and learned models into a single ZIP; `python -m ravan.cli import [--merge]` restores or merges profiles with automatic pre-import safety backups.
- **Installer, Auto-Update & Distribution**:
  - Inno Setup 6 installer (`Ravaan-Setup-0.7.0.exe`) for per-user non-admin installation with Start Menu and startup entries.
  - In-app updater (`ravan/core/updater.py`, `ravan/ui/update_dialog.py`) with changelog summaries, tray balloons, and one-click mutex handoff.
  - Windows deep linking via `ravan://` URL protocol (`ravan://settings`, `ravan://stats`, `ravan://snippet`).
- **Cloud Sync 2.0 & Settings Robustness**:
  - Generic WebDAV backend supporting Nextcloud and ownCloud.
  - Three-way dictionary union and interactive snippet conflict prompt.
  - Background sync polling with 15s burst debounce and offline backoff.
  - Config schema versioning (`schema_version: 2`) and corrupt config auto-recovery.
  - Settings window search box filter and per-tab reset to defaults.
- **Prediction Quality & Learning Engine v2**:
  - Trigram model with backoff smoothing and interpolation (> 80% top-3 accuracy).
  - Next-word multi-word sentence continuations (`[بعدی]`).
  - Learning engine v2 with half-life frequency decay and per-app vocabulary weighting.
  - Multi-word repeated F12 conversion and punctuation protection.
- **Full Bilingual UI Localization (fa / en)**:
  - Native Persian phrasing with correct half-spaces (نیم‌فاصله‌گذاری استاندارد).
  - Mirrored RTL layout for Persian UI with live language switching in Settings.

## [0.5.0] - 2026-10-18

### Added
- **Quick Text Stats (`Alt+S`)**:
  - Floating stats popup when text is selected across any Windows application.
  - Displays word count, character count (with and without whitespace), estimated reading time (~200 wpm), and Persian vs. English character percentage ratio.
  - Clean floating card design with instant `Esc` or click-outside dismissal.
- **Cloud Sync (GitHub Gist)**:
  - Opt-in synchronization for user custom dictionary (`user_words.txt`) and snippets via private GitHub Gists.
  - Automated timestamped local backups (`.bak`) before pulling or pushing remote changes.
  - Dedicated "Sync" tab in Settings UI with manual "Sync Now" button and optional background sync timer.
- **Snippets 2.0 Enhancements**:
  - Support for `|` pipe cursor placeholder in snippet replacement text (in addition to `$0` and `{{cursor}}`).
  - Added `{{clipboard}}` dynamic placeholder to embed system clipboard contents into expanded snippets.
  - Added per-snippet `enabled` toggle switch with JSON import/export preservation.
- **Interactive Window Picker**:
  - Modal dialog with a 3-second visual countdown allowing users to click or switch to any target window.
  - Automatically captures the process executable name or Win32 window class (`class:<name>`) and adds it to the excluded apps list.
- **Elevated Application Detection**:
  - Checks if the active foreground window runs with Administrator privileges while Ravaan runs as standard user.
  - Displays an elevation warning banner in Settings to clarify why keystroke injection may be blocked by Windows UIPI.
- **GitHub Release Update Checker**:
  - Query GitHub Releases API for new version tags.
  - Added `--version` and `--check-updates` flags to CLI.
  - Added "Check for updates…" option to the system tray context menu.
- **Modern Tabbed Settings UI**:
  - Redesigned into structured tabs: General, Hotkeys, Excluded Apps, Sync, and About.
  - Interactive "Record" buttons for customizing global hotkeys.

### Changed
- **Sub-500ms Startup Profiling**:
  - Prediction corpus files and user learning engine are lazy-loaded on the first keystroke rather than blocking UI startup.
  - Added startup phase timing metrics.
- **Low-Level Hook Latency Monitoring**:
  - Keyboard hook measures event dispatch latency and logs warnings if processing exceeds 5 ms.
- **Caret Detection Optimization**:
  - COM UIA instance cached across calls; caret bounding boxes cached with 30ms TTL.
  - Unresponsive or failing process IDs enter a 3-second cooldown to avoid repeated COM lag.
- **Logging Improvements**:
  - Increased log rotation threshold to 5 MB (with 3 backup files).
  - Added crash handler hook with unhandled exception dialog and direct "Open Logs Folder" action.
- **Strict Code Quality & Modular Architecture**:
  - Enforced strict < 400 LOC boundary across all project modules.
  - Separated concerns into companion modules (`settings_builder.py`, `settings_sync.py`, `stats_popup.py`, `window_picker.py`, `log_setup.py`, `focus.py`).

### Fixed
- Fixed Win32 hook mock compatibility in headless test runs.
- Fixed layout switch tracking during rapid consecutive keystrokes.
- Resolved all Ruff linting errors and formatting inconsistencies.
- Maintained 100% green test suite across 172 unit and integration tests.

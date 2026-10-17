# Changelog

All notable changes to Ravaan (روان) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

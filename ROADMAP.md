# Roadmap

## Completed (v1.0.0-rc1)

- **Phase 0: Release Engineering Pipeline & Pre-Release Hardening**
  - Multi-artifact GitHub Actions release workflow publishing both `Ravaan-1.0.0-rc1-portable.zip` and `Ravaan-Setup-1.0.0-rc1.exe`.
  - Windows binary release smoke check job downloading portable zip and executing `Ravaan.exe --check-updates --version` before publishing.
  - In-app updater hardened with pre-release channel awareness (stable users protected from `-rc` releases).
  - Bilingual release notes template (`docs/RELEASE_NOTES_TEMPLATE.md`) with automated SHA256 checksum tables, elevated app warnings, and migration guide.
  - Multi-flag CLI diagnostic execution support.
- **Phase 1: Security & Privacy Hardening**
  - Comprehensive `SECURITY.md` threat model documenting zero keystroke persistence and responsible disclosure.
  - Windows DPAPI credential encryption via ctypes for Gist tokens and WebDAV passwords in `config.json` with seamless migration.
  - Hardened clipboard history: automatic exclusion of password manager apps (1Password, Bitwarden, KeePass, etc.), regex token filtering, Shannon entropy heuristics, and 7-day auto-expiration.
  - WebDAV unencrypted HTTP warning on insecure configurations.
  - Hardened sandboxed `ravan://` deep link URL parser with action whitelisting, input sanitization, and fuzz resilience.
  - Keylogger-risk audit test verifying zero raw keystroke leaks in logs and aggregate-only learning profiles.
- **Phase 2: Real-World Windows QA Matrix**
  - Scripted diagnostics selftest (`python -m ravan.cli selftest`): in-app verification of WH_KEYBOARD_LL hook, UIA caret reachability, SendInput injection, clipboard round-trip, audio devices, DPAPI encryption, and dictionaries with PASS/FAIL report.
  - Multi-monitor & mixed-DPI popup clamping: per-monitor work area detection via `MonitorFromPoint` and `GetMonitorInfoW`, eliminating popup placement errors across multi-monitor and RDP sessions.
  - Elevated window degradation: single rate-limited tray alert per elevated session with zero repeated notification spam and complete injection suppression.
  - Custom caret fallback chain: robust handling of terminal canvas containers (VS Code), Excel cells, browser address bars, and Telegram/WhatsApp Desktop with container box filtering and cursor fallback.
  - Pre-seeded exclusion defaults: added 1Password, Bitwarden, KeePass, KeePassXC, Dashlane, LockApp, LogonUI, and CredentialUIBroker to default excluded apps.
  - Memory & latency soak test (`python -m ravan.cli soak`): synthetic typing loop verifying stable RSS (<30 MB peak vs 150 MB ceiling) and zero latency drift across 10,000 keystrokes.
- **Phase 3: UX Final Polish (v1.0 Face)**
  - Unified UI theme system (`ravan/ui/theme.py`): centralized palette tokens (dark, light, high-contrast), typography tokens (Vazirmatn / Segoe UI), and DWM rounded corners.
  - Prediction confidence meter: 4-level discrete confidence indicator (` `, `▂`, `▅`, `█`) per candidate row.
  - Text statistics popup unified with design tokens and multi-monitor work area clamping.
  - First-Run Onboarding Wizard (`ravan/ui/wizard.py`): friendly 20-second intro with live bilingual language picker and 5 hotkeys tour card.
  - System tray upgrades: multi-resolution crisp icon set with alpha channel, Quick Toggles submenu (Prediction, Autocorrect, Auto-ZWNJ, Power Mode) with live checkmarks, and "Pause for 10 min" toggle with auto-resume timer and visual pause badge.
  - Accessibility: High-contrast theme mode, complete keyboard navigation (`Ctrl+Tab`, `Ctrl+Shift+Tab`, `Escape`, `Ctrl+Return`), and screen-reader accessibility.
- **Phase 4: Data & Migration Completeness**
  - Data Manifest (`ravan/core/data_manifest.py`): single-source-of-truth registry for all user data files, schemas, privacy classifications, and aggregate disk usage summary (`get_storage_summary`).
  - Learning Profile Citable Artifact (`ravan/core/learning.py`): version 3 schema with statistical metadata headers (`total_words`, `total_bigrams`, `total_trigrams`, `apps_tracked`, `top_words`).
  - Cloud Sync for Learning Profile: optional, opt-in synchronization of aggregated typing profile across machines via both WebDAV and GitHub Gist.
  - Multi-version migration test suite (`tests/test_migration_fixtures.py`): verifying lossless migration from v0.4, v0.5, and v0.7 to v1.0 (schema 3).
  - Data & Privacy Documentation (`DATA.md`): file inventory, DPAPI encryption guarantees, zero-telemetry policy, and safe reset procedures.

## Completed (v0.7.0)

- **M30: Power-User Features: Math v2, Macro Recorder & Power Mode (Focus Typing)**
  - Inline Math v2: support percentages (`%` / `٪`), discount/markup (`500+10%`), rounding macros (`1200*1.09=2`), and currency formatting (`=t` Toman, `=r` Rial). Automatic suppression inside password fields.
  - Keystroke Macro Recorder: record key sequences until Esc, save with custom trigger (e.g. `//m1`), replay via snippet expansion, optional timing preservation, and clear warning about elevated/admin apps.
  - Power Mode / Focus Typing (`Ctrl+Alt+P`): one-touch toggle suppressing all popups with dimmed tray icon and optional duration timer.
  - CLI Profile Backup & Migration: `python -m ravan.cli export` and `python -m ravan.cli import [--merge]` for complete profile ZIP archives.
- **M29: Inno Setup Windows Installer & Auto-Update Engine**
  - Clean non-admin per-user installer (`Ravaan-Setup-0.7.0.exe`) with Start Menu shortcuts and optional startup entry.
  - In-app background update checker with changelog summary, non-intrusive tray balloon, and 1-click download/install with mutex handoff.
  - `ravan://` deep-linking URL protocol registration (`ravan://settings`, `ravan://stats`, `ravan://snippet`).
- **M28: Cloud Sync 2.0 & Settings Robustness**
  - Generic WebDAV backend (Nextcloud / ownCloud) alongside GitHub Gist.
  - Three-way dictionary merge and interactive snippet conflict prompt (keep local, remote, or both).
  - Background sync polling debounced after typing bursts with offline backoff.
  - Schema migration versioning and corrupt config auto-recovery.
  - Settings window search box filter and per-tab reset to defaults.
- **M27: Prediction Quality: Sentence Model & Learning Engine v2**
  - Trigram model with backoff smoothing and interpolation. Top-3 hit rate > 80% on held-out benchmarks (`python -m ravan.cli bench`).
  - Next-word multi-word sentence predictions.
  - Learning engine v2 with half-life frequency decay, per-app weighting, and profile export/import (`python -m ravan.cli learn`).
  - Layout conversion (F12) quality: mixed-direction support, punctuation protection, and repeated F12 multi-word expansion.
- **M26: Full Bilingual UI Localization (fa / en)**
  - 100% extraction of UI strings into `en.json` and `fa.json` with `t(key)` helper.
  - Native Persian phrasing with correct half-spaces (نیم‌فاصله‌گذاری درست).
  - RTL correctness for Persian UI (mirrored layout and right-aligned labels).
  - Live language switcher in Settings (Auto / English / فارسی).

---

## Completed (v0.5.0)

- **M25: Quick Text Statistics (Alt+S — Milestone M15)**
  - Instantly inspect word count, character count (with & without whitespace), estimated reading time, and Persian vs. English character percentage ratio for any selected text or current word across any Windows application.
  - Floating non-activating card with dark/light mode detection, DWM rounded corners, and auto-dismiss after 6 seconds or Esc.
- **M24: GitHub Gist Cloud Sync (Opt-in)**
  - Securely sync custom dictionary words (`user_words.txt`) and snippets (`snippets.json`) across PCs via a private GitHub Gist.
  - Dedicated "Sync" tab in Settings with token masking, manual Push/Pull controls, last-sync timestamp, and automated pre-sync local backups kept in `%APPDATA%\Ravan\backups\`.
- **M23: Snippets 2.0 Enhancements**
  - Added support for cursor placement marker `|` (in addition to `$0` and `{{cursor}}`).
  - Added `{{clipboard}}` expansion macro injecting current clipboard text into templates.
  - Added per-snippet enable/disable toggle with persistent JSON import/export.
- **M22: Performance, Profiling & Update Checker**
  - Lazy-loading for prediction tables and dictionaries reducing app startup time to ~500 ms (< 1.5s target) and hook latency to < 0.1 ms median.
  - Added `--version` and `--check-updates` CLI flags querying the GitHub Releases API.
  - Added manual "Check for updates…" tray menu item with non-intrusive notifications and one-click release opening.
- **M21: Reliability & System Compatibility**
  - Elevated app awareness: detects when focused window runs as admin and warns user once via tray notification regarding UIPI isolation.
  - Caret detection fallback chain optimization with 30ms TTL caching and failed UIA PID cooldown (3s) to prevent keystroke lag.
  - Window class exclusion matching (support for `class:ClassName`) and interactive "Pick Window" modal with 3-second delay capture and open window list.
  - Log rotation upgraded to 5 MB with 3 backup rotations and "Open logs folder" tray item.
  - Global crash handler writing full tracebacks and the last 50 log lines to `%APPDATA%\Ravan\crash\`.
- **M20: UI/UX Modernization & Live Hotkey Rebinding**
  - Native Windows 11 rounded corners via DWM attribute 33 (`DWMWCP_ROUND`), subtle dark/light border, and Tk DPI scaling.
  - Windows system theme auto-detection (dark/light) with manual override in Settings.
  - Full-featured Settings window reorganized into clean tabs (General, Prediction, Hotkeys, Exclusions, Snippets, Sync, About).
  - Interactive live key combination capture for hotkey rebinding with duplicate hotkey conflict validation.
  - Clipboard history ring buffer expanded to 50 items with item pinning (favorites) and JSON persistence across restarts (`Alt+V`).
  - First-run onboarding tooltip introducing top 5 essential shortcuts.
- **M19: Trigram/Bigram N-Gram Prediction & Personal Adaptive Learning**
  - High-frequency English corpus expanded to 2,760 words and Persian corpus to 3,000+ words.
  - Fast $O(\log N)$ bisect prefix matching with sub-15ms response latency.
  - Trigram and bigram transition engine tracking personal word pairings.
  - Autocorrect modes (`safe`, `normal`, `off`) and persistent ignored words set.

---

## Completed (v0.4.0 and earlier)

- **M18: Continuous Android-Style Prediction, Atomic Injection & User Typing Style Learning Engine**
- **M17: Code Quality Pass (< 400 LOC strict rule & Ruff 100% clean)**
- **M16: Snippets Editor with Live Preview & Math Placeholders**
- **M15: External UTF-8 Dictionary Loading & Hierarchical Ranking**
- **M14: PyInstaller standalone distribution packaging (`Ravaan.exe`)**
- **M13: Number to Persian words converter, Rial-to-Toman calculator, and thousands separator formatting**
- **M12: Keyboard layout audio feedback (distinct gentle tones for Persian and English)**
- **M11: Dynamic snippets with Persian Jalali (Shamsi) calendar date/time expander**
- **M10: In-place text transformation (case cycling with `Shift+F12` and Persian normalizer with `Ctrl+F12`)**
- **M9: Inline quick math calculator on `=` trigger**
- **M8: User custom dictionary (`user_words.txt`) & priority merging**
- **M7: Selection layout conversion**
- **M6: Smart Persian half-space (ZWNJ): prefix/suffix auto-attachment + `Shift+Space` hotkey**
- **M5: Caret clipboard history ring buffer popup (`Alt+V`)**
- **M4: Persian / Arabic text and number normalization**
- **M3: Safe autocorrect & confusable typo normalization**
- **M2: Tray menu with prediction toggle + notifications**
- **M1: Single-instance guard, launch-at-startup, per-app exclusions, real UIA caret**

---

## Future Horizon

1. **Native Inno Setup Windows Installer**
   - Provide an optional graphical setup wizard `.exe` with Start Menu shortcuts and automatic uninstaller.
2. **Global Hotstring Engine**
   - Instant multi-character hotstring triggers without requiring word delimiters.
3. **Multi-Monitor Caret Coordinate Mapping**
   - Enhanced virtual screen multi-DPI per-monitor coordinate translations for heterogeneous monitor layouts.

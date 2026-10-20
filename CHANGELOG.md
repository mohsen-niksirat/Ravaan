# Changelog

All notable changes to Ravaan (روان) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - Phase 5

### Added
- Resilient low-level keyboard hook (`WH_KEYBOARD_LL`) architecture in `ravan/platform/hook.py`:
  - Thread liveness checking (`is_alive()`) and auto-recovery health checking (`check_health()`).
  - Thread-safe restart and reinstallation (`reinstall()`) with mutex guarding.
  - Non-blocking event emission (`_emit()`): drops oldest event on queue overflow to guarantee the Windows hook thread never blocks or introduces keyboard lag.
- Watchdog background monitoring in `ravan/ui/app_polling.py` (`_poll_hook_health()`):
  - Monotonic clock-jump detection (> 4.0s) to instantly recover state and re-verify hook liveness after system sleep/resume or lock-screen transitions.
  - Periodic 3.0s health checks ensuring automatic hook reinstallation if Windows silently unhooks `WH_KEYBOARD_LL`.
- Unit tests for hook lifecycle, non-blocking queue overflow, and sleep clock-jump recovery in `tests/test_hook_resilience.py`.

## [Unreleased] - Phase 4

### Added
- Windows Credential Manager integration in `ravan/core/crypto.py` via native `advapi32.dll` (`CredWriteW`, `CredReadW`, `CredDeleteW`, `CredFree`) with zero external dependencies and safe in-memory fallback for non-Windows platforms.
- Credential targets for sensitive tokens: `Ravaan/GitHubGistToken`, `Ravaan/WebDAVPassword`, and `Ravaan/AIApiKey`.
- Automatic migration in `ravan/core/config.py`: plaintext and legacy DPAPI tokens in `config.json` are transparently migrated into Windows Credential Manager and replaced with sentinel markers (`wincred:<target>`), eliminating plaintext secret storage on disk.
- Direct round-trip and auto-migration unit tests in `tests/test_crypto.py`.
- Windows DPAPI encryption at rest for user learning profile (`user_learning.json`) in `ravan/core/learning.py`, preventing unauthorized inspection of learned typing vocabulary on disk, with transparent legacy plaintext migration.
- `clear_learned_data()` method in `UserLearningEngine` to completely reset learned vocabulary, n-grams, and per-app weights to factory defaults.
- Automated tests for DPAPI encryption at rest, legacy import, clear learned data, and learning disabled toggle in `tests/test_learning.py`.
- In-app Privacy & Data Management controls in Settings:
  - "Adaptive typing learning" toggle (`learning_enabled`) to enable/disable user vocabulary tracking on demand.
  - "Export my data (.json)" button to export learned words and style profiles to a user-selected JSON file.
  - "Clear learned data" button with confirmation prompt to reset learned vocabulary and n-grams.
- Prominent privacy guarantee banner in Cloud Sync settings reassuring users in both Persian and English that typed text, keystrokes, and clipboard data never leave their computer.
- Full localization in both `fa.json` and `en.json` with correct Persian ZWNJ typography and RTL layout.
- Auto-update security and integrity enforcement in `ravan/core/updater.py`:
  - Strict HTTPS-only enforcement: insecure `http://` or non-HTTPS download URLs are rejected immediately with `ValueError`.
  - SHA-256 hash calculation and verification during download; mismatched checksums abort installation and automatically purge the downloaded binary.
  - Windows PE executable binary header validation (`b"MZ"` magic signature check) prior to launching detached setup process.
  - Automated SHA256 extraction from release notes or checksum assets via `extract_sha256_for_installer`.
  - Unit tests covering HTTPS rejection, valid/invalid SHA256 checksums, and PE header checks in `tests/test_installer_and_updater.py`.
- Comprehensive update to `DATA.md` and `SECURITY.md`:
  - Updated data manifests, Windows Credential Manager storage, and DPAPI at rest documentation.
  - Corrected legacy path references to canonical `%APPDATA%\Ravaan`.
  - Added plain-language Persian privacy summary (*«خلاصهٔ حریم خصوصی به زبان ساده — چه چیزی ذخیره می‌شود، چه چیزی نمی‌شود»*).
  - Documented third-party dependency vulnerability audit (0 vulnerabilities in `comtypes`, `Pillow`, `pystray`).

## [Unreleased] - Phase 3

### Added
- Data-driven Persian ZWNJ rules file `ravan/data/zwnj_rules.json` specifying verbal prefixes (`می`, `نمی`, `بی`), plural/comparative suffixes (`ها`, `های`, `تر`, `ترین`, etc.), personal/possessive endings (`ام`, `ای`, `ایم`, `اید`, `اند`, `مان`, `تان`, `شان`), compound words (`گفت‌وگو`, `سیستم‌عامل`, `پیش‌فرض`), and exception lists (`مینا`, `بیمار`, `شاهنامه`, `روزنامه`).
- Context-aware Persian punctuation engine (`normalize_persian_punctuation` in `ravan/core/normalizer.py`):
  - Persian punctuation conversion (`?` $\to$ `؟`, `,` $\to$ `،`, `;` $\to$ `؛`) strictly in Persian context while protecting numbers, HTML entities, and English text.
  - Smart quotes conversion: straight and curly quotes (`"..."` / `“...”`) $\to$ Persian guillemets (`«...»`) when containing Persian text.
  - Typographic ellipsis conversion: `...` $\to$ `…` (horizontal ellipsis U+2026).
  - Typographic bracket/quote spacing: space outside, zero space inside (`( متن )` $\to$ `(متن)`, `« سخن »` $\to$ `«سخن»`).
  - Spacing normalization around punctuation: zero space before, exactly one space after, preserving times (`10:30`), decimals (`3.14`), URLs, and emails.
- Contextual digit formatting engine (`normalize_contextual_digits`):
  - Intelligent `"auto"` mode formatting digits inside Persian prose as Persian digits (`۰-۹`) while preserving Latin digits in URLs, emails, file paths, IP addresses, versions, and code tokens.
  - Added `digit_mode` setting to `Config` (`"auto"` | `"fa"` | `"en"` | `"keep"`).
- "Clean Pasted Text" / "پاک‌سازی متن کلیپ‌بورد" feature (`clean_pasted_text`):
  - Normalizes clipboard text with Arabic character unification, ZWNJ, punctuation, smart quotes, and contextual digits.
  - Automatically preserves markdown code blocks (```` ```...``` ````) and inline code (`` `...` ``) completely untouched.
  - Accessible via tray menu and default hotkey `Ctrl+Shift+F12` with toast feedback and localized strings (`fa.json`, `en.json`).
- Golden-file test suite (`tests/data/typography_golden_cases.json` and `tests/test_normalizer.py::test_typography_golden_cases`) enforcing 100% fidelity on complex mixed Persian/English, code, and punctuation fixtures.

## [Unreleased] - Phase 2

### Added
- Conservative, statistical confidence scoring (`score_confidence`) in `AutoFixEngine.detect` utilizing dictionary presence, frequency rank tiers, consonant/vowel clusters, and length heuristics.
- Mid-word wrong-layout conversion (`_maybe_autofix_mid_word` and `mid_word=True` in `AutoFixEngine`) with prefix completion guarding (`active_dict.completions()`) ensuring active typing is never interrupted if valid words can be completed in the active layout.
- Default suppression for code editors and terminals (`DEFAULT_CODE_AND_TERMINAL_APPS` covering VS Code, Cursor, PyCharm, IntelliJ, Sublime Text, Windows Terminal, PowerShell, CMD, Bash, Git Bash, Mintty, ConEmu, WezTerm, Alacritty, Kitty).
- Learning from user undos: auto-fix pairs reverted twice (`count >= 2`) via Backspace or `Ctrl+Shift+Z` are permanently added to the user's blacklist (`autofix_blacklist`) and saved to `%APPDATA%\Ravaan\config.json`.
- Automated Phase 2 benchmark script `scripts/check_layout_autodetect.py` and automated quality gate `tests/test_layout_autodetect.py` enforcing False Positive Rate < 0.1%, Precision >= 98%, and Recall >= 90%.

### Changed
- Refined instant undo from Backspace (`_undo_last_correction_from_backspace`) and global undo hotkey (`_undo_last_correction`) to properly restore original text without leaving dangling delimiters or duplicate deletions.
- Isolated test configurations across autofix unit tests to prevent cross-test state leakage to user AppData.

## [Unreleased] - Phase 1

### Added
- Large, license-checked Persian dictionary (162,937 words with frequency weights) and English dictionary (46,827 words with frequency weights) sourced from Hermit Dave FrequencyWords (MIT License) and merged with Ravaan's curated Persian lexicon.
- High-performance binary dictionary compiler `scripts/compile_dictionary.py` and `compile_dict_binary` generating `RVN2` format with dual-offset index tables (alphabetical and rank-ordered).
- Memory-mapped zero-heap dictionary sequence (`_MmapEntriesSequence`) in `ravan/core/dict.py` achieving < 4 ms load time and reducing idle RAM from 30.4 MB to 18.5 MB.
- Created `THIRD_PARTY_LICENSES.md` and added Section 7 to `DATA.md` documenting lexicon licenses and binary index architecture.
- Autocorrect safe token screening (`is_safe_autocorrect_token`) filtering digits, URLs, emails, @mentions, hashtags, file paths, code identifiers, camelCase, snake_case, and extensive programming keywords (`_CODE_KEYWORDS`).
- Persian ZWNJ morphological decomposition in `Dictionary.contains` and `Dictionary.get` handling verbal prefixes (`می‌`, `نمی‌`), suffixes (`‌ها`, `‌های`, `‌ترین`, `‌ام`, `‌اش`, etc.), and compound words (`دوزبانه`, `متن‌باز`, `سیستم‌عامل`).
- Realistic false-positive test corpus `tests/data/false_positive_corpus.json` covering formal Persian, colloquial Persian, mixed Persian/English, and code syntax.
- Automated false-positive benchmark `scripts/check_false_positives.py` and CI quality gate `tests/test_false_positives.py` strictly enforcing False Positive Rate < 0.1% (achieved 0.000% error rate).
- Automated tests verifying complete password-field and excluded-app suppression across keyboard hook handling, text predictions, autofix, layout switching, and clipboard history (`tests/test_suppression.py`).

### Changed
- Reassigned default layout conversion hotkey to `Pause` (avoiding F12 conflicts with Chrome/Edge DevTools and VS Code). Added `VK_PAUSE` mapping in `ravan/platform/keys.py` and `ravan/platform/winapi.py`.
- Reassigned default quick text statistics hotkey to `Ctrl+Alt+S` (avoiding Alt+S conflicts in office and graphics applications).
- Added duplicate hotkey detection in Settings to prevent configuration conflicts.
- Updated English and Persian localizations (`en.json`, `fa.json`) and onboarding hints to reflect new default hotkeys.
- Enforced safe autocorrect invariants: 3-letter tokens cannot expand via edit distance; autocorrect never strips ZWNJ from user-typed text; ambiguous corrections require confidence margin.
- Enhanced excluded application matching in `Config.is_excluded` to support extension-agnostic process matching (e.g. `keepass` matching `keepass.exe`).

## [Unreleased] - Phase 0

### Added
- Added baseline performance benchmark script `scripts/benchmark_baseline.py` measuring cold start latency, in-process initialization, idle RAM, hook callback latency, and prediction throughput.

### Changed
- Standardized canonical user configuration directory to `%APPDATA%\Ravaan`.
- Added automatic, non-destructive migration engine `migrate_legacy_appdata()` migrating legacy `%APPDATA%\Ravan` artifacts.
- Standardized single instance mutex to `Ravaan` while guarding against conflicts with legacy instances.
- Reconfigured CLI/main stdout to UTF-8 on Windows to eliminate `UnicodeEncodeError` in console output.

## [2.0.0] - 2026-10-19

### Added
- **Automatic Wrong-Layout Correction (Target A)**:
  - Real-time automatic correction of words typed in the wrong keyboard layout (e.g. `slhl` → `سلام`, `سشمئشدی` → `salam`).
  - Dual operation modes: `safe` (dictionary-verified) and `aggressive` (frequency-based).
  - Annoyance Guard: automatically disables auto-fix for 2.0s upon manual editing.
  - Per-app auto-fix override modes and mixed Persian/English benchmark gate exceeding 98% precision.
  - Dedicated Settings tab with mode selectors, recent corrections log, and blacklist manager.

- **Unified Undo & Confidence UX (Target C)**:
  - Instant one-key undo via global hotkey (`Ctrl+Shift+Pause` / `Ctrl+Shift+Z`) restoring original text and keyboard layout.
  - Floating transient toast notification (`ToastPopup`) displaying previous and restored words with theme styling.
  - Automatic permanent blacklisting when any word correction pair is undone 3 consecutive times.

- **Auto Layout Switch on Detection (Target B)**:
  - System-level Windows keyboard layout switching via `WM_INPUTLANGCHANGEREQUEST` and `ActivateKeyboardLayout`.
  - 3 operational modes: `fix_only`, `switch_only`, and `fix_and_switch`.
  - Complete suppression inside password fields, excluded applications, and active IME composition.

- **Transliteration Mode: Finglish -> Persian (Target D)**:
  - Phonetic transliteration engine converting Latin Finglish into proper Persian script (e.g. `chetori` → `چطوری`).
  - Pre-seeded 9,799-word bilingual mapping dictionary with fuzzy phonetic fallback.
  - Personal frequency learning (`record_pick`) remembering user candidate choices across sessions.
  - System tray toggle with checkmark and dynamic `FA-TL` language indicator badge.
  - CLI bulk transliteration tool (`python -m ravan.cli translit`).

- **Live Suggestions Upgrade (Target E)**:
  - Option to accept inline word predictions with Arrow keys (Right Arrow, or Left Arrow in RTL text).
  - Dimmed sentence and bigram continuation rows with direct `Shift+Enter` acceptance.
  - Continuous typing hardening: auto-suppression in password fields, numbers-only controls, and IME composition.
  - Sub-millisecond p95 latency (<0.3ms) and multi-monitor boundary work-area clamping.

- **Snippets 3.0: Forms, Images, Per-App, Regex (Target F)**:
  - Regex snippet triggers (`re:...`) with capture group substitutions (`$1`, `$2`) and 5ms ReDoS timeout guard.
  - Interactive Form Snippets: modal mini-dialog (`QuickFormDialog`) for dynamic variables (`{{name}}`, `{{choice:A|B}}`, `{{date}}`).
  - Direct image snippet pasting (PNG/JPEG) onto target applications via Windows clipboard (CF_DIB).
  - Per-application snippet execution filtering (`app_filter`).
  - Single-file portable `.ravaanpack` bundle export/import CLI and specification.

- **Quick Accent / Persian Letter Picker (Target G)**:
  - Key-hold trigger (300ms configurable) opening a horizontal variant strip above the caret.
  - Full coverage for Persian/Arabic letter variants (ه/ة/ھ, ی/ي/ئ, ک/ك, ا/آ/أ/إ/ء, و/ؤ, ZWNJ on Space, ۰-۹/٠-٩).
  - 1–9 number key selection, arrow key navigation, and automatic suppression in fullscreen games and videos.

- **AI Text Assistant (Target H)**:
  - Global `Ctrl+Shift+G` hotkey opening an elegant floating AI Assistant on selected text.
  - Support for offline local Ollama (`http://localhost:11434`) and custom OpenAI-compatible endpoints.
  - Quick action transformations: Rewrite & Polish, Fix Grammar & ZWNJ, Translate FA↔EN, Summarize, and Freeform Prompt.
  - Windows DPAPI credential protection for API keys with zero user text logging (zero-log privacy policy).

- **Voice Dictation: Push-to-Talk (Target I)**:
  - Local offline speech-to-text dictation via `Ctrl+Alt+V` with ASR feasibility probing (`faster-whisper`, `whisper`, `vosk`).
  - In-memory audio buffer with zero disk leaks: audio bytes are wiped immediately upon transcription.
  - Automated Persian text normalization and ZWNJ formatting applied to recognized speech.

- **Competitive Audit & Release Engineering (Target J)**:
  - Comprehensive competitive parity matrix in `COMPARISON.md` comparing Ravaan v2.0 against Punto Switcher, Caramba, NeuroSwitcher, Espanso, Beeftext, and PowerToys.
  - Full codebase compliance: all Python files strictly under 400 LOC with 100% test pass rate.

## [1.0.0] - 2026-10-19

### Added
- **Release Engineering & Packaging Pipeline**:
  - Multi-artifact CI publishing attaching both portable ZIP (`Ravaan-1.0.0-portable.zip`) and Inno Setup installer (`Ravaan-Setup-1.0.0.exe`).
  - Automated release smoke testing running real Windows binaries (`Ravaan.exe --check-updates --version`) on clean GitHub runners before publishing.
  - Smart pre-release channel filtering in the in-app updater: stable users are never offered `-rc` builds, while pre-release testers receive newer candidates.
  - Bilingual release notes template (`docs/RELEASE_NOTES_TEMPLATE.md`) with automated SHA256 tables, known limitations, and upgrade notes.
  - Combined CLI argument execution support for diagnostic commands (`--check-updates --version`).

- **Security & Privacy Hardening**:
  - Comprehensive `SECURITY.md` threat model documenting local-first processing, zero raw keystroke persistence, and reporting policies.
  - Windows Data Protection API (DPAPI) encryption for Gist tokens and WebDAV passwords in `config.json` via ctypes with automatic plaintext token migration.
  - Clipboard history hardening with password manager exclusion (1Password, Bitwarden, KeePass, etc.), regex token and Shannon entropy filtering, and 7-day auto-expiration.
  - WebDAV unencrypted HTTP security warning on plain `http://` configurations.
  - Sandboxed `ravan://` deep link parser with strict action whitelisting, parameter sanitization, and ReDoS/buffer overflow resilience.
  - Keylogger-risk audit test verifying zero raw keystroke dumps in logs and aggregate-only learning profiles.

- **Real-World Windows QA Matrix (Phase 2)**:
  - Scripted diagnostics selftest (`python -m ravan.cli selftest`): in-app verification of WH_KEYBOARD_LL hook, UIA caret reachability, SendInput injection, clipboard round-trip, audio devices, DPAPI encryption, and dictionaries with a PASS/FAIL summary report.
  - Multi-monitor & mixed-DPI popup clamping: per-monitor work area detection via `MonitorFromPoint` and `GetMonitorInfoW`, eliminating popup placement errors across multi-monitor and RDP sessions.
  - Elevated window degradation: single rate-limited tray alert per elevated session with zero repeated notification spam and complete injection suppression.
  - Custom caret fallback chain: robust handling of terminal canvas containers (VS Code), Excel cells, browser address bars, and Telegram/WhatsApp Desktop with container box filtering and cursor fallback.
  - Pre-seeded exclusion defaults: added 1Password, Bitwarden, KeePass, KeePassXC, Dashlane, LockApp, LogonUI, and CredentialUIBroker to default excluded apps.
  - Memory & latency soak test (`python -m ravan.cli soak`): synthetic typing loop verifying stable RSS (<30 MB peak vs 150 MB ceiling) and zero latency drift across 10,000 keystrokes.

- **UX Final Polish (Phase 3)**:
  - Unified UI theme system (`ravan/ui/theme.py`) providing cohesive design tokens (`Palette`: dark, light, high-contrast), typography stack with Vazirmatn for Persian, and DWM window attributes with rounded corners.
  - Frequency-scaled subtle confidence bar meter per candidate in prediction popup.
  - Refactored text statistics popup (`StatsPopupWindow`) to eliminate style drift and use unified palette and multi-monitor work area clamping.
  - Friendly First-Run Onboarding Wizard (`FirstRunWizard` in `ravan/ui/wizard.py`): single-screen, 20-second modal featuring live UI language switching, 5 essential hotkeys tour card, and full keyboard navigation (Return/Escape).
  - Upgraded system tray: multi-resolution crisp icon set with alpha transparency, Quick Toggles submenu (Prediction, Autocorrect, Auto-ZWNJ, Power Mode) with live checkmarks, and "Pause for 10 min" toggle with auto-resume timer and visual pause badge.
  - Accessibility enhancements: high-contrast theme picker in Settings, complete keyboard navigation (`Ctrl+Tab`, `Ctrl+Shift+Tab`, `Escape`, `Ctrl+Return`), and screen-reader accessible control structures.

- **Data & Migration Completeness (Phase 4)**:
  - Central Data Manifest (`ravan/core/data_manifest.py`) registering all user data files, schemas, privacy classes, and aggregate disk usage summary (`get_storage_summary`).
  - Learning Profile Citable Artifact (`ravan/core/learning.py`) with version 3 schema and statistical metadata headers (`total_words`, `total_bigrams`, `total_trigrams`, `apps_tracked`, `top_words`).
  - Upgraded Config Schema to version 3 with `sync_learning_profile` toggle and backward-compatible migration.
  - Cloud Sync for Learning Profile: optional, opt-in synchronization of aggregated typing profile across machines via both WebDAV and GitHub Gist.
  - Multi-version migration test suite (`tests/test_migration_fixtures.py`) verifying lossless migration from v0.4, v0.5, and v0.7 to v1.0 (schema 3).
  - Data & Privacy Documentation (`DATA.md`) covering file inventory, DPAPI encryption guarantees, zero-telemetry policy, and safe reset procedures.

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

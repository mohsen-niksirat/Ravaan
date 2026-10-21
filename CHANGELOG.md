# Changelog

All notable changes to Ravaan (روان) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - Round 5 Phase 3: Snippets 3.0 Image Snippets & Per-App Groups
- **Image Snippets (\image:C:\\path\\to\\image.png\ or \is_image=True\)**:
  - Automatically loads PNG, JPEG, BMP, GIF, or WebP images and places them on the Windows clipboard (\CF_DIB\).
  - Automatically triggers target application paste (\Ctrl+V\).
  - Save-time file existence and Pillow image format verification (\alidate_image_path\).
  - Expand-time missing image guard: shows friendly tray notification without text corruption or silent crashes.
- **Per-App Snippet Groups (avan/core/snippet_groups.py\)**:
  - Group model with name, enabled toggle, and list of executable/window-class matchers (\is_app_excluded\ matcher reuse).
  - Snippets can be assigned to 0..N groups; snippets with groups only expand when active application matches an enabled group.
  - Global snippets (0 assigned groups) remain active across all allowed applications.
  - Supports executable names (\chrome.exe\), extension-less names (\chrome\), and window classes (\class:ConsoleWindowClass\, \class:Notepad\).
- **Snippet Groups Manager (avan/ui/snippet_groups_ui.py\)**:
  - Embedded list editor in Settings -> Snippets tab with Add, Edit Matchers, Toggle Active, and Delete Group capabilities.
- **Snippet Editor Upgrades**:
  - Snippet Type selector: Text vs Image.
  - Image file picker dialog (\pick_image_file\) with auto-completion.
  - Per-app group assignment checkboxes with dynamic status hints.
  - Visual badges in snippet list (\[Img]\, \[Regex]\, and assigned group tags).


### Added - Round 5 Phase 2: Snippets 3.0 Interactive Forms
- **Snippet Forms Engine (`ravan/core/snippet_forms.py`)**:
  - Full support for interactive snippet placeholders (`{{field}}`, `{{field=default}}`, `{{field:choice:A|B}}`, `{{field:date}}`).
  - Multi-line textarea support with `{{field:multiline}}`.
  - Opt-in per-field value memory (`{{field:remember}}`), caching the last entered value per snippet across sessions.
  - Nested dynamic macro defaults (`{{url={{clipboard}}}}`, `{{date={{shamsi}}}}`).
  - Balanced brace parser supporting nested template expressions.
  - Headless `FormController` enabling 100% testable, decoupled form validation and rendering.
- **Themed Popup UI (`ravan/ui/form_dialog.py`)**:
  - RTL-correct Persian rendering and theme palette integration.
  - Tab / Shift+Tab field navigation; Enter confirms single-line inputs; Ctrl+Enter confirms multi-line textareas; Esc cancels without text deletion or insertion.
  - Automatic foreground window tracking and focus restoration (`SetForegroundWindow`), ensuring the active application never permanently loses focus.
  - Required field validation with red outline visual highlighting.

### Added - Round 5 Phase 1: Snippets 3.0 Regex Triggers
- **Regex Triggers (`re:`)**:
  - Full support for regular expression triggers with capture group expansions `$1`..`$9` (and `\1`..`\9`, `${1}`).
  - Double-dollar `$$` escaping to output literal `$` symbols in replacement templates.
  - Dedicated module `ravan/core/snippet_regex.py` for pattern extraction, compilation, and evaluation.
- **Safety & Catastrophic Backtracking Guard**:
  - Implemented `validate_regex_trigger()` with rejection of patterns that match empty strings (preventing unwanted triggers on empty typing states).
  - Built-in ReDoS / catastrophic backtracking test battery rejecting patterns exceeding a 1.0 ms budget.
  - Safe execution engine with length bounding and timeout protection (`safe_regex_match`).
- **Priority Chain Ordering**:
  - Regex triggers evaluate strictly *after* auto-fix (`sghl` -> `سلام`) and transliteration (`ketab` -> `کتاب`), preventing loose regexes from intercepting wrong-layout keystrokes.
  - Full backward compatibility with exact snippet triggers (`find_matching_snippet(..., include_regex=False)`).
- **Snippet Editor Upgrades**:
  - Added visual `[Regex]` badge for regex triggers in the Snippets table view.
  - Added interactive Live Trigger Test box with real-time feedback (matched replacement preview, syntax errors, or no-match indicator).
  - Validation at save time with user-facing alerts.

## [1.0.0] - 2026-10-21 - Initial Stable Release

### Summary
The initial production release of **Ravaan (????)** ? the intelligent, privacy-first bilingual Persian/English typing assistant for Windows.

### Bug Fixes
- **Shift+Enter Soft Newline Pass-through**:
  - Fixed an issue where pressing `Shift+Enter` while the prediction overlay was visible swallowed the keystroke and replaced the typed word with a candidate instead of passing the line break through to the active application (Word, Telegram, Slack, browsers).
  - Added dedicated unit tests in `tests/test_suggestions_v2.py` verifying `Shift+Enter` passes through cleanly to the OS while dismissing the suggestion popup and appending a newline to the typing journal.

### Phase 10: Final Polish, Release Automation & Version Harmonization
- Release Build Pipeline (`scripts/build_release.py`):
  - Automated workflow bundling `Ravaan.exe` via PyInstaller (`ravan.spec`), creating portable ZIP archives with multilingual documentation, and computing GNU `SHA256SUMS.txt`.
  - Optional automated Inno Setup compilation via `ISCC.exe`.
- Version Harmonization:
  - Standardized version string `1.0.0` across all codebase components: `ravan/__init__.py`, `pyproject.toml`, `installer/setup.iss`, `packaging/winget/`, `packaging/scoop/`, and `packaging/chocolatey/`.
- Release Readiness Test Suite (`tests/test_release_readiness.py`):
  - 8 automated tests ensuring version consistency across all distribution manifests, PyInstaller spec compliance, binary lexicon integrity (162k words), and release packaging.
- Quality Gates:
  - Total test suite expanded to 458 automated tests passing at 100% with 0 linter errors.

## [Unreleased] - Phase 9

### Added
- Interactive Demos & Scenarios Showcase (`docs/DEMO.md`):
  - Created 6 visual ASCII-art typing walkthroughs demonstrating wrong layout auto-fix (sghl -> سلام), Persian typography & ZWNJ (کتاب ها -> کتاب‌ها), text snippets, Finglish candidate popup, inline calculator, and memory-only privacy architecture.
- Modern Bilingual Documentation Overhaul (`README.md`, `README.fa.md`):
  - Modernized `README.md` with CI badges, release links, package manager installation instructions (Winget, Scoop, Chocolatey), keyboard shortcuts matrix, and architecture diagrams.
  - Authored dedicated Persian documentation `README.fa.md` with standard Persian typography, ZWNJ, and comprehensive setup guides.
- Community & Contribution Guidelines (`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`):
  - Created contributor guide outlining local setup, test commands, conventional commits, and dictionary contribution workflows.
  - Added Contributor Covenant Code of Conduct v2.1.
- GitHub Issue & Pull Request Templates (`.github/`):
  - Form-based YAML templates for bug reports, feature requests, and Persian dictionary / ZWNJ suggestions.
  - Configured `config.yml` with links to Security FAQ and Discussions.
  - Added structured Pull Request template (`pull_request_template.md`) enforcing zero-telemetry and bilingual parity checklists.
- Documentation & Localization Parity Test Suite (`tests/test_docs_and_community.py`):
  - 14 automated tests verifying 100% key and placeholder parity across all 298 strings in `en.json` and `fa.json`, validating internal relative markdown links, and verifying issue template schemas.

## [Unreleased] - Phase 8

### Added
- Inno Setup Pascal Script & Clean Uninstall Choice (`installer/setup.iss`):
  - Added bilingual prompt during uninstallation asking if the user wishes to delete their `%APPDATA%\Ravaan` personal data, custom snippets, and learned vocabulary.
  - Safe default (`MB_DEFBUTTON2` / No) ensures data is preserved unless explicitly confirmed.
  - Upgrade-in-place safety: upgrades overwrite binary files in `{app}` without touching user data.
- Checksums & Package Pipeline Enhancements (`scripts/generate_hashes.py`, `.github/workflows/release.yml`):
  - Added `--write-sums` generating standard GNU coreutils compatible `SHA256SUMS.txt`.
  - Added conditional SignPath Foundation code signing step in CI workflow.
  - Updated release workflow to include standard checksums and multilingual README files in portable ZIP.
- Windows Package Manager Manifests (`packaging/`):
  - Winget v1.6.0 multi-file manifests: `MohsenNiksirat.Ravaan.yaml`, `MohsenNiksirat.Ravaan.installer.yaml`, `MohsenNiksirat.Ravaan.locale.en-US.yaml`, and `MohsenNiksirat.Ravaan.locale.fa-IR.yaml`. Configured with silent switch `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART` and user-scope installer.
  - Scoop manifest (`packaging/scoop/ravaan.json`) targeting 64-bit portable release with `persist: "data"`, shortcut, and GitHub autoupdate.
  - Chocolatey package (`packaging/chocolatey/ravaan/`) including `ravaan.nuspec` (schema 2015/06), `chocolateyinstall.ps1`, and `chocolateyuninstall.ps1` with `/ALLUSERS=0` user-scope install.
- Automated Packaging Test Suite (`tests/test_installer_and_packaging.py`):
  - 18 automated tests verifying Inno Setup configuration, checksum script outputs (GNU format & Markdown table), Winget YAML schema fields, Scoop JSON persistence and paths, and Chocolatey XML metadata.
- Security & Trust Documentation (`docs/SECURITY_FAQ.md`, `docs/SMARTSCREEN.md`):
  - Created bilingual Security, Privacy & Transparency FAQ explaining why low-level keyboard hooks (`SetWindowsHookExW`) are required, offering ironclad guarantees of zero keystroke logging, zero telemetry, local-only storage, and guidelines for auditing via Process Monitor and Resource Monitor.
  - Created bilingual Windows Defender SmartScreen bypass guide with step-by-step instructions (More info -> Run anyway), SHA-256 hash verification instructions via PowerShell, and SignPath Foundation code-signing roadmap.
- Expanded Automated Packaging Test Suite (`tests/test_installer_and_packaging.py`):
  - 20 automated tests validating installer configurations, package manager manifests, checksum generator, and security documentation completeness.

## [Unreleased] - Phase 7

### Added
- High-Accuracy Transliteration & Phonetic Engine (`ravan/core/translit.py`):
  - Retained fast exact dictionary lookups for ~10,000 common Finglish words.
  - Added morphological affix decomposition for Persian verb prefixes (`mi-`, `nemi-`, `bi-`, `be-`, `ba-`, `na-`) and suffixes (`-ha`, `-haye`, `-am`, `-et`, `-esh`, `-emoon`, `-etoon`, `-eshoon`, `-tar`, `-tarin`, `-an`, `-yan`, `-i`, `-ei`, `-ee`).
  - Added rule-based phonetic transducer (`_phonetic_transduce`) supporting Persian digraphs (`kh`, `sh`, `ch`, `zh`, `gh`, `ck`, `ph`, `th`, `dh`, `aa`, `ee`, `oo`) and position-aware letter mapping.
  - Integrated 162k+ Persian lexicon (`Dictionary.persian()`) to validate and rank candidate outputs by true corpus frequency, prioritizing canonical ZWNJ typography.
  - Implemented token safety screening (`is_safe_finglish_token`): strictly protects URLs, emails, file paths, code identifiers, numbers, hashtags, and @mentions from transliteration.
- Transliteration Benchmark Suite (`tests/test_translit_benchmark.py`):
  - Comprehensive automated benchmark covering conversational expressions, inflected verbs, compound words, comparative adjectives, colloquial slang, and token screening.
  - Achieved **94.95% Top-1** and **100.00% Top-3** accuracy across the benchmark suite (exceeding 90% gate).
  - Maintained 100.00% accuracy on the 212-word corpus in `tests/test_translit.py`.
- Safe Interactive Candidate Selection & Instant Undo (`ravan/ui/app_autofix.py`, `ravan/ui/app_dialogs.py`):
  - Resolved candidate replacement bug: choosing alternative candidates (2..5) from the overlay popup dynamically replaces the previously inserted candidate without text corruption or character offset mismatch.
  - Added instant undo support: pressing Backspace immediately (< 4.0s) or triggering global undo (`Ctrl+Shift+Z`) reverts the transliterated word back to the original Finglish token.
  - Thread-safe UI toast notification: queued toast messages from background threads to `_ui_queue` on the main Tkinter thread, eliminating concurrency warnings.
- Settings & Tray Integration with "Experimental" Labels (`ravan/ui/settings_builder.py`, `ravan/ui/settings_save.py`, `ravan/ui/settings_reset.py`, `ravan/ui/tray.py`):
  - Added clearly labeled `(Experimental) / (آزمایشی)` toggle and hotkey configuration in Settings and System Tray.
  - Maintained safe opt-in default (`translit_enabled = False`) across resets and new installations.
  - Full bilingual parity across `en.json` and `fa.json` for tray labels, tooltips, examples, and undo toasts.
  - Automated tests covering candidate replacement safety, instant undo, and settings persistence in `tests/test_translit_ui.py`.

## [Unreleased] - Phase 6

### Added
- Enhanced 3-step First-Run Onboarding Wizard (`FirstRunWizard` in `ravan/ui/wizard.py`):
  - Presets selection: Simple (minimalist, smart ZWNJ only), Standard (recommended balance of predictions and auto-fix), and Power User (full feature set with next-word, clipboard history, calc, macros).
  - Primary conversion hotkey selector with dropdown choices (`Pause`, `Alt+L`, `Ctrl+Shift+L`, `F12`, `Alt+Shift`).
  - 30-second live interactive typing demo sandbox: real-time simulation of layout conversion (`sghl ` → `سلام `), smart ZWNJ (`می ` → `می‌`), and live suggestion pills.
  - Full keyboard accessibility and bilingual localization in `fa.json` and `en.json`.
  - Comprehensive unit tests in `tests/test_wizard_v2.py`.
- Settings Window Simplification, ToolTips, and Search (`ravan/ui/tooltip.py`, `ravan/ui/settings.py`, `ravan/ui/settings_builder.py`, `ravan/ui/settings_autofix.py`):
  - Reusable lightweight hover tooltip component (`ToolTip`) with graceful fading and bounds checking.
  - One-click clear button (`✕`) for fast search resetting in Settings window.
  - Inline "what does this do?" examples (`↳ Example: ...`) under major feature toggles (calculator, clipboard history, smart ZWNJ, punctuation spacing, auto-fix layout).
  - Bilingual tooltips and examples in `fa.json` and `en.json`.
  - Comprehensive automated tests in `tests/test_settings_search.py`.
- Tray "Quick Tips & Shortcuts" Window (`QuickTipsWindow` in `ravan/ui/quick_tips.py`):
  - In-app searchable cheat sheet and help guide categorized by Essential Shortcuts, Smart Everyday Features, and Privacy & Trust.
  - Interactive search bar with instant clear button to find tips quickly.
  - Full keyboard accessibility with `<Escape>` closing and Tab navigation.
  - Complete bilingual localization and RTL support in `en.json` and `fa.json`.
- Non-Annoying Educational Feature Hints (`HintManager` in `ravan/ui/hint_manager.py`):
  - Strict guarantee: max one hint per feature ever, persisted across restarts in `Config.shown_hints`.
  - Non-intrusive, dismissible forever with a dedicated setting toggle (`enable_feature_hints`).
- Dedicated Pause / Resume Hotkey & Tray Integration (`pause_hotkey` in `ravan/core/config.py`, `ravan/ui/key_handler.py`, `ravan/ui/tray.py`):
  - Configurable global hotkey (`Ctrl+Alt+Pause` by default) to pause/resume Ravaan assistance from anywhere.
  - Works consistently both when active and when paused.
  - One-click pause toggle in the system tray menu.
  - Automated tests in `tests/test_quick_tips_and_hints.py`.
- Accessibility, High-Contrast & Typography Verification (`tests/test_accessibility.py`):
  - Verified WCAG 2.1 AA compliant contrast ratios ($\ge$ 4.5:1 for normal text, $\ge$ 15.0:1 for high-contrast mode) across dark, light, and high-contrast palettes.
  - Full keyboard navigation across all interactive dialogs (`<Escape>` to dismiss, Tab order, Enter to trigger primary actions).
  - RTL font stack prioritization (`Vazirmatn` with fallbacks) and LTR stack (`Segoe UI`).
  - No color-only signals: confidence meters use 4-step Unicode block indicators (` `, `▂`, `▅`, `█`) and status indicators feature distinct text/icons.



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
- Global Crash Handler & Friendly Bilingual Crash Dialog in `ravan/ui/crash_dialog.py` and `ravan/ui/log_setup.py`:
  - Sanitized technical diagnostic report generation (`build_diagnostic_report`) containing OS platform, architecture, Python version, app version, clean exception stack traces, and recent log entries.
  - Strict privacy guarantee: guarantees that zero keystrokes, typed text, or personal credentials are ever recorded.
  - Standalone modal `CrashDialog` with clear Persian and English explanations, reassuring users that their privacy is protected.
  - "Copy Diagnostic Report" button with one-click clipboard copying and visual feedback.
  - "Open Logs Folder", "Restart Ravaan", and "Close" controls.
  - Localized strings in both `fa.json` and `en.json` with correct RTL layout.
  - Automated tests in `tests/test_crash_handler.py`.
- Automated CI Performance Gate and budget verification in `tests/test_perf_gate.py`:
  - Enforced strict latency and memory budgets across all critical typing paths.
  - Cold dictionary load budget (< 25 ms, actual < 4 ms).
  - Idle RAM budget (< 45 MB RSS, actual ~19.0 MB).
  - Hook callback latency budget (mean < 400 us, p95 < 1000 us).
  - Rapid typing burst throughput (1,000 keystrokes at 150+ WPM without backlog, < 500 us per event).
  - Prediction query latency budget (mean < 5.0 ms, p95 < 15.0 ms).
  - Auto-fix wrong-layout detection budget (mean < 2.5 ms, p95 < 8.0 ms).
- Performance optimizations:
  - Added LRU query completion cache in `Dictionary` (`ravan/core/dict.py`), dropping prediction query latency from 8.27 ms down to 1.10 ms.
  - Optimized `is_safe_autocorrect_token` in `ravan/core/predictor.py` using set disjoint checks and native tuple suffixes, accelerating token screening 4x to > 45,000 tokens/sec.
  - Added standard `__len__` method to `Dictionary`.
- Extended Soak & Multi-Application QA Matrix Harness in `ravan/core/soak.py` and `docs/QA-MATRIX.md`:
  - Multi-app continuous typing simulation across 10 Windows applications: Notepad, Word, Excel, Chrome, Edge, Firefox, VS Code, Telegram Desktop, Discord, and Windows Terminal.
  - Zero memory leaks and stable latency throughout rapid window switching and continuous typing workloads.
  - Comprehensive documentation in `docs/QA-MATRIX.md` covering Windows 10 and 11 behavior, Win32 vs WinUI 3 controls, UIPI elevated barriers, password field suppression, and multi-monitor DPI scaling.
  - Added automated tests in `tests/test_qa_windows.py` for terminal/IDE wrong-layout suppression and multi-monitor negative coordinate handling.

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

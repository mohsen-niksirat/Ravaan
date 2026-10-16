# Roadmap

Done (v0.4):
- M20: Code Quality Pass (Refactored all modules to strictly under 400 lines of code across `ravan/ui` and `ravan/platform` via mixins and modular builders, raised test suite to 130 passing tests including comprehensive Win32 API and UI mock test suites, added `ruff` configuration to `pyproject.toml` with clean pass across all files, and integrated `ruff check .` into GitHub Actions CI matrix)
- M19: Snippets 2.0 (Dedicated Snippet Editor window in Tkinter with live preview & search filter, multi-line snippet expansions, cursor-position placeholder `$0` and `{{cursor}}` via synthetic Left arrow key injection, expanded date macros for year/month/day/weekday/yesterday/tomorrow, embedded math calculation evaluation `{{calc:...}}`, JSON import/export with merge/replace, and excluded apps protection so snippet expansion is suppressed in excluded applications)
- M18: Autocorrect & Language Intelligence (bilingual awareness via layout hook tracking so English and Persian are never mixed, Persian confusable typo normalization for `ی/ي`, `ک/ك`, `ه/ة`, `ت/ة`, log-frequency candidate probability scoring, instantaneous undo autocorrect via `Ctrl+Shift+Z` or single `Backspace`, and punctuation spacing cleanup removing pre-punctuation spaces before `.,!?:؛،؟`)
- M17: Reliability & UX hardening (Per-Monitor V2 DPI awareness, flicker-free overlay row recycling with SWP_NOACTIVATE, interactive excluded apps detector in Settings, structured rotating file logging capped at 2MB with 3 backups, graceful UIA failure throttling per process, and Diagnostics tray window with live status & markdown report export)
- M16: PyInstaller standalone distribution packaging (`Ravaan.exe` with bundled icon & assets, windowed no-console), GitHub Actions CI/CD release workflow on tag push, and install/uninstall documentation
- M15: External UTF-8 dictionary loading (`word<TAB>frequency`), 12,500+ Persian frequency dataset, hierarchical ranking (custom dict > frequency > edit distance), and adaptive learning selection boost
- Number to Persian words converter, Rial-to-Toman calculator, and thousands separator formatting (`/w`, `/t`, `/s`, CLI `words`)
- Keyboard layout audio feedback (distinct gentle tones for Persian and English upon layout switch)
- Dynamic snippets with Persian Jalali (Shamsi) calendar date/time expander (`/today`, `/shamsi`, `/tarikh`, `/time`, `/uuid`, `{{placeholders}}`, and CLI `jalali`)
- In-place text transformation (case cycling with `Shift+F12` and Persian normalizer with `Ctrl+F12`)
- Inline quick math calculator on `=` trigger (`(50+30)*2= -> 160`, supporting Persian digits `۱۲*۵= -> ۶۰`, and CLI `calc`)
- User custom dictionary (`user_words.txt`), in-memory priority merging in `Dictionary` and `DictPredictor`, settings window editor, and CLI `dict list/add/remove`
- Selection layout conversion (convert highlighted text in place or fall back to last word)
- Smart Persian half-space (ZWNJ): prefix/suffix auto-attachment + `Shift+Space` hotkey
- Caret clipboard history ring buffer popup (`Alt+V`) with quick 1–5 number paste
- Persian / Arabic text and number normalization (CLI + core module)
- Expanded dictionary assets (770+ English, 12,500+ Persian frequency-ranked words)
- Full Settings UI with toggles for new features
- Safe autocorrect (never rewrites dictionary words)
- Tray menu with prediction toggle + notifications
- Single-instance guard, launch-at-startup (HKCU Run)
- Per-app exclusions (excluded_apps)
- Real UIA caret (TextPattern2/TextPattern + ancestor walk)
- Journal reset on focus change; popup auto-timeout; hotkey repeat throttle

---

## Next Horizon (Proposed Future Milestones)

1. **Hotkey Remapping UI & Per-App Shortcut Profiles**
   - Provide an interactive graphical keybinder in Settings to customize hotkeys (`F12`, `Alt+L`, `Alt+V`, `Ctrl+F12`, `Shift+F12`, `Shift+Space`, etc.).
   - Support per-application custom trigger overrides (e.g. disable `F12` in VS Code or games, bind `Alt+F12` instead).

2. **Full English Frequency Dictionary Expansion (50,000+ Words)**
   - Expand the bundled English dictionary with frequency counts derived from contemporary English corpora.
   - Introduce n-gram bigram/trigram next-word prediction based on typed context.

3. **Cloud & Git Sync for User Dictionary and Snippets**
   - Allow typists to synchronize `user_words.txt` and `snippets.json` across multiple machines using GitHub Gist, Google Drive, or WebDAV.
   - Conflict resolution and backup history.

4. **Native Inno Setup Windows Installer & Auto-Updater**
   - Build a signed setup `.exe` with Inno Setup with start-menu shortcuts and desktop integration.
   - Lightweight silent background update checker for new GitHub Releases.

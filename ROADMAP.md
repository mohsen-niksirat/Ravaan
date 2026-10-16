# Roadmap
 
Done (v0.4):
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

Next:
- Phase 2: Distribution & First Release (PyInstaller single-file exe, GitHub Actions release workflow)
- Phase 3: Reliability & UX Hardening (DPI scaling, overlay caret tracking, structured logging & diagnostics window)
- Phase 4: Autocorrect & Language Intelligence (bilingual awareness, typo modeling, undo hotkey)
- Phase 5: Snippets 2.0 (multi-line snippets, JSON import/export, cursor $0 placement)
- Phase 6: Code Quality Pass (linting pass, modular refactoring, fake Win32 tests)
- Per-app hotkey profiles
- Installer (Inno Setup) + optional code signing
- Linux port (Wayland input capture) — long term

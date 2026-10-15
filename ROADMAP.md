# Roadmap
 
Done (v0.4):
- Dynamic snippets with Persian Jalali (Shamsi) calendar date/time expander (`/today`, `/shamsi`, `/tarikh`, `/time`, `/uuid`, `{{placeholders}}`, and CLI `jalali`)
- In-place text transformation (case cycling with `Shift+F12` and Persian normalizer with `Ctrl+F12`)
- Inline quick math calculator on `=` trigger (`(50+30)*2= -> 160`, supporting Persian digits `۱۲*۵= -> ۶۰`, and CLI `calc`)
- User custom dictionary (`user_words.txt`), in-memory priority merging in `Dictionary` and `DictPredictor`, settings window editor, and CLI `dict list/add/remove`
- Selection layout conversion (convert highlighted text in place or fall back to last word)
- Smart Persian half-space (ZWNJ): prefix/suffix auto-attachment + `Shift+Space` hotkey
- Caret clipboard history ring buffer popup (`Alt+V`) with quick 1–5 number paste
- Persian / Arabic text and number normalization (CLI + core module)
- Expanded dictionary assets (770+ English, 560+ Persian curated words)
- Full Settings UI with toggles for new features
- Safe autocorrect (never rewrites dictionary words)
- Tray menu with prediction toggle + notifications
- Single-instance guard, launch-at-startup (HKCU Run)
- Per-app exclusions (excluded_apps)
- Real UIA caret (TextPattern2/TextPattern + ancestor walk)
- Journal reset on focus change; popup auto-timeout; hotkey repeat throttle

Next:
- Local ONNX / small LLM sentence completion behind the `Predictor` interface
- Voice input / dictation
- Full frequency dictionaries (EN ~50k, FA ~30k) as compressed SQLite / trie assets
- Per-app hotkey profiles
- Installer (Inno Setup) + optional code signing
- Linux port (Wayland input capture) — long term

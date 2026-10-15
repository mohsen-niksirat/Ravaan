# Roadmap

Done (v0.2):
- Safe autocorrect (never rewrites dictionary words)
- Settings window (hotkeys, toggles, snippets, exclusions, startup)
- Tray menu with prediction toggle + notifications
- Single-instance guard, launch-at-startup (HKCU Run)
- Per-app exclusions (excluded_apps) — now enforced
- Real UIA caret (TextPattern2/TextPattern + ancestor walk)
- Journal reset on focus change; popup auto-timeout; hotkey repeat throttle

Next:
- Local ONNX / small LLM sentence completion behind the `Predictor` interface
- Voice input / dictation
- Clipboard history
- More languages beyond FA/EN
- Full frequency dictionaries (EN ~50k, FA ~30k) as compressed assets
- Per-app hotkey profiles
- Installer (Inno Setup) + optional code signing
- Linux port (Wayland input capture) — long term

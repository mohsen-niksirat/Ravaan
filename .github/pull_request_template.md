## Description
<!-- Briefly describe the changes made in this Pull Request and why they are needed. -->

## Related Issue
<!-- Link to related issue (e.g. Closes #123, Fixes #456) -->

## Type of Change
<!-- Mark the relevant option with an [x] -->
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Dictionary / Linguistics update (Persian words, ZWNJ rules, transliteration)
- [ ] Documentation update
- [ ] Performance optimization or refactor

## Core Principles Checklist
<!-- All submissions must adhere to Ravaan's core security and privacy architecture -->
- [ ] **Zero Telemetry:** No network analytics, telemetry SDKs, or background web requests introduced.
- [ ] **Zero Keystroke Logging:** No keystroke logging or saving raw input streams to disk.
- [ ] **Bilingual Parity:** Any new user-facing strings are synchronized in both `ravan/data/locales/en.json` and `ravan/data/locales/fa.json`.
- [ ] **Automated Tests:** Added or updated unit tests (`pytest`).
- [ ] **Code Quality:** All checks pass (`pytest` and `ruff check .`).
- [ ] **Changelog:** Updated `CHANGELOG.md` under `[Unreleased]`.

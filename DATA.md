# Ravaan (روان) — Data, Privacy & Storage Architecture

This document provides a complete inventory of every file created by **Ravaan**, its schema version, privacy classification, encryption guarantees, and instructions for backing up or resetting user data.

---

## 1. Storage Location

On Microsoft Windows, all persistent user configuration and runtime data are stored in:

```
%APPDATA%\Ravaan\
(e.g., C:\Users\<Username>\AppData\Roaming\Ravaan\)
```

Ravaan does **not** write to the Windows Registry for user settings (with the sole exception of the optional standard Windows `Run` key if "Launch at startup" is enabled).

---

## 2. File Inventory & Data Manifest

All files are registered in Ravaan's single-source-of-truth manifest (`ravan.core.data_manifest`):

| File | Schema Version | Privacy Classification | Resettable | Description |
| :--- | :---: | :---: | :---: | :--- |
| `config.json` | `3` | **Credentials** | Yes | Core settings, hotkeys, theme preferences, and DPAPI-encrypted sync credentials. |
| `user_words.txt` | `1` | **Private** | Yes | Custom user vocabulary additions (UTF-8, one word per line). |
| `user_learning.json` | `3` | **Private** | Yes | Learned n-gram transitions, vocabulary decay weights, and per-app models. |
| `clipboard_history.json` | `1` | **Sensitive** | Yes | Recent clipboard ring buffer, filtered for high-entropy secrets and passwords. |
| `stats.json` | `1` | **Metrics** | Yes | Keystroke counters, saved character metrics, and typing velocity statistics. |
| `backups/` | — | **Private** | Yes | Automated pre-sync snapshots and safety backups created before reset actions. |
| `logs/ravan.log` | — | **Diagnostic** | Yes | Rotating diagnostic application logs (sanitized of auth tokens and passwords). |

---

## 3. Privacy & Security Architecture

### 3.1 Local-First & Zero Telemetry
- **No telemetry**: Ravaan never phones home. There are no tracking scripts, analytics SDKs, or background metric collectors.
- **Local processing**: All Persian text normalization, layout conversion (EN ↔ FA), spell-checking, and n-gram suggestions are performed 100% locally in memory on your CPU.

### 3.2 Credential Protection via Windows DPAPI
- When Cloud Sync is configured, sensitive credentials (GitHub Gist Personal Access Tokens and WebDAV passwords) are encrypted before being written to `config.json` using the **Windows Data Protection API (DPAPI)** via `CryptProtectData`.
- DPAPI keys are tied to the local Windows user account and cannot be decrypted by other user accounts on the machine or from copied configuration files.

### 3.3 Sensitive Input & Clipboard Protection
- **Entropy screening**: Text copied to the clipboard is scanned for high-entropy tokens (e.g. AWS keys, JWT tokens, hex hashes) and password patterns before entering the clipboard history.
- **Application exclusions**: Password managers (e.g., `1password.exe`, `keepass.exe`, `bitwarden.exe`) are excluded by default from suggestion tracking and keystroke capture.
- **Secret redaction**: Application logs automatically redact sensitive authorization tokens and passwords before writing to disk.

---

## 4. Cloud Sync & Synchronization Scope

Cloud Sync is **strictly opt-in** and supports two backends:
1. **GitHub Gist**: Stores `user_words.txt`, `snippets.json`, and optionally `learning_profile.json` in a secret Gist owned by the user.
2. **WebDAV (Nextcloud / ownCloud)**: Stores the same files via HTTPS PUT/GET requests on your own private cloud instance.

### Optional Learning Profile Sync
By default, your typing learning model (`user_learning.json`) remains strictly local on each PC. If you enable *"Include learned typing profile in cloud sync"*, an aggregated statistical profile is synchronized across your devices.

---

## 5. Schema Migration & Backward Compatibility

Ravaan supports automated, lossless schema migration from all previous versions:
- **v0.4 (Schema 0/None)**: Migrates legacy flat hotkeys and app exclusions to schema 3.
- **v0.5 (Schema 1)**: Migrates inline calculator, quickpick digits, and ZWNJ settings.
- **v0.7 (Schema 2)**: Migrates WebDAV and Gist sync configuration and dark/light theme tokens.
- **v1.0 (Schema 3)**: Unified data manifest, learning profile sync, and multi-monitor layout persistence.

---

## 6. How to Reset or Backup Your Data

### Exporting / Restoring Backups
- **From UI**: Open **Settings → Data / Sync → Export Backup ZIP** or **Restore Backup ZIP**.
- **CLI**:
  ```bash
  ravan export-data --dest C:\Backups\Ravaan-Backup.zip
  ravan import-data --src C:\Backups\Ravaan-Backup.zip
  ```

### Resetting Specific Data Files
To clear a specific component without losing your main configuration:
- **User Words**: Clear the text area in **Settings → Dictionary → User Words** and click Save.
- **Learned Model**: Delete `%APPDATA%\Ravaan\user_learning.json` while Ravaan is closed. It will regenerate with standard starter transitions on next launch.
- **Clipboard History**: Delete `%APPDATA%\Ravaan\clipboard_history.json`.
- **Full Factory Reset**: Delete the `%APPDATA%\Ravaan\` folder while Ravaan is closed. Ravaan will trigger the First-Run Onboarding Wizard upon restart.

---

## 7. Bundled Lexicons & Dictionaries

Ravaan bundles large, license-checked word lists for Persian and English word prediction, auto-correction, and wrong-layout detection:

| Asset | Source / Corpus | License | Words | Format | Cold-Load Latency |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `words_fa.txt` / `.bin` | Hermit Dave FrequencyWords (2018) + Ravaan Curated Lexicon | **MIT** | 162,935 | UTF-8 / RVN2 mmap | **< 4 ms** |
| `words_en.txt` / `.bin` | Hermit Dave FrequencyWords (2018) + Ravaan Curated Lexicon | **MIT** | 46,827 | UTF-8 / RVN2 mmap | **< 2 ms** |
| `finglish_dict.json` | Ravaan Bilingual Transliteration Lexicon | **MIT** | 9,799 | JSON | < 5 ms |

### High-Performance Binary Index (`RVN2`)
To guarantee sub-millisecond cold start times without loading 200,000+ Python objects into heap memory, Ravaan automatically compiles `.txt` word lists into memory-mapped `.bin` files (`RVN2` format):
- Dual offset indexing: alphabetical table for $O(\log N)$ binary search and contiguous prefix completion; rank table for instant $O(1)$ priority sorting.
- Zero-heap overhead: the OS memory-maps the binary file into virtual memory without allocating Python objects for inactive vocabulary.
- Seamless fallback: if `.bin` is deleted or `.txt` is updated, Ravaan automatically recompiles the binary index on startup.


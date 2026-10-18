# Security and Privacy Policy

Ravaan (روان) is an open-source typing assistant for bilingual Persian and English typists on Windows. Because typing assistants operate near system-level input streams (global keyboard hooks and synthesized keystroke injection), we treat security and privacy as fundamental non-negotiable architectural requirements.

---

## 1. Threat Model & Design Principles

1. **Local-First Processing**: All core features — layout conversion, word prediction, autocorrect, ZWNJ half-spacing, inline calculation, and text normalization — execute entirely on your local machine with zero mandatory cloud connectivity.
2. **Least Privilege**: Ravaan runs strictly in the standard user security context (`PrivilegesRequired=lowest`). It does not require Administrator privileges or elevate via UAC.
3. **No Keystroke Telemetry**: Raw keystroke logs, scan codes, and timing sequences are **never** written to disk or transmitted over the network.
4. **Defense in Depth**: Password fields are detected and shielded; clipboard history ignores credentials; sensitive sync tokens are encrypted at rest with Windows DPAPI.

---

## 2. What Is and Is Never Stored

### What is NEVER Stored or Transmitted:
- ❌ **Raw Keystrokes**: Individual keypresses, keyup/keydown events, physical scan codes, and character stream buffers are **never** serialized to disk, written to logs, or sent over the network.
- ❌ **Volatile Word Tracker**: The in-memory buffer holding current typing context exists exclusively in volatile RAM and is flushed on word boundaries and focus transitions.
- ❌ **Password Content**: Keystrokes typed into password fields (detected via Win32 `ES_PASSWORD` or UI Automation `IsPassword`) are completely shielded from prediction, autocorrect, and macro learning.
- ❌ **Unencrypted Tokens**: Sync tokens and passwords are never stored in plaintext on disk.

### What IS Stored Locally on Disk:
All user data is strictly confined to `%APPDATA%\Ravan`:
- `config.json`: Application preferences and hotkeys. Sensitive tokens (`gist_token`, `webdav_password`) are encrypted at rest using Windows DPAPI.
- `user_words.txt`: Custom words explicitly added by the user or learned from normal completed words.
- `snippets.json`: User-configured snippet expansion triggers and replacements.
- `clipboard_history.json`: Clipboard ring buffer (subject to password-manager exclusion, token filtering, and auto-expiration).
- `learning_profile.json`: Aggregate word-level unigram/bigram/trigram frequencies used solely for local candidate ranking.
- `logs/ravan.log`: Application runtime diagnostics (rotated at 5 MB, keeping max 3 backups; contains only operational events and completed autocorrect reversals, never raw keystrokes).
- `backups/`: Up to 10 local timestamped JSON snapshots taken before cloud sync operations.

---

## 3. Password Input Shield

Ravaan actively queries the focused window and text field before processing text:
- **Win32 Password Style Detection**: Checks window style bits for `ES_PASSWORD`.
- **UI Automation (UIA) Text Pattern**: Queries the accessible element's `IsPassword` property.
- When a password input field is focused:
  - Prediction popups are disabled.
  - Autocorrect is disabled.
  - Math evaluation is disabled.
  - Word tracking is cleared and halted.
  - Macro recorder refuses to record.

---

## 4. Clipboard History Hardening

Ravaan's clipboard history ring buffer (`Alt+V`) implements proactive privacy protections:
1. **Password Manager Exclusion**: Copies originating from known password manager processes (`1password.exe`, `bitwarden.exe`, `keepass.exe`, `keepassxc.exe`, `dashlane.exe`, `enpass.exe`, `lastpass.exe`, `nordpass.exe`, `roboform.exe`, `authy.exe`) or any application in your excluded apps list are automatically discarded.
2. **Token and Key Filtering**: Text matching known patterns for API credentials (e.g. GitHub tokens, AWS keys, Stripe secret keys, Slack tokens, private keys) or high-entropy password strings (mixed case, digits, and symbols without spaces) is detected by heuristic analysis and rejected.
3. **Automatic Expiration**: Unpinned clipboard history items automatically expire and are purged after **7 days** (configurable via `clip_history_retention_days`).
4. **Internal Sentinel Filtering**: Clipboard operations executed by Ravaan itself (such as snippet expansion) use internal sentinel tags and are never stored in user clipboard history.

---

## 5. Sync Security & Credential Protection

- **Windows DPAPI Encryption**: Sync credentials (`gist_token` and `webdav_password`) are encrypted using the Windows Data Protection API (`CryptProtectData` in `Crypt32.dll`) tied directly to your Windows user account.
- **Migration of Plaintext Tokens**: Any existing plaintext tokens from earlier versions (0.x) are automatically upgraded to DPAPI encryption on first launch.
- **Unencrypted WebDAV (HTTP) Warning**: Configuring a WebDAV sync URL over plain `http://` triggers prominent warnings in the application logs and user interface, as plain HTTP transmits credentials and dictionaries in cleartext across the network. HTTPS is strongly enforced.
- **Pre-Sync Snapshots**: Every sync push or pull automatically generates a timestamped local snapshot in `%APPDATA%\Ravan\backups\`, allowing instant rollback in the event of an upstream conflict.

---

## 6. `ravan://` Deep Link Protocol Validation

The `ravan://` custom URL protocol handler registered in Windows (`HKCU\Software\Classes\ravan`) is strictly sandboxed:
- **Whitelisted Actions**: Only explicitly permitted internal commands are parsed (`settings`, `stats`, `snippet`, `help`, `about`).
- **No Remote Code Execution**: Deep links cannot execute external commands, launch shell binaries, or modify system files.
- **No Automated Text Injection**: Deep links are strictly prohibited from typing or injecting text into other applications.
- **Input Sanitization**: Total URL length is capped at 2048 characters; null bytes, path traversal sequences (`..`, `\`), and control characters are stripped. Parameters such as settings tabs and snippet triggers are validated against strict whitelists.

---

## 7. Installation & System Footprint

- **Per-User Only**: The Inno Setup installer (`Ravaan-Setup-x.y.z.exe`) uses `PrivilegesRequired=lowest`. It requires no Administrator UAC prompts.
- **Strict Confinement**:
  - Executable and assets: `%LOCALAPPDATA%\Programs\Ravaan`
  - User configuration and state: `%APPDATA%\Ravan`
  - Registry: Strictly confined to `HKEY_CURRENT_USER\Software\Classes\ravan` and `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run` (optional).
- **Clean Uninstall**: Uninstalling Ravaan cleanly removes all binaries, shortcuts, and protocol associations while preserving your personal dictionaries in `%APPDATA%\Ravan` to prevent accidental data loss.

---

## 8. Reporting Security Vulnerabilities

If you discover a potential security vulnerability in Ravaan, please report it responsibly:
- **Private Reporting**: Open a confidential security report via [GitHub Security Advisories](https://github.com/mohsen-niksirat/Ravaan/security/advisories/new).
- Do not disclose vulnerabilities in public GitHub issues or discussions until a patch has been released.
- We will acknowledge receipt of your report within 48 hours and provide an estimated timeline for remediation.

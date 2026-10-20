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
All user data is strictly confined to `%APPDATA%\Ravaan`:
- `config.json`: Application preferences and hotkeys. Sensitive tokens (`gist_token`, `webdav_password`, `ai_api_key`) are stored in Windows Credential Manager and never stored in plaintext on disk.
- `user_words.txt`: Custom words explicitly added by the user or learned from normal completed words.
- `snippets.json`: User-configured snippet expansion triggers and replacements.
- `clipboard_history.json`: Clipboard ring buffer (subject to password-manager exclusion, token filtering, and auto-expiration).
- `user_learning.json`: Aggregate word-level unigram/bigram/trigram frequencies, **encrypted at rest via Windows DPAPI** (`CryptProtectData`).
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

- **Windows Credential Manager Integration**: Sync credentials (`gist_token`, `webdav_password`, `ai_api_key`) are saved directly into the Windows Credential Manager via native Win32 `advapi32.dll` (`CredWriteW` / `CredReadW`) under targets like `Ravaan/GitHubGistToken`.
- **Zero Plaintext Tokens**: `config.json` stores only non-sensitive target pointers (`wincred:<target>`), eliminating plaintext secret exposure.
- **Migration of Plaintext and Legacy Tokens**: Any legacy plaintext or DPAPI tokens from earlier versions are automatically migrated to Windows Credential Manager on startup.
- **Strict HTTPS Enforcement**: WebDAV and sync endpoints over unencrypted `http://` produce clear warnings; encrypted HTTPS is strongly enforced.
- **Pre-Sync Snapshots**: Every sync push or pull automatically generates a timestamped local snapshot in `%APPDATA%\Ravaan\backups\`, allowing instant rollback.

---

## 6. Auto-Update Integrity & Verification

Ravaan's in-app updater implements strict cryptographic and binary integrity gates:
- **HTTPS Only**: All update release queries and installer download URLs must use `https://`. Non-HTTPS URLs are rejected immediately.
- **SHA-256 Hash Verification**: During download, SHA-256 is computed dynamically and compared against the expected release hash. Any mismatch halts execution and purges the unverified binary.
- **PE Binary Signature Check**: Downloaded executables are verified to possess a valid Windows PE header (`b"MZ"` signature) before launching.

---

## 7. `ravan://` Deep Link Protocol Validation

The `ravan://` custom URL protocol handler registered in Windows (`HKCU\Software\Classes\ravan`) is strictly sandboxed:
- **Whitelisted Actions**: Only explicitly permitted internal commands are parsed (`settings`, `stats`, `snippet`, `help`, `about`).
- **No Remote Code Execution**: Deep links cannot execute external commands, launch shell binaries, or modify system files.
- **No Automated Text Injection**: Deep links are strictly prohibited from typing or injecting text into other applications.
- **Input Sanitization**: Total URL length is capped at 2048 characters; null bytes, path traversal sequences (`..`, `\`), and control characters are stripped. Parameters such as settings tabs and snippet triggers are validated against strict whitelists.

---

## 8. خلاصهٔ امنیت و حریم خصوصی به زبان ساده (چه چیزی ذخیره می‌شود، چه چیزی نمی‌شود)

- **چه چیزی هرگز ثبت یا ارسال نمی‌شود؟**
  - هیچ گزارشی از کلیدهای فشرده‌شده، حروف تایپ‌شده یا زمان‌بندی کلیدها ثبت نمی‌شود.
  - هیچ داده‌ای از پنجره‌ها یا فیلدهای رمز عبور خوانده یا پردازش نمی‌شود.
  - هیچ تلمتری یا اطلاعات آماری به هیچ سروری ارسال نمی‌گردد.

- **چه چیزی روی سیستم شما ذخیره می‌شود؟**
  - تنظیمات و کلیدهای میانبر در `%APPDATA%\Ravaan\config.json`.
  - توکن‌ها و رمزها در **Windows Credential Manager** (نه در فایل کانفیگ).
  - مدل یادگیری واژگان در `user_learning.json` به صورت **رمزگذاری‌شده با DPAPI ویندوز**.
  - واژگان سفارشی و کلمات اختصاری در فایل‌های متنی محلی.

- **اختیارات و کنترل‌های شما:**
  - یادگیری هوشمند را با یک تیک می‌توانید کاملاً غیرفعال کنید.
  - می‌توانید با یک کلیک از تمام داده‌های یادگیری خروجی استاندارد JSON بگیرید.
  - می‌توانید تمام واژگان و سبک‌های آموخته‌شده را با دکمهٔ «پاک‌سازی داده‌ها» به حالت کارخانه بازگردانید.

---

## 9. Installation & System Footprint

- **Per-User Only**: The Inno Setup installer (`Ravaan-Setup-x.y.z.exe`) uses `PrivilegesRequired=lowest`. It requires no Administrator UAC prompts.
- **Strict Confinement**:
  - Executable and assets: `%LOCALAPPDATA%\Programs\Ravaan`
  - User configuration and state: `%APPDATA%\Ravaan`
  - Registry: Strictly confined to `HKEY_CURRENT_USER\Software\Classes\ravan` and `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run` (optional).
- **Clean Uninstall**: Uninstalling Ravaan cleanly removes all binaries, shortcuts, and protocol associations while preserving your personal dictionaries in `%APPDATA%\Ravaan` to prevent accidental data loss.

---

## 10. Reporting Security Vulnerabilities

If you discover a potential security vulnerability in Ravaan, please report it responsibly:
- **Private Reporting**: Open a confidential security report via [GitHub Security Advisories](https://github.com/mohsen-niksirat/Ravaan/security/advisories/new).
- Do not disclose vulnerabilities in public GitHub issues or discussions until a patch has been released.
- We will acknowledge receipt of your report within 48 hours and provide an estimated timeline for remediation.

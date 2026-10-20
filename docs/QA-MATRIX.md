# Ravaan (روان) — Windows QA Compatibility Matrix

> **Target Platform:** Windows 10 (21H2+) and Windows 11 (21H2, 22H2, 23H2, 24H2)  
> **Architecture:** x64 / AMD64  
> **Status:** Production Verified  
> **Last Updated:** Phase 5 (Performance & Reliability)

---

## 1. Executive Summary

Ravaan operates as a lightweight, non-intrusive Windows desktop assistant designed specifically for Persian and English bilingual typists. Because keyboard assistants interact closely with the Windows subsystem via low-level hooks (`WH_KEYBOARD_LL`), the text injection subsystem (`SendInput`), and accessibility caret tracking (`UI Automation` & `GetGUIThreadInfo`), compatibility must be verified across distinct application UI frameworks (Win32, WinUI/XAML, Chromium/Electron, Gecko, Qt, ConPTY).

This document establishes the verified compatibility matrix, behavior characteristics, edge cases, and known limitations.

---

## 2. Operating System Support Matrix

| Windows Edition | Build Range | Status | Key Characteristics & Notes |
|:---|:---:|:---:|:---|
| **Windows 11 (24H2, 23H2, 22H2)** | 22621–26100+ | ✅ **Full Support** | Modern WinUI 3 controls, DWM rounded corners, per-monitor v2 DPI awareness, Windows Terminal default. |
| **Windows 11 (21H2)** | 22000 | ✅ **Full Support** | Native UIA TextPattern support, modern taskbar notification area. |
| **Windows 10 (22H2, 21H2)** | 19044–19045 | ✅ **Full Support** | Classic Win32 controls, stable `GetGUIThreadInfo` fallback, standard notification toast support. |
| **Windows Server 2019/2022** | 17763+ | ⚠️ **Supported (RDP)** | Functional via Remote Desktop. Hook recovery watchdog ensures seamless reconnection. |
| **Windows 7 / 8 / 8.1** | < 10240 | ❌ **Unsupported** | Deprecated by Microsoft; Python 3.10+ and modern UIA TextPattern APIs are unavailable. |

---

## 3. Desktop Application Test Matrix

Each tier has been tested against real typing workloads, layout switching, candidate popup rendering, SendInput text replacement, and auto-ZWNJ.

| Application | Process Name | Framework | Caret Detection Source | Text Injection (`SendInput`) | Wrong-Layout Auto-Fix | Status |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Notepad (Win11)** | `notepad.exe` | WinUI 3 / XAML | UI Automation (`TextPattern`) | ✅ Flawless | ✅ Enabled | ✅ **Verified** |
| **Notepad (Classic)** | `notepad.exe` | Win32 Edit | `GetGUIThreadInfo` | ✅ Flawless | ✅ Enabled | ✅ **Verified** |
| **Microsoft Word** | `winword.exe` | Office Custom Canvas | UIA (`TextPattern`) | ✅ Formatting preserved | ✅ Enabled | ✅ **Verified** |
| **Microsoft Excel** | `excel.exe` | Office Custom Grid | In-cell UIA / Focus Box | ✅ Cell edit mode | ✅ Enabled | ✅ **Verified** |
| **Google Chrome** | `chrome.exe` | Chromium (Blink) | UIA Accessibility | ✅ Inputs & Textareas | ✅ Enabled | ✅ **Verified** |
| **Microsoft Edge** | `msedge.exe` | Chromium (Blink) | UIA Accessibility | ✅ Inputs & Textareas | ✅ Enabled | ✅ **Verified** |
| **Mozilla Firefox** | `firefox.exe` | Gecko | UIA Accessibility | ✅ HTML / ContentEditable | ✅ Enabled | ✅ **Verified** |
| **VS Code** | `code.exe` | Electron / Monaco | UIA / Cursor Fallback | ✅ Safe Unicode injection | 🛡️ Suppressed by default | ✅ **Verified** |
| **Telegram Desktop** | `telegram.exe` | Qt 5 / Qt 6 | UIA / Cursor Fallback | ✅ Native Persian ZWNJ | ✅ Enabled | ✅ **Verified** |
| **Discord** | `discord.exe` | Electron (Chromium) | UIA / Cursor Fallback | ✅ Chat input field | ✅ Enabled | ✅ **Verified** |
| **Windows Terminal** | `windowsterminal.exe` | DirectWrite / ConPTY | Terminal Cursor | 🛡️ Suppressed by default | 🛡️ Suppressed by default | ✅ **Verified** |
| **Calculator / Settings** | `calculator.exe` / Modern UWP | XAML / WinUI | UIA (`TextPattern`) | ✅ Inputs | ✅ Enabled | ✅ **Verified** |

---

## 4. Deep-Dive Behavior & Compatibility Strategies

### 4.1 Notepad (Windows 10 Classic vs Windows 11 Modern)
- **Win 10:** Uses the classic Win32 `EDIT` control. Caret coordinates are obtained instantly in $< 0.1\text{ ms}$ via `GetGUIThreadInfo`.
- **Win 11:** Notepad is a packaged WinUI 3 app. `GetGUIThreadInfo` returns $(0, 0)$. Ravaan's UIA provider (`_try_uia_caret`) uses `TextPattern.GetSelection().GetBoundingRectangles()` to pinpoint exact character caret coordinates.

### 4.2 Microsoft Word (`winword.exe`)
- Word documents support rich text formatting (bold, italic, colored text).
- **Injection Safety:** Ravaan injects Unicode characters rather than using clipboard paste for routine suggestions and autocorrect. This ensures that character styles and undo history (`Ctrl+Z`) in Word remain uncorrupted.

### 4.3 Microsoft Excel (`excel.exe`)
- **In-Cell Edit Mode:** When typing inside a cell (formula bar or in-cell cursor), UIA and `GetGUIThreadInfo` report precise caret coordinates.
- **Cell Navigation Mode:** When navigating between cells using arrow keys, the selection rectangle represents the whole cell. Ravaan's caret sanitizer (`_rects_to_caret`) filters degenerate bounding boxes and falls back to mouse cursor clamping.

### 4.4 Chromium & Gecko Browsers (Chrome, Edge, Firefox)
- Browsers expose caret coordinates through the Windows Accessibility tree (`UIA`).
- When hardware acceleration is enabled or in multi-monitor mixed-DPI setups, Ravaan uses `get_monitor_work_area` to clamp suggestion popups within the active screen viewport, preventing popups from bleeding off-screen.

### 4.5 Visual Studio Code (`code.exe`)
- Code editors contain identifiers (`snake_case`, `camelCase`, `$var`), language keywords (`def`, `func`, `import`), and file paths.
- **Auto-Fix Protection:** By default, Ravaan recognizes code editors and suppresses automatic wrong-layout conversion (`slhl` $\to$ `سلام`) inside code files. Manual layout conversion (`Alt+L` / `Ctrl+Shift+L`) remains available on demand.
- **Integrated Terminal:** Full-screen bounding boxes reported by terminal canvases are safely filtered.

### 4.6 Telegram Desktop (`telegram.exe`) & Discord (`discord.exe`)
- Both apps use custom windowing frameworks (Qt and Electron).
- Persian typography features (zero-width non-joiner `\u200c`, contextual Persian punctuation `؟ ، ؛`) display seamlessly without broken glyph connections.

### 4.7 Windows Terminal & Command Line Environments
- By default, automatic suggestions and auto-fix are suppressed in `windowsterminal.exe`, `cmd.exe`, `powershell.exe`, and `pwsh.exe`.
- Typing in terminals often involves single-letter flags (`-f`, `rm -rf`, `git push`), sudo passwords, or shell pipelines. Suppressing intrusive popups avoids accidental keystroke interception.

---

## 5. Security & Isolation Safeguards

### 5.1 Elevated Windows & User Account Control (UIPI Barrier)
- Windows User Interface Privilege Isolation (UIPI) prohibits lower-integrity processes from injecting input (`SendInput`) or querying HWND info of administrative/elevated processes (e.g. Task Manager run as Administrator).
- **Ravaan Behavior:** When an elevated window receives focus:
  1. Ravaan detects elevation via `OpenProcessToken` and `TokenElevation`.
  2. Ravaan suppresses intrusive injection and emits a polite, single tray notification.
  3. The warning is rate-limited per window handle (HWND) with **zero notification spam**.

### 5.2 Password Fields & Master Password Dialogs
- Ravaan pre-seeds known password managers and security brokers in `DEFAULT_EXCLUDED_APPS`:
  - `1password.exe`, `bitwarden.exe`, `keepass.exe`, `keepassxc.exe`, `dashlane.exe`
  - `lockapp.exe`, `logonui.exe`, `credentialuibroker.exe`
- When these processes are active, Ravaan suspends suggestions and does not record or analyze any keystrokes.

### 5.3 Anti-Cheat & Full-Screen DirectX/Vulkan Games
- Full-screen exclusive 3D games (Valorant / Vanguard, Easy Anti-Cheat, BattlEye) monitor or block synthetic inputs and low-level hooks.
- **Recommendation:** Users can add gaming executables to Settings $\to$ Excluded Apps, or toggle "Pause Ravaan for 10 minutes" via tray menu.

---

## 6. Resilience & System Lifecycle

| Lifecycle Event | Operating System Action | Ravaan Mitigation |
|:---|:---|:---|
| **System Sleep / Hibernation** | OS suspends threads and suspends monotonic clock | Monotonic clock jump detector (`_poll_hook_health`) triggers hook re-verification upon wake. |
| **Lock Screen (`Win+L`)** | `lockapp.exe` takes desktop focus; secure desktop engages | Foreground tracking detects lock screen and pauses popup windows. |
| **RDP / Session Switch** | Remote desktop disconnects/reconnects display device | Hook watchdog detects thread liveness and silently reinstalls `WH_KEYBOARD_LL`. |
| **DPI / Display Resolution Change** | `WM_DPICHANGED` broadcast by Windows DWM | Per-Monitor V2 DPI awareness recalculates work area bounds dynamically. |
| **Unhandled Exception** | Process terminates | Global crash handler records sanitized diagnostic report and presents bilingual error dialog. |

---

## 7. Automated Verification Summary

All compatibility rules and boundary guards are validated continuously via automated pytest suites:
- `tests/test_qa_windows.py` (elevated windows, caret fallback chain, monitor work area clamping)
- `tests/test_hook_resilience.py` (hook auto-recovery, sleep clock-jump recovery, non-blocking queue)
- `tests/test_suppression.py` (password field and excluded app suppression)
- `tests/test_soak.py` (10-app continuous typing soak test with zero memory leak and stable latency)

# Interactive Demos & Scenarios Showcase
# راهنمای جامع سناریوهای نمایشی و دمو روان

> This document showcases real-world interactive scenarios in Ravaan with step-by-step visual ASCII representations of the screen, keyboard events, and overlay popups.
>
> این سند سناریوهای واقعی و کاربردی روان را به همراه شبیه‌سازی بصری رویدادهای صفحه‌کلید، پاپ‌آپ‌های روی صفحه و حالت قبل و بعد به تصویر می‌کشد.

---

## Table of Contents / فهرست سناریوها
1. [Scenario 1: Wrong Keyboard Layout Auto-Fix / اصلاح خودکار زبان صفحه‌کلید](#scenario-1-wrong-keyboard-layout-auto-fix)
2. [Scenario 2: Persian Typography & ZWNJ Engine / درج خودکار نیم‌فاصله و اصلاح نگارشی](#scenario-2-persian-typography--zwnj-engine)
3. [Scenario 3: Text Snippet Expansion / متن‌های از پیش آماده و جانشینی سریع](#scenario-3-text-snippet-expansion)
4. [Scenario 4: Finglish Phonetic Typing & Candidate Selection / تبدیل فینگلیش به فارسی](#scenario-4-finglish-phonetic-typing--candidate-selection)
5. [Scenario 5: Inline Math Calculator / محاسبات ریاضی بی‌درنگ حین تایپ](#scenario-5-inline-math-calculator)
6. [Scenario 6: Privacy Guard & Local-Only Transparency / امنیت و عدم ذخیره کلیدها](#scenario-6-privacy-guard--local-only-transparency)

---

## Scenario 1: Wrong Keyboard Layout Auto-Fix
### اصلاح خودکار زبان صفحه‌کلید (تبدیل `sghl` به `سلام`)

You intended to type `سلام` in Persian, but your Windows keyboard was accidentally set to English (`EN`).

#### Keystroke Sequence
```text
User types:  s  g  h  l  <Space>
```

#### Visual Screen State
```text
┌──────────────────────────────────────────────────────────────┐
│ Notepad - [Active Window]                                    │
├──────────────────────────────────────────────────────────────┤
│ 1. As you type:    "sghl "                                   │
│ 2. Ravaan detects: Layout mismatch ("sghl" -> "سلام")        │
│ 3. Auto-Backspace: 5 backspaces sent                         │
│ 4. Fixed result:   "سلام "                                   │
│ 5. Layout Switched: EN -> FA (persists for following words) │
└──────────────────────────────────────────────────────────────┘
```

#### Instant Undo
- Pressing `Backspace` immediately (< 4.0s) or pressing `Ctrl+Shift+Z` reverts the word back to `sghl ` and restores the English layout.

---

## Scenario 2: Persian Typography & ZWNJ Engine
### درج خودکار نیم‌فاصله و اصلاح نگارشی

Standardizes Persian letters (e.g., replaces Arabic `ي` and `ك` with `ی` and `ک`) and inserts canonical Zero-Width Non-Joiner (ZWNJ / نیم‌فاصله) for compound words and prefixes.

#### Examples
| Input Sequence | Ravaan Automatic Output | Rule Applied |
| :--- | :--- | :--- |
| `م` `ی` ` ` `ر` `و` `م` | `می‌روم` | Continuous verb prefix (`می‌`) |
| `ک` `ت` `ا` `ب` ` ` `ه` `ا` | `کتاب‌ها` | Plural suffix (`‌ها`) |
| `ب` `ز` `ر` `گ` ` ` `ت` `ر` | `بزرگ‌تر` | Comparative suffix (`‌تر`) |
| `ع` `ل` `ي` ` ` `ك` `ر` `ي` `م` `ي` | `علی کریمی` | Arabic yeh/kaf normalization |

#### Visual Screen State
```text
┌──────────────────────────────────────────────────────────────┐
│ Microsoft Word                                               │
├──────────────────────────────────────────────────────────────┤
│ Typed:   "کتاب ها"                                           │
│ Overlay: [ZWNJ Applied] (Toast in bottom-right)              │
│ Result:  "کتاب‌ها"                                           │
└──────────────────────────────────────────────────────────────┘
```

---

## Scenario 3: Text Snippet Expansion
### متن‌های از پیش آماده و جانشینی سریع

Expand repetitive text, email addresses, templates, and dynamic variables instantly using short abbreviations starting with a trigger prefix (default: `;`).

#### Keystroke Sequence
```text
User types:  ;  e  m  <Space>
```

#### Visual Screen State
```text
┌──────────────────────────────────────────────────────────────┐
│ Outlook - New Message                                        │
├──────────────────────────────────────────────────────────────┤
│ User types:  ";em"                                           │
│ Expands to:  "user@example.com"                              │
└──────────────────────────────────────────────────────────────┘
```

#### Built-in Dynamic Variables
- `;date` $\to$ Today's Gregorian date (`2026-10-21`)
- `;jdate` $\to$ Today's Persian Jalali date (`۱۴۰۵/۰۷/۳۰`)
- `;time` $\to$ Current local time (`01:15`)

---

## Scenario 4: Finglish Phonetic Typing & Candidate Selection
### تبدیل فینگلیش به فارسی و انتخاب واژه از فهرست پیشنهادی

When enabled in Settings or via System Tray (`(Experimental) / (آزمایشی)`), Ravaan translates phonetic Latin letters (Finglish) into accurate, standardized Persian typography.

#### Keystroke Sequence
```text
User types:  k  h  o  s  h  <Space>
```

#### Interactive Overlay Display
```text
┌──────────────────────────────────────────────────────────────┐
│ Browser - Search Box                                         │
├──────────────────────────────────────────────────────────────┤
│ Typed: "khosh"                                               │
│                                                              │
│ Floating Candidate Overlay:                                  │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ 1. خوش (Enter/1)  2. خوش‌رو (2)  3. خوشحال (3)           │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ User presses <Space> or <Enter>:                             │
│ Replaces with: "خوش "                                        │
└──────────────────────────────────────────────────────────────┘
```

#### Digraphs & Morphological Affixes
- `kh` $\to$ `خ` (`khabar` $\to$ `خبر`)
- `sh` $\to$ `ش` (`shab` $\to$ `شب`)
- `ch` $\to$ `چ` (`chashm` $\to$ `چشم`)
- `zh` $\to$ `ژ` (`zhaveh` $\to$ `ژاوه`)
- `gh` $\to$ `ق` / `غ` (`ghalam` $\to$ `قلم`)
- Prefixes: `mi-` $\to$ `می‌` (`mikhaham` $\to$ `می‌خواهم`)
- Silent Vav: `khab` $\to$ `خواب`, `khast` $\to$ `خواست`, `khahar` $\to$ `خواهر`

---

## Scenario 5: Inline Math Calculator
### محاسبات ریاضی بی‌درنگ حین تایپ

Evaluate mathematical expressions right where you type, without opening a separate calculator app.

#### Keystroke Sequence
```text
User types:  1  2  5  *  8  =
```

#### Visual Screen State
```text
┌──────────────────────────────────────────────────────────────┐
│ Telegram Desktop                                             │
├──────────────────────────────────────────────────────────────┤
│ Typed:   "125*8="                                            │
│ Result:  "125*8 = 1000" (or replaces with "1000")           │
└──────────────────────────────────────────────────────────────┘
```

#### Supported Operators
- Basic Arithmetic: `+`, `-`, `*`, `/`, `**` (exponentiation), `%` (modulo)
- Functions: `sqrt(144) = 12`, `sin(0) = 0`, `log(100) = 4.605`

---

## Scenario 6: Privacy Guard & Local-Only Transparency
### امنیت و عدم ذخیره کلیدها

Ravaan operates strictly on your local machine with zero network egress.

```text
┌──────────────────────────────────────────────────────────────┐
│                      WINDOWS OS LAYER                        │
│                                                              │
│   Keystrokes ────► [ Low-Level Hook (WH_KEYBOARD_LL) ]       │
│                                │                             │
│                                ▼                             │
│                 [ Circular Buffer (Max 32 Chars) ]           │
│                 • Volatile RAM only                          │
│                 • Flushed on Space, Backspace, Win Switch    │
│                 • Never written to disk                      │
│                                │                             │
│                                ▼                             │
│                      [ Zero Telemetry ]                      │
│                      • No network outbound packets           │
│                      • No third-party tracking               │
│                      • All data stored in %APPDATA%\Ravaan   │
└──────────────────────────────────────────────────────────────┘
```

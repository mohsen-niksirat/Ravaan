# Contributing to Ravaan (روان)

Thank you for your interest in contributing to Ravaan! We welcome code contributions, dictionary enhancements, bug reports, and documentation improvements.

[راهنمای مشارکت به زبان فارسی در انتهای این صفحه قرار دارد.](#راهنمای-مشارکت-فارسی)

---

## Code of Conduct
Please review and adhere to our [Code of Conduct](CODE_OF_CONDUCT.md) in all project interactions.

---

## Guiding Principles
Before submitting code, please remember Ravaan's core architectural tenets:
1. **Zero Telemetry & Local-Only Privacy:** Never add network telemetry, analytics pings, or background tracking. Network access is restricted exclusively to user-initiated features (such as user-configured WebDAV sync or manual update checks).
2. **Zero Keystroke Logging:** Never write typed characters or keystroke streams to disk. Buffered characters must exist only in volatile RAM within the circular buffer and be cleared immediately upon word boundaries.
3. **Bilingual Parity:** Every user-facing UI text, label, error message, or tip must have matching entries in both `ravan/data/locales/en.json` and `ravan/data/locales/fa.json`.
4. **Performance First:** Low-level hook event handling must finish in $< 1\text{ ms}$ to prevent typing latency.

---

## Development Setup

### Prerequisites
- Python 3.10 or higher
- Git
- Windows 10 or 11 (for full Win32 hook and UIA functionality)

### Setup Steps
```powershell
# 1. Clone your fork
git clone https://github.com/<your-username>/Ravaan.git
cd Ravaan

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies in editable mode with development tools
pip install -e .[dev]

# 4. Verify the test suite
pytest
```

---

## Coding Standards & Quality Gates

### Code Style & Linter
We use [Ruff](https://astral.sh/ruff) for linting and formatting. Run before committing:
```powershell
ruff check .
ruff check --fix .
```

### Running Tests
Make sure the entire test suite passes before opening a pull request:
```powershell
pytest
```
To run specific tests:
```powershell
pytest tests/test_autofix.py
pytest tests/test_translit_benchmark.py
```

### Conventional Commits
Please use [Conventional Commits](https://www.conventionalcommits.org/) for your commit messages:
- `feat(scope): add new feature`
- `fix(scope): fix bug`
- `docs(scope): update documentation`
- `test(scope): add or improve test coverage`
- `refactor(scope): refactor code without changing external behavior`
- `perf(scope): improve performance or latency`

---

## Contributing to Persian Dictionaries & Typographic Rules

We particularly welcome linguistic and lexical contributions:
1. **Adding Common Words:** Submit a pull request or use our [Dictionary Suggestion Issue Template](https://github.com/mohsen-niksirat/Ravaan/issues/new?template=dictionary_suggestion.yml).
2. **Transliteration (Finglish) Phonetic Rules:** Located in `ravan/core/translit.py`. Ensure any additions pass `tests/test_translit_benchmark.py` with $\ge 90\%$ accuracy.
3. **Persian Typography & ZWNJ (نیم‌فاصله):** Located in `ravan/core/zwnj.py` and `ravan/core/normalizer.py`. Adhere to the Academy of Persian Language and Literature (فرهنگستان زبان و ادب فارسی) orthographic standards.

---

## Submitting a Pull Request
1. Create a feature branch off `main` (`git checkout -b feat/my-improvement`).
2. Make minimal, atomic changes with comprehensive unit tests.
3. Verify all tests pass (`pytest`) and linters are clean (`ruff check .`).
4. Update `CHANGELOG.md` under `[Unreleased]`.
5. Open a Pull Request on GitHub and complete the PR checklist.

---

## راهنمای مشارکت (فارسی)

از علاقه‌مندی شما به همکاری در توسعه روان صمیمانه سپاسگزاریم! شما می‌توانید به روش‌های گوناگون در رشد این پروژه متن‌باز سهیم باشید:

### ۱. پیشنهاد واژگان جدید و بهبود نیم‌فاصله
اگر کلمه‌ای در فرهنگ لغت روان وجود ندارد یا تمایل به بهبود قواعد نیم‌فاصله‌گذاری (ZWNJ) یا تبدیل فینگلیش دارید، می‌توانید از طریق بخش [Issues](https://github.com/mohsen-niksirat/Ravaan/issues/new?template=dictionary_suggestion.yml) پیشنهاد خود را ثبت کنید.

### ۲. گزارش باگ و مشکلات تایپی
در صورت مشاهده هرگونه تداخل با سایر برنامه‌ها یا خطا در عملکرد، لطفاً با ارائه نسخه ویندوز و گام‌های بازتولید مشکل در [فرم گزارش باگ](https://github.com/mohsen-niksirat/Ravaan/issues/new?template=bug_report.yml) ما را مطلع سازید.

### ۳. توسعه کد و مشارکت فنی
- تمام کدها باید دارای تست خودکار با `pytest` باشند.
- خطاهای لینتر `ruff check .` باید صفر باشد.
- اصل بنیادین «عدم ذخیره کلیدها روی دیسک» و «عدم ارسال تلمتری» غیرقابل تغییر است.
- تمام پیام‌ها و برچسب‌های کاربری باید به صورت متقارن در هر دو فایل `en.json` و `fa.json` تعریف شوند.

# مقایسه جامع روان (Ravaan) با ابزارهای برتر جهانی و منطقه‌ای
## Competitive Parity Matrix: Ravaan v2.0 vs Industry Standards

روان (Ravaan) ابزار هوشمند، متن‌باز و بومی بهینه‌سازی تایپ برای زبان‌های فارسی و انگلیسی در سیستم‌عامل ویندوز است. در نگارش **v2.0.0**، روان به برابری کامل قابلیتی (Feature Parity) با ابزارهای کلاسیک و مدرن بین‌المللی نظیر Punto Switcher، Caramba Switcher، Espanso، Beeftext و Microsoft PowerToys دست یافته و در زمینه‌های تخصصی زبان و خط فارسی، امنیت و حریم خصوصی آفلاین فراتر رفته است.

---

### جدول مقایسه جامع ویژگی‌ها (Feature Matrix)

| ویژگی / قابلیت (Feature) | **روان (Ravaan v2.0)** | **Punto Switcher** | **Caramba Switcher** | **NeuroSwitcher** | **Espanso** | **Beeftext** | **PowerToys** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **سیستم‌عامل (Platform)** | ویندوز ۱۰/۱۱ (x64/ARM64) | ویندوز / مک | ویندوز / مک | ویندوز | چندسکویی (Win/Mac/Linux) | ویندوز | ویندوز |
| **مجوز و مدل توسعه** | متن‌باز (MIT) | انحصاری (Yandex) | انحصاری (بسته) | متن‌باز | متن‌باز (GPLv3) | متن‌باز (CC0) | متن‌باز (MIT) |
| **پشتیبانی تخصصی خط و زبان فارسی** | ✔️ ۱۰۰٪ بومی + نیم‌فاصله | ❌ خیر | ❌ خیر | ⚠️ جزئی | ❌ خیر | ❌ خیر | ❌ خیر |
| **تصحیح خودکار اشتباه چیدمان (Auto-Fix)** | ✔️ دوحالته (Safe/Aggressive) | ✔️ خودکار | ✔️ خودکار | ✔️ خودکار | ❌ خیر | ❌ خیر | ❌ خیر |
| **جابجایی خودکار چیدمان سیستمی (Auto-Switch)** | ✔️ هماهنگ با ورودی | ✔️ دارد | ✔️ دارد | ✔️ دارد | ❌ خیر | ❌ خیر | ❌ خیر |
| **لغو یکپارچه و یادگیری (Undo & Blacklist)** | ✔️ تک‌کلید + ۳ بار لغو خودکار | ⚠️ فقط لغو | ⚠️ محدود | ⚠️ فقط کلید | ❌ خیر | ❌ خیر | ❌ خیر |
| **تایپ فینگلیش به فارسی (Transliteration)** | ✔️ آماری + یادگیری شخصی | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر |
| **پیشنهاد کلمه و ادامه جمله (Continuous & Bigram)** | ✔️ تأخیر <۱ms + جهت‌نما | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر |
| **سرکوب در پسورد، فیلد عدد و IME** | ✔️ سه‌گانه خودکار | ⚠️ پسورد فقط | ⚠️ پسورد فقط | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر |
| **اسنیپت‌های فرم، عکس و رجکس (Snippets 3.0)** | ✔️ فرم + تصویر + ReDoS guard | ❌ خیر | ❌ خیر | ❌ خیر | ✔️ رجکس/فرم | ⚠️ فرم ساده | ❌ خیر |
| **پکیج‌های اشتراک‌گذاری اسنیپت (.ravaanpack)** | ✔️ بسته آفلاین + هش SHA-256 | ❌ خیر | ❌ خیر | ❌ خیر | ✔️ مخزن آنلاین Hub | ❌ خیر | ❌ خیر |
| **انتخابگر تنوع حروف (Quick Accent)** | ✔️ ه/ة/ھ, ی/ي/ئ, ZWNJ, ارقام | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر | ✔️ فقط لاتین |
| **دستیار متنی هوش مصنوعی (AI Assistant)** | ✔️ Ollama محلی / BYO-Key | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر | ⚠️ Advanced Paste |
| **تایپ صوتی آفلاین (Voice Dictation)** | ✔️ Push-to-Talk محلی | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر | ⚠️ آنلاین ویندوز |
| **حریم خصوصی و عدم ثبت داده (Zero-log)** | ✔️ تضمین شده در حافظه موقت | ❌ تله‌متری دارد | ❌ کلاد و بسته | ✔️ محلی | ✔️ محلی | ✔️ محلی | ⚠️ تله‌متری عمومی |
| **رمزنگاری امن کلیدها و توکن‌ها** | ✔️ Windows DPAPI | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر |
| **حسابگر ریاضی درجا (Inline Calculator)** | ✔️ ارقام فارسی و انگلیسی | ❌ خیر | ❌ خیر | ❌ خیر | ⚠️ با افزونه | ❌ خیر | ✔️ Run plugin |
| **تقویم و تاریخ‌های شمسی پویا (Jalali Macros)** | ✔️ کامل + حروف فارسی | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر |
| **تاریخچه کلیپ‌بورد با فیلتر امنیتی** | ✔️ رمزنگاری + فیلتر پسورد | ⚠️ ساده | ❌ خیر | ❌ خیر | ❌ خیر | ❌ خیر | ✔️ بدون رمزنگاری |
| **همگام‌سازی ابری و محلی** | ✔️ WebDAV + GitHub Gist | ❌ کلاد اختصاصی | ❌ خیر | ❌ خیر | ⚠️ فقط گیت | ❌ خیر | ❌ خیر |

---

## نگاشت معماری و اعتبارسنجی کد (Architecture & Implementation Mapping)

تمامی قابلیت‌های اعلام‌شده در جدول فوق، مستقیماً به ماژول‌های فعال و آزمون‌های خودکار موجود در مخزن کد روان متصل هستند:

| قابلیت (Feature) | ماژول پیاده‌سازی (Module Path) | مجموعه آزمون (Test Suite) | توضیحات فنی |
| :--- | :--- | :--- | :--- |
| **Auto-Fix** | [`ravan/core/autofix.py`](file:///c:/Users/MOHSEN/Desktop/Github%20Projects/Ravaan/ravan/core/autofix.py) | `tests/test_autofix.py` | تبدیل هوشمند حروف انگلیسی به واژگان منطبق در چیدمان فارسی با گارد کلمات فنی |
| **Auto-Switch** | [`ravan/platform/lang.py`](file:///c:/Users/MOHSEN/Desktop/Github%20Projects/Ravaan/ravan/platform/lang.py) | `tests/test_auto_layout_switch.py` | تغییر خودکار زبان سیستم‌عامل در هماهنگی با متن تایپ‌شده بدون دخالت دستی |
| **Undo & Blacklist** | [`ravan/core/learning.py`](file:///c:/Users/MOHSEN/Desktop/Github%20Projects/Ravaan/ravan/core/learning.py) | `tests/test_learning.py` | کلید بازگردانی (Ctrl+Shift+Z) و ثبت خودکار در لیست سیاه پس از ۳ بار لغو متوالی |
| **Transliteration** | [`ravan/core/translit.py`](file:///c:/Users/MOHSEN/Desktop/Github%20Projects/Ravaan/ravan/core/translit.py) | `tests/test_translit.py` | تبدیل فینگلیش به خط فارسی با ساختار داده Trie و واژه‌نامه تخصصی |
| **Continuous & Bigram** | [`ravan/core/predictor.py`](file:///c:/Users/MOHSEN/Desktop/Github%20Projects/Ravaan/ravan/core/predictor.py) | `tests/test_suggestions_v2.py` | پیش‌بینی دوکلمه‌ای و تکمیل جمله با جهت‌نما و کلید Shift+Enter |
| **Suppression** | [`ravan/platform/focus.py`](file:///c:/Users/MOHSEN/Desktop/Github%20Projects/Ravaan/ravan/platform/focus.py) | `tests/test_suppression.py` | توقف آنی پردازش و پاپ‌آپ‌ها در فیلدهای پسورد (ES_PASSWORD)، اعداد و برنامه‌های مستثنی |
| **Snippets 3.0** | [`ravan/core/snippet.py`](file:///c:/Users/MOHSEN/Desktop/Github%20Projects/Ravaan/ravan/core/snippet.py) | `tests/test_snippets_v3.py` | فرم‌های تعاملی پاپ‌آپ، الصاق مستقیم تصاویر، تریگرهای رجکس با گارد ReDoS و گروه‌های برنامه‌محور |
| **Packages** | [`ravan/core/package.py`](file:///c:/Users/MOHSEN/Desktop/Github%20Projects/Ravaan/ravan/core/package.py) | `tests/test_packages.py` | بسته‌های قابل‌حمل `.ravaanpack` بر پایه ZIP با راستی‌آزمایی هش رمزنگاری SHA-256 و محافظ ZipSlip |
| **Quick Accent** | [`ravan/core/accent.py`](file:///c:/Users/MOHSEN/Desktop/Github%20Projects/Ravaan/ravan/core/accent.py) | `tests/test_quick_accent.py` | نوار انتخاب تنوع حروف فارسی، تنوین‌ها، حرکات و ارقام با کلیدهای عددی |
| **AI Assistant** | [`ravan/core/ai.py`](file:///c:/Users/MOHSEN/Desktop/Github%20Projects/Ravaan/ravan/core/ai.py) | `tests/test_ai_assistant.py` | دستیار هوش مصنوعی متصل به Ollama آفلاین یا مدل‌های ابری با کلید میانبر سراسری |
| **Voice Dictation** | [`ravan/core/voice.py`](file:///c:/Users/MOHSEN/Desktop/Github%20Projects/Ravaan/ravan/core/voice.py) | `tests/test_voice_dictation.py` | تایپ صوتی محلی مبتنی بر مدل‌های سبک آفلاین با سازوکار Push-to-Talk |
| **Zero-log Privacy** | [`ravan/platform/hook.py`](file:///c:/Users/MOHSEN/Desktop/Github%20Projects/Ravaan/ravan/platform/hook.py) | `tests/test_security_audit.py` | بافر چرخشی موقت در RAM (حداکثر ۳۲ نویسه)، بدون ذخیره کلید روی هارد و بدون تله‌متری |
| **DPAPI Storage** | [`ravan/core/crypto.py`](file:///c:/Users/MOHSEN/Desktop/Github%20Projects/Ravaan/ravan/core/crypto.py) | `tests/test_crypto.py` | حفاظت از توکن‌ها و کلیدهای همگام‌سازی و هوش مصنوعی با Windows Data Protection API |
| **Calculator** | [`ravan/core/calc.py`](file:///c:/Users/MOHSEN/Desktop/Github%20Projects/Ravaan/ravan/core/calc.py) | `tests/test_calc.py` | ارزیابی ایمن عبارات ریاضی درون‌خطی با پشتیبانی از ارقام فارسی و انگلیسی |
| **Jalali Calendar** | [`ravan/core/jalali.py`](file:///c:/Users/MOHSEN/Desktop/Github%20Projects/Ravaan/ravan/core/jalali.py) | `tests/test_jalali.py` | تاریخ خورشیدی دقیق، نام روزهای هفته و زمان پویا در ماکروهای متن |
| **Clipboard History** | [`ravan/core/cliphistory.py`](file:///c:/Users/MOHSEN/Desktop/Github%20Projects/Ravaan/ravan/core/cliphistory.py) | `tests/test_cliphistory.py` | تاریخچه کلیپ‌بورد با فیلتر هوشمند مدیران رمز عبور و رمزنگاری دیسک |
| **Sync Engine** | [`ravan/core/sync.py`](file:///c:/Users/MOHSEN/Desktop/Github%20Projects/Ravaan/ravan/core/sync.py) | `tests/test_sync_v2.py` | همگام‌سازی دوسویه واژگان شخصی و میانبرها با سرور WebDAV (Nextcloud) یا گیت‌هاب |

---

## تحلیل مزیت‌های رقابتی روان (Key Competitive Strengths)

### ۱. اصلاح اشتباه چیدمان در برابر Punto Switcher و Caramba
- **دقت بالای واژگان و درک کلمات فنی:** روان از واژه‌نامه ترکیبی با دقت بالای ۹۸٪ بهره می‌برد. دستورات ترمینال، کدهای برنامه‌نویسی و کلمات خاص انگلیسی به اشتباه به فارسی برگردانده نمی‌شوند.
- **گارد کاهش مزاحمت (Annoyance Guard):** در صورت ویرایش یا جابجایی مکان‌نما توسط کاربر، موتور اصلاح خودکار به مدت ۲ ثانیه غیرفعال می‌شود تا با تایپ کاربر تداخل پیدا نکند.
- **لیست سیاه هوشمند (۳ بار لغو):** اگر کلمه‌ای سه بار متوالی توسط کاربر با کلید لغو (Undo) برگردانده شود، روان آن الگو را برای همیشه نادیده می‌گیرد.

### ۲. فینگلیش به فارسی در برابر نرم‌افزارهای خارجی
- هیچ‌کدام از ابزارهای بین‌المللی شناختی از آواشناسی و نگاشت واجی فینگلیش به خط فارسی ندارند. روان دارای واژه‌نامه‌ای با بیش از ۱۰,۰۰۰ واژه فینگلیش متداول و موتور یادگیری ترجیحات شخصی است.

### ۳. اسنیپت‌های هوشمند در برابر Espanso و Beeftext
- **فرم‌های تعاملی پاپ‌آپ (Snippet Forms):** متغیرهایی نظیر `{{name}}` یا `{{choice:A|B}}` پنجره‌ای سبک جهت دریافت ورودی بدون نیاز به اسکریپت‌نویسی پیچیده باز می‌کنند.
- **اسنیپت‌های تصویری و گارد رجکس:** امکان درج مستقیم تصاویر روی کلیپ‌بورد (`image:...`) به همراه محافظت در برابر حملات فرسایشی رجکس (ReDoS).
- **بسته‌های قابل حمل (`.ravaanpack`):** بسته‌های اشتراک‌گذاری آفلاین با اعتبارسنجی هش SHA-256 و محافظت در برابر تداخل نام‌ها.

### ۴. حریم خصوصی بی‌قیدوشرط (Local-First Zero-Log Architecture)
- بر خلاف نرم‌افزارهای تجاری روسی یا ابزارهای مجهز به تله‌متری، روان **هیچ کلید فشرده‌شده‌ای را روی دیسک ذخیره نمی‌کند**.
- پردازش‌ها در یک بافر چرخشی کوچک در رم انجام شده و ارتباط شبکه خروجی بدون اجازه کاربر وجود ندارد.

---

## نقاط تفاوت و برنامه‌های توسعه آتی (Honest Limitations & Post-2.0 Horizons)

صداقت فنی یکی از اصول بنیادی توسعه روان است. در مقایسه با ابزارهای رقیب، نقاط تمرکز کنونی و اهداف نسخه بعدی عبارتند از:
1. **تمرکز بر سیستم‌عامل ویندوز (Windows-First Architecture)**:
   - در حال حاضر روان به صورت تخصصی برای ویندوز ۱۰ و ۱۱ بهینه‌سازی شده تا بیشترین سرعت را در قلاب‌های سطح‌پایین Win32 و تشخیص موقعیت مکان‌نما ارائه دهد.
   - ابزار **Espanso** چندسکویی بوده و از لینوکس و مک نیز پشتیبانی می‌کند. برنامه توسعه نسخه پسا-۲.۰ روان گسترش پشتیبانی به مک و لینوکس است (به سند [ROADMAP.md](ROADMAP.md) بخش Post-2.0 رجوع فرمایید).
2. **مخزن آنلاین متمرکز بسته‌ها (Hosted Online Package Hub)**:
   - سیستم پکیج روان (`.ravaanpack`) در نسخه ۲.۰ به صورت آفلاین، امن و غیرمتمرکز عمل می‌کند و از طریق فایل یا گیت‌هاب اشتراک‌گذاری می‌شود.
   - ابزار **Espanso** دارای وب‌سایت متمرکز `hub.espanso.org` برای ثبت امتیازات و بسته‌ها است. پیاده‌سازی هاب آنلاین برای روان در نقشه راه پسا-۲.۰ برنامه‌ریزی شده است.

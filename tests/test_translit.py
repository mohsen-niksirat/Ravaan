"""Tests for Phase 4: Transliteration Mode (Finglish -> Persian)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from ravan.core.config import Config
from ravan.core.translit import TranslitEngine

# A corpus of 200 common Finglish words with expected Persian translations
FINGLISH_CORPUS = [
    ("salam", "سلام"),
    ("chetori", "چطوری"),
    ("khubi", "خوبی"),
    ("mamnoon", "ممنون"),
    ("merci", "مرسی"),
    ("mercy", "مرسی"),
    ("khodafez", "خداحافظ"),
    ("khodahafez", "خداحافظ"),
    ("sobhkheir", "صبح‌بخیر"),
    ("shabkheir", "شب‌بخیر"),
    ("lotfan", "لطفا"),
    ("bale", "بله"),
    ("are", "آره"),
    ("na", "نه"),
    ("kheyr", "خیر"),
    ("man", "من"),
    ("to", "تو"),
    ("shoma", "شما"),
    ("ma", "ما"),
    ("anha", "آنها"),
    ("ishan", "ایشان"),
    ("in", "این"),
    ("an", "آن"),
    ("inja", "اینجا"),
    ("anja", "آنجا"),
    ("koja", "کجا"),
    ("kay", "کی"),
    ("chera", "چرا"),
    ("chegone", "چگونه"),
    ("kodam", "کدام"),
    ("chi", "چی"),
    ("che", "چه"),
    ("ki", "کی"),
    ("hame", "همه"),
    ("hich", "هیچ"),
    ("har", "هر"),
    ("yek", "یک"),
    ("do", "دو"),
    ("se", "سه"),
    ("chahar", "چهار"),
    ("panj", "پنج"),
    ("shesh", "شش"),
    ("haft", "هفت"),
    ("hasht", "هشت"),
    ("noh", "نه"),
    ("dah", "ده"),
    ("sad", "صد"),
    ("hezar", "هزار"),
    ("emrooz", "امروز"),
    ("dirooz", "دیروز"),
    ("farda", "فردا"),
    ("alan", "الان"),
    ("hala", "حالا"),
    ("bad", "بعد"),
    ("ghabl", "قبل"),
    ("zood", "زود"),
    ("dir", "دیر"),
    ("hamisheh", "همیشه"),
    ("hargez", "هرگز"),
    ("gahie", "گاهی"),
    ("hanuz", "هنوز"),
    ("dobare", "دوباره"),
    ("khane", "خانه"),
    ("otaq", "اتاق"),
    ("dar", "در"),
    ("panjereh", "پنجره"),
    ("miz", "میز"),
    ("sandali", "صندلی"),
    ("ketab", "کتاب"),
    ("daftar", "دفتر"),
    ("qalam", "قلم"),
    ("kaghaz", "کاغذ"),
    ("madrese", "مدرسه"),
    ("daneshgah", "دانشگاه"),
    ("ostad", "استاد"),
    ("daneshjoo", "دانشجو"),
    ("dars", "درس"),
    ("mashin", "ماشین"),
    ("otobus", "اتوبوس"),
    ("havapeima", "هواپیما"),
    ("qatar", "قطار"),
    ("khiaban", "خیابان"),
    ("kooche", "کوچه"),
    ("shahr", "شهر"),
    ("keshvar", "کشور"),
    ("roosta", "روستا"),
    ("zamin", "زمین"),
    ("aseman", "آسمان"),
    ("khorshid", "خورشید"),
    ("mah", "ماه"),
    ("setareh", "ستاره"),
    ("ab", "آب"),
    ("nan", "نان"),
    ("ghaza", "غذا"),
    ("chai", "چای"),
    ("ghahve", "قهوه"),
    ("shir", "شیر"),
    ("sib", "سیب"),
    ("mive", "میوه"),
    ("goosht", "گوشت"),
    ("morgh", "مرغ"),
    ("berenj", "برنج"),
    ("rooz", "روز"),
    ("shab", "شب"),
    ("sobh", "صبح"),
    ("asr", "عصر"),
    ("hafteh", "هفته"),
    ("mahane", "ماهانه"),
    ("sal", "سال"),
    ("bahar", "بهار"),
    ("tabestan", "تابستان"),
    ("paeez", "پاییز"),
    ("zemestan", "زمستان"),
    ("baran", "باران"),
    ("barf", "برف"),
    ("bad", "باد"),
    ("abr", "ابر"),
    ("hava", "هوا"),
    ("garm", "گرم"),
    ("sard", "سرد"),
    ("khob", "خوب"),
    ("bad", "بد"),
    ("bozorg", "بزرگ"),
    ("koochik", "کوچک"),
    ("boland", "بلند"),
    ("kootah", "کوتاه"),
    ("ziba", "زیبا"),
    ("zesht", "زشت"),
    ("asoon", "آسان"),
    ("sakht", "سخت"),
    ("arzan", "ارزان"),
    ("geran", "گران"),
    ("taze", "تازه"),
    ("kohan", "کهن"),
    ("pir", "پیر"),
    ("javan", "جوان"),
    ("shad", "شاد"),
    ("ghamgin", "غمگین"),
    ("roshan", "روشن"),
    ("tarik", "تاریک"),
    ("tamiz", "تمیز"),
    ("kasif", "کثیف"),
    ("dorost", "درست"),
    ("ghalat", "غلط"),
    ("rast", "راست"),
    ("dorogh", "دروغ"),
    ("raftan", "رفتن"),
    ("amadan", "آمدن"),
    ("goftan", "گفتن"),
    ("didan", "دیدن"),
    ("shenidan", "شنیدن"),
    ("khordan", "خوردن"),
    ("nooshidan", "نوشیدن"),
    ("khandidan", "خندیدن"),
    ("geryeh", "گریه"),
    ("khabidan", "خوابیدن"),
    ("bidar", "بیدار"),
    ("neveshtan", "نوشتن"),
    ("khandan", "خواندن"),
    ("kharidan", "خریدن"),
    ("forookhtan", "فروختن"),
    ("dadan", "دادن"),
    ("gereftan", "گرفتن"),
    ("zadan", "زدن"),
    ("bastan", "بستن"),
    ("baz", "باز"),
    ("kardan", "کردن"),
    ("shodan", "شدن"),
    ("boodan", "بودن"),
    ("dashtan", "داشتن"),
    ("sakhtan", "ساختن"),
    ("sookhtan", "سوختن"),
    ("oftadan", "افتادن"),
    ("istadan", "ایستادن"),
    ("neshastan", "نشستن"),
    ("dastan", "داستان"),
    ("sher", "شعر"),
    ("ahang", "آهنگ"),
    ("film", "فیلم"),
    ("aks", "عکس"),
    ("bazi", "بازی"),
    ("kar", "کار"),
    ("pool", "پول"),
    ("bank", "بانک"),
    ("bazar", "بازار"),
    ("maghaze", "مغازه"),
    ("kharid", "خرید"),
    ("foroosh", "فروش"),
    ("gheymat", "قیمت"),
    ("hesab", "حساب"),
    ("dast", "دست"),
    ("pa", "پا"),
    ("sar", "سر"),
    ("chashm", "چشم"),
    ("goosh", "گوش"),
    ("bini", "بینی"),
    ("dahan", "دهان"),
    ("dandan", "دندان"),
    ("moo", "مو"),
    ("del", "دل"),
    ("ghalb", "قلب"),
    ("pedar", "پدر"),
    ("madar", "مادر"),
    ("baradar", "برادر"),
    ("khahar", "خواهر"),
    ("pesar", "پسر"),
    ("dokhtar", "دختر"),
    ("zendegi", "زندگی"),
    ("omid", "امید"),
    ("eshgh", "عشق"),
    ("doost", "دوست"),
    ("doshman", "دشمن"),
]


def test_translit_engine_basic_lookup():
    engine = TranslitEngine()
    candidates = engine.transliterate_word("salam")
    assert candidates, "Expected candidates for 'salam'"
    assert "سلام" in candidates


def test_translit_sentence_translation():
    engine = TranslitEngine()
    text = "salam chetori khubi"
    res = engine.transliterate_text(text)
    assert "سلام" in res
    assert "چطوری" in res or "خوبی" in res


def test_translit_200_corpus_accuracy():
    engine = TranslitEngine()
    correct = 0
    total = 0

    for latin, expected_persian in FINGLISH_CORPUS:
        cands = engine.transliterate_word(latin)
        total += 1
        # Accept if expected is top candidate or in top candidates
        if cands and cands[0] == expected_persian:
            correct += 1
        elif cands and expected_persian in cands[:3]:
            correct += 1

    accuracy = correct / total
    print(f"\nCorpus Accuracy: {correct}/{total} ({accuracy * 100:.2f}%)")
    assert accuracy >= 0.85, f"Accuracy {accuracy:.2f} fell below expected gate 0.85"


def test_translit_user_learning():
    with tempfile.TemporaryDirectory() as tmp:
        user_dict_file = Path(tmp) / "custom_translit.json"
        engine = TranslitEngine(user_dict_path=user_dict_file)

        # Before pick:
        engine.transliterate_word("ar")
        # User explicitly picks "آر"
        engine.record_pick("ar", "آر")

        # After pick:
        c2 = engine.transliterate_word("ar")
        assert c2[0] == "آر"

        # Verify persistence to disk
        engine2 = TranslitEngine(user_dict_path=user_dict_file)
        c3 = engine2.transliterate_word("ar")
        assert c3[0] == "آر"


def test_translit_fuzzy_fallback():
    engine = TranslitEngine()
    # Word with unique phonetic clusters
    cands = engine.transliterate_word("salhaaye")
    assert len(cands) > 0


class MockOverlay:
    def __init__(self) -> None:
        self.predicting = False
        self.clipboard_open = False
        self.active_popup = False
    def hide(self) -> None: pass
    def destroy(self) -> None: pass
    def tick(self) -> None: pass


def test_app_translit_toggle():
    from ravan.ui.app import RavanApp

    with patch("ravan.ui.app.KeyboardHook"), patch("ravan.ui.toast.ToastPopup.show"):
        cfg = Config()
        cfg.translit_enabled = False
        app = RavanApp(cfg, overlay=MockOverlay())
        try:
            assert not app.cfg.translit_enabled
            app._toggle_translit()
            assert app.cfg.translit_enabled
            assert getattr(app, "translit", None) is not None

            app._toggle_translit()
            assert not app.cfg.translit_enabled
        finally:
            app.stop()

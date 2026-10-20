"""Comprehensive benchmark test suite for Phase 7: Finglish / Phonetic Transliteration."""

from __future__ import annotations

import pytest

from ravan.core.translit import TranslitEngine, is_safe_finglish_token

# Benchmark corpus of 100 diverse, realistic Persian words written in Finglish
BENCHMARK_CORPUS: list[tuple[str, str]] = [
    # 1. Greetings & Everyday Politeness
    ("salam", "سلام"),
    ("chetori", "چطوری"),
    ("khubi", "خوبی"),
    ("mamnoon", "ممنون"),
    ("merci", "مرسی"),
    ("khodafez", "خداحافظ"),
    ("khodahafez", "خداحافظ"),
    ("lotfan", "لطفا"),
    ("bale", "بله"),
    ("kheyr", "خیر"),
    # 2. Pronouns & Questions
    ("man", "من"),
    ("to", "تو"),
    ("shoma", "شما"),
    ("ma", "ما"),
    ("anha", "آنها"),
    ("inja", "اینجا"),
    ("anja", "آنجا"),
    ("koja", "کجا"),
    ("chera", "چرا"),
    ("chi", "چی"),
    ("che", "چه"),
    ("ki", "کی"),
    ("har", "هر"),
    ("hich", "هیچ"),
    ("hame", "همه"),
    # 3. Time & Temporal
    ("emrooz", "امروز"),
    ("dirooz", "دیروز"),
    ("farda", "فردا"),
    ("alan", "الان"),
    ("hala", "حالا"),
    ("ghabl", "قبل"),
    ("zood", "زود"),
    ("dir", "دیر"),
    ("hamisheh", "همیشه"),
    ("hargez", "هرگز"),
    ("dobare", "دوباره"),
    # 4. Common Nouns & Places
    ("khane", "خانه"),
    ("otaq", "اتاق"),
    ("dar", "در"),
    ("panjereh", "پنجره"),
    ("miz", "میز"),
    ("sandali", "صندلی"),
    ("ketab", "کتاب"),
    ("daftar", "دفتر"),
    ("mashin", "ماشین"),
    ("shahr", "شهر"),
    ("keshvar", "کشور"),
    ("zamin", "زمین"),
    ("aseman", "آسمان"),
    ("khorshid", "خورشید"),
    ("ab", "آب"),
    ("nan", "نان"),
    ("ghaza", "غذا"),
    # 5. Adjectives & Comparisons
    ("bozorg", "بزرگ"),
    ("koochik", "کوچک"),
    ("boland", "بلند"),
    ("kootah", "کوتاه"),
    ("ziba", "زیبا"),
    ("sakht", "سخت"),
    ("tamiz", "تمیز"),
    ("roshan", "روشن"),
    ("tarik", "تاریک"),
    ("shad", "شاد"),
    ("ghamgin", "غمگین"),
    # 6. Inflected Verbs with Prefixes (mi-, nemi-) and Suffixes
    ("mikhaham", "می‌خواهم"),
    ("nemikham", "نمی‌خوام"),
    ("mikonam", "می‌کنم"),
    ("mikonim", "می‌کنیم"),
    ("nemiram", "نمی‌رم"),
    ("raftam", "رفتم"),
    ("rafti", "رفتی"),
    ("raftim", "رفتیم"),
    ("goftam", "گفتم"),
    ("goftim", "گفتیم"),
    ("didi", "دیدی"),
    ("kardam", "کردم"),
    ("kardid", "کردید"),
    ("amadam", "آمدم"),
    # 7. Suffixes, Plurals, and Compounds (tar, tarin, ha, yan, an)
    ("bozorgtar", "بزرگ‌تر"),
    ("behtarin", "بهترین"),
    ("daneshjooyan", "دانشجویان"),
    ("daryaha", "دریاها"),
    ("derakhtan", "درختان"),
    ("dustan", "دوستان"),
    ("pedaram", "پدرم"),
    ("madarash", "مادرش"),
    ("ketabet", "کتابت"),
    ("khubam", "خوبم"),
    ("daneshgah", "دانشگاه"),
    ("khoshbakhtane", "خوشبختانه"),
    ("irani", "ایرانی"),
    ("zibaee", "زیبایی"),
    ("bacheha", "بچه‌ها"),
    # 8. Slang & Colloquial Expressions
    ("chakerim", "چاکریم"),
    ("nokaram", "نوکرم"),
    ("fadat", "فدات"),
    ("ghorbanat", "قربانت"),
    ("dastet", "دستت"),
    ("chetorid", "چطورید"),
]


@pytest.fixture(scope="module")
def engine() -> TranslitEngine:
    return TranslitEngine()


def test_translit_benchmark_accuracy(engine: TranslitEngine) -> None:
    """Benchmark test verifying phonetic transliteration accuracy on 80+ realistic words."""
    correct_top1 = 0
    correct_top3 = 0
    total = len(BENCHMARK_CORPUS)

    failures: list[tuple[str, str, list[str]]] = []

    for latin, expected_persian in BENCHMARK_CORPUS:
        cands = engine.transliterate_word(latin)
        top1 = cands[0] if cands else ""

        # Normalize ZWNJ for comparison tolerance if both forms are legitimate
        norm_expected = expected_persian.replace("\u200c", "")

        is_top1 = (top1 == expected_persian) or (top1.replace("\u200c", "") == norm_expected)
        is_top3 = any(
            (c == expected_persian) or (c.replace("\u200c", "") == norm_expected)
            for c in cands[:3]
        )

        if is_top1:
            correct_top1 += 1
            correct_top3 += 1
        elif is_top3:
            correct_top3 += 1
        else:
            failures.append((latin, expected_persian, cands[:4]))

    top1_accuracy = correct_top1 / total
    top3_accuracy = correct_top3 / total

    print(
        f"\nTransliteration Benchmark Results:\n"
        f"  Total Words: {total}\n"
        f"  Top-1 Accuracy: {correct_top1}/{total} ({top1_accuracy * 100:.2f}%)\n"
        f"  Top-3 Accuracy: {correct_top3}/{total} ({top3_accuracy * 100:.2f}%)"
    )

    if failures:
        print("  Failures (first 5):", failures[:5])

    # Hard gate: Top-3 accuracy must be at least 90%
    assert top3_accuracy >= 0.90, (
        f"Transliteration top-3 accuracy {top3_accuracy * 100:.1f}% fell below required 90% gate!"
    )
    # Top-1 accuracy must be at least 80%
    assert top1_accuracy >= 0.80, (
        f"Transliteration top-1 accuracy {top1_accuracy * 100:.1f}% fell below required 80% gate!"
    )


def test_translit_token_safety_screening(engine: TranslitEngine) -> None:
    """Ensure URLs, emails, filenames, code keywords, and numbers are protected."""
    unsafe_tokens = [
        "https://google.com",
        "user@example.com",
        "script.py",
        "archive.zip",
        "index.html",
        "my_var_name",
        "12345",
        "salam123",
        "v2.0",
        "calc()",
        "#trending",
        "@mention",
        "C:\\Windows",
        "api/v1/auth",
    ]

    for tok in unsafe_tokens:
        assert not is_safe_finglish_token(tok), f"Expected token {tok!r} to be screened as unsafe!"
        cands = engine.transliterate_word(tok)
        assert cands == [], f"Expected unsafe token {tok!r} to return empty candidates, got {cands}"

    # Verify transliterate_text preserves unsafe tokens untouched
    sample_text = "salam baradar be https://ravaan.dev boro va script.py ro run kon 123"
    result = engine.transliterate_text(sample_text)
    assert "https://ravaan.dev" in result
    assert "script.py" in result
    assert "123" in result


def test_translit_user_learning_prioritization(engine: TranslitEngine) -> None:
    """Verify that user selection overrides default transliteration ranking."""
    word = "khiyaban"
    _ = engine.transliterate_word(word)

    # Let's say user explicitly picks a custom spelling
    custom_choice = "خیابون"
    engine.record_pick(word, custom_choice)

    updated_cands = engine.transliterate_word(word)
    assert updated_cands[0] == custom_choice

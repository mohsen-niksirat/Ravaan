"""Comprehensive tests for Ravaan v3.1 Advanced Offline Suite:
1. Unit, Currency (Rial/Toman/Words), Temperature & Timezone Converter (unit_converter.py & calc.py)
2. Smart Time-of-Day Greetings, Relative Jalali/Gregorian Dates & App-Conditional Snippets
3. Bilingual Offline Emoji & Symbol Quick-Search (:keyword / :کلیدواژه:)
4. Offline Persian Thesaurus (Synonyms), Context-Aware Homophone Guard & Harakat Helper
5. Advanced Paste & Clipboard Format Transformer (TSV->Markdown/JSON, URLs->MD, Clean FA)
6. Windows Native WinRT OCR Wrapper & Persian Post-Processing (ravan/platform/ocr.py)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ravan.cli import main as cli_main
from ravan.core.advanced_paste import (
    detect_best_paste_modes,
    transform_clipboard_content,
    tsv_to_json_array,
    tsv_to_markdown_table,
)
from ravan.core.calc import calculate, extract_math_expression
from ravan.core.config import Config, Snippet
from ravan.core.emoji_search import expand_colon_emoji, search_emoji, search_emoji_candidates
from ravan.core.orthography import check_live_orthography
from ravan.core.predictor import DictPredictor
from ravan.core.snippet import SnippetEngine, extract_form_fields, render_template
from ravan.core.snippet_macros import get_time_greeting
from ravan.core.thesaurus import (
    apply_homophone_fixes,
    check_homophones,
    lookup_harakat_variants,
    lookup_synonyms,
    strip_harakat,
)
from ravan.core.unit_converter import evaluate_conversion
from ravan.platform import ocr as ocr_mod


def test_unit_currency_temp_and_timezone_conversions() -> None:
    # Length & Mass
    assert calculate("150km to m") == "150,000 m"
    assert calculate("۱۵۰ کیلومتر به متر") == "۱۵۰,۰۰۰ متر"
    assert calculate("1000g to kg") == "1 kg"
    assert calculate("2 mesghal to g") == "9.2166 g"

    # Digital Storage
    assert calculate("5gb to mb") == "5,120 MB"
    assert calculate("۲ گیگ به مگابایت") == "۲,۰۴۸ مگابایت"

    # Temperature
    assert calculate("0c to f") == "32 °F"
    assert calculate("100 celsius to fahrenheit") == "212 °F"
    assert calculate("۰ سانتی‌گراد به فارنهایت") == "۳۲ °F"

    # Iranian Financial (Rial <-> Toman & Words)
    assert calculate("45000000 rial to toman") == "4,500,000 Toman"
    assert calculate("۴۵۰۰۰۰۰۰ ریال به تومان") == "۴,۵۰۰,۰۰۰ تومان"
    assert calculate("1250000 toman to words") == "یک میلیون و دویست و پنجاه هزار تومان"

    # Timezone conversions
    assert evaluate_conversion("18:30 tehran in london") == "15:00 London"
    assert evaluate_conversion("۱۸:۳۰ تهران به لندن") == "۱۵:۰۰ لندن"
    assert evaluate_conversion("23:00 london to tehran") == "02:30 Tehran (+1d)"

    # Inline '=' extraction from live typing buffer
    assert extract_math_expression("قیمت نهایی ۴۵۰۰۰۰۰۰ ریال به تومان") == "۴۵۰۰۰۰۰۰ ریال به تومان"
    assert extract_math_expression("ساعت پرواز 18:30 tehran in london") == "18:30 tehran in london"


def test_smart_snippets_greetings_relative_dates_and_app_conditionals() -> None:
    assert get_time_greeting("fa", hour=8) == "صبح بخیر"
    assert get_time_greeting("fa", hour=13) == "ظهر بخیر"
    assert get_time_greeting("fa", hour=17) == "عصر بخیر"
    assert get_time_greeting("fa", hour=23) == "شب بخیر"
    assert get_time_greeting("en", hour=9) == "Good morning"
    assert get_time_greeting("en", hour=19) == "Good evening"

    # Relative Jalali & Gregorian dates must NOT be mistaken for form fields
    tmpl = "موعد تحویل: {{jalali:+3d}} (میلادی: {{date:+1w}}) — {{greeting_fa}}"
    assert extract_form_fields(tmpl) == []
    rendered = render_template(tmpl)
    assert "{{" not in rendered
    assert "/" in rendered and "-" in rendered

    # App-conditional snippet expansion
    cond_tmpl = "{{if_app:telegram,whatsapp:سلام مخلصم!|با سلام و احترام؛}} ({{app}})"
    assert extract_form_fields(cond_tmpl) == []
    eng = SnippetEngine([Snippet(trigger=";hi", replacement=cond_tmpl)])
    out_tg = eng.expand(";hi", app_name="telegram.exe")
    out_word = eng.expand(";hi", app_name="winword.exe")
    assert out_tg == "سلام مخلصم! (telegram.exe)"
    assert out_word == "با سلام و احترام؛ (winword.exe)"


def test_bilingual_emoji_search_and_predictor_integration() -> None:
    hits_fa = search_emoji(":تیک", limit=3)
    assert hits_fa and hits_fa[0].symbol == "✅"

    hits_en = search_emoji(":rocket", limit=3)
    assert hits_en and hits_en[0].symbol == "🚀"

    assert expand_colon_emoji(":تیک:") == "✅"
    assert expand_colon_emoji(":قلب:") == "❤️"
    assert expand_colon_emoji(":rocket:") == "🚀"
    assert expand_colon_emoji(":unknown_xyz:") is None

    cands = search_emoji_candidates(":موشک", limit=3)
    assert cands and cands[0].text == "🚀"

    pred = DictPredictor.from_config(Config())
    pred_cands = pred.predict(":تیک", "", limit=5)
    assert pred_cands and pred_cands[0].text == "✅"


def test_persian_thesaurus_homophones_and_harakat() -> None:
    # Bidirectional synonyms
    syns_email = lookup_synonyms("ایمیل")
    assert "رایانامه" in syns_email
    syns_rev = lookup_synonyms("رایانامه")
    assert "ایمیل" in syns_rev

    syns_approve = lookup_synonyms("تأیید")
    assert "تصویب" in syns_approve and "پذیرش" in syns_approve

    # Context-aware homophones
    sample = "او در حیات خانه بر اثاث قانون‌گزاری و سپاس‌گذاری نماز غذا خواند."
    fixes = check_homophones(sample)
    assert len(fixes) >= 4
    corrected = apply_homophone_fixes(sample)
    assert "حیاط خانه" in corrected
    assert "بر اساس" in corrected
    assert "قانون‌گذاری" in corrected
    assert "سپاس‌گزاری" in corrected
    assert "نماز قضا" in corrected

    # Live Orthography Guard integration
    sug1 = check_live_orthography("خانه", recent_words=["در", "حیات", "خانه"])
    assert sug1 is not None
    assert sug1.original == "حیات خانه"
    assert sug1.replacement == "حیاط خانه"
    assert sug1.reason == "homophone"

    sug2 = check_live_orthography("خواستگاه")
    assert sug2 is not None
    assert sug2.replacement == "خاستگاه"
    assert sug2.reason == "homophone"

    # Harakat helper
    assert strip_harakat("سَلامٌ عَلَیکُم — کِتـــاب‌ها") == "سلام علیکم — کتاب‌ها"
    variants = lookup_harakat_variants("ملک")
    assert len(variants) >= 3


def test_advanced_paste_clipboard_transformers() -> None:
    tsv = "نام\tسن\nعلی\t۲۵\nسارا\t۳۰"
    assert "tsv_to_markdown" in detect_best_paste_modes(tsv)

    md_table = tsv_to_markdown_table(tsv)
    assert "| نام" in md_table and "| علی" in md_table and "| ---" in md_table

    json_arr = json.loads(tsv_to_json_array(tsv))
    assert json_arr == [{"نام": "علی", "سن": 25}, {"نام": "سارا", "سن": 30}]

    messy_fa = "<p>سلام و سپاس‌گذاری در حیات خانه كتاب ها</p>"
    cleaned_fa = transform_clipboard_content(messy_fa, mode="clean_fa")
    assert "<p>" not in cleaned_fa
    assert "سپاس‌گزاری" in cleaned_fa
    assert "حیاط خانه" in cleaned_fa
    assert "کتاب‌ها" in cleaned_fa

    md_links = transform_clipboard_content("گیت‌هاب روان - https://github.com/mohsen-niksirat/Ravaan", mode="url_to_markdown")
    assert md_links == "[گیت‌هاب روان](https://github.com/mohsen-niksirat/Ravaan)"

    emails = transform_clipboard_content("Contact info@ravaan.ir or dev@example.com today", mode="extract_emails")
    assert emails.splitlines() == ["info@ravaan.ir", "dev@example.com"]


def test_windows_native_ocr_postprocessing_and_mocked_extract(tmp_path: Path) -> None:
    raw_ocr = "كتاب ها در حیات خانه مي باشد"
    cleaned = ocr_mod.postprocess_ocr_text(raw_ocr, normalize_fa=True)
    assert "کتاب‌ها" in cleaned
    assert "حیاط خانه" in cleaned
    assert "می‌باشد" in cleaned

    img_file = tmp_path / "sample.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    fake_proc = MagicMock(returncode=0, stdout="بر اثاث گزارش كتاب ها\n", stderr="")
    with (
        patch.object(ocr_mod, "is_ocr_supported", return_value=True),
        patch.object(ocr_mod.subprocess, "run", return_value=fake_proc),
    ):
        extracted = ocr_mod.extract_text_from_image(img_file)
    assert "بر اساس" in extracted
    assert "کتاب‌ها" in extracted

    with pytest.raises(FileNotFoundError):
        ocr_mod.extract_text_from_image(tmp_path / "missing.png")


def test_cli_v3_1_offline_subcommands(capsys) -> None:
    assert cli_main(["calc", "150km to m"]) == 0
    assert "150,000 m" in capsys.readouterr().out

    assert cli_main(["emoji", "تیک"]) == 0
    assert "✅" in capsys.readouterr().out

    assert cli_main(["thesaurus", "ایمیل"]) == 0
    assert "رایانامه" in capsys.readouterr().out

    assert cli_main(["thesaurus", "--homophones", "حیات خانه"]) == 0
    assert "حیاط خانه" in capsys.readouterr().out

    assert cli_main(["paste", "--mode", "bullet_list", "اول\nدوم"]) == 0
    assert "• اول" in capsys.readouterr().out


def test_v3_1_new_modules_respect_size_budget() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    for rel in (
        "ravan/core/unit_converter.py",
        "ravan/core/emoji_search.py",
        "ravan/core/thesaurus.py",
        "ravan/core/advanced_paste.py",
        "ravan/platform/ocr.py",
    ):
        lines = len((repo_root / rel).read_text(encoding="utf-8").splitlines())
        assert lines <= 400, f"{rel} has {lines} lines (exceeds 400-line ceiling)"

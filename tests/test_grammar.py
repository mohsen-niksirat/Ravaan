"""Unit and integration tests for Persian grammar, preposition detachment, and tanween."""

from __future__ import annotations

from ravan.cli import main as cli_main
from ravan.core.grammar import (
    correct_persian_grammar,
    fix_compounds,
    fix_ezafe_heh,
    fix_prepositions,
    fix_tanween,
    inspect_grammar,
)
from ravan.core.normalizer import clean_pasted_text, normalize_persian


def test_fix_prepositions_detachment():
    """Verify that fused prepositions are detached according to Academy rules."""
    raw = "بنام خداوند بخشنده مهربان و بسوی او بازمی‌گردیم."
    expected = "به نام خداوند بخشنده مهربان و به سوی او بازمی‌گردیم."
    assert fix_prepositions(raw) == expected

    more = "بعنوان مثال بطور کلی بخاطر باران بدلیل ترافیک بویژه عصرها بهمراه دوستان بعلاوه هزینه بموقع بجای او"
    fixed = fix_prepositions(more)
    assert "به عنوان مثال" in fixed
    assert "به طور کلی" in fixed
    assert "به خاطر باران" in fixed
    assert "به دلیل ترافیک" in fixed
    assert "به ویژه عصرها" in fixed
    assert "به همراه دوستان" in fixed
    assert "به علاوه هزینه" in fixed
    assert "به موقع" in fixed
    assert "به جای او" in fixed


def test_colloquial_verb_biyad_not_corrupted():
    """Verify that colloquial verb 'بیاد' (بیاید) is NOT corrupted into 'به یاد'."""
    raw = "قرار بود فردا بیاد و با ما صحبت کند."
    # 'بیاد' must remain untouched
    assert fix_prepositions(raw) == raw


def test_fix_tanween_adverbs():
    """Verify that Arabic-origin adverbs receive tanween fatha."""
    raw = "من حتما و واقعا و مثلا این کار را عملا انجام می‌دهم."
    fixed = fix_tanween(raw)
    assert "حتماً" in fixed
    assert "واقعاً" in fixed
    assert "مثلاً" in fixed
    assert "عملاً" in fixed


def test_existing_tanween_preserved_without_duplication():
    """Verify that words with tanween already present are not double-modified."""
    raw = "این موضوع اصلاً و کاملاً مشخص است."
    assert fix_tanween(raw) == raw
    assert inspect_grammar(raw) == []


def test_mystic_plural_orafa_preserved():
    """Verify that 'عرفا' (plural of عارف) is NOT transformed into 'عرفاً'."""
    raw = "در آثار عرفا و فلاسفه این مسئله مطرح شده است."
    assert fix_tanween(raw) == raw


def test_fix_compounds():
    """Verify compound words cohesion and ZWNJ standardization."""
    raw = "گفت و گو در مورد راه حل ها و دست دوم بودن کالا و روبه‌رو شدن"
    fixed = fix_compounds(raw)
    assert "گفت‌وگو" in fixed
    assert "راه‌حل‌ها" in fixed
    assert "دست‌دوم" in fixed

    raw2 = "گفتگو با دانش آموزان در خصوص پیش نهاد ها"
    fixed2 = fix_compounds(raw2)
    assert "گفت‌وگو" in fixed2
    assert "پیشنهادها" in fixed2


def test_fix_ezafe_heh():
    """Verify silent heh ezafe with Persian words, numbers, and Latin characters."""
    assert fix_ezafe_heh("خانه ی من") == "خانه‌ی من"
    assert fix_ezafe_heh("پروژه ی Ravaan بسیار کاربردی است") == "پروژه‌ی Ravaan بسیار کاربردی است"
    assert fix_ezafe_heh("صفحه ی ۲ و بخش ۳") == "صفحه‌ی ۲ و بخش ۳"
    assert fix_ezafe_heh("نسخه ی 2.0 منتشر شد") == "نسخه‌ی 2.0 منتشر شد"


def test_inspect_grammar_issues():
    """Verify inspect_grammar detects issues and returns detailed metadata."""
    sample = "بنام خدا حتما گفتگو خانه ی ما"
    issues = inspect_grammar(sample)
    categories = [i.category for i in issues]
    assert "preposition" in categories
    assert "tanween" in categories
    assert "compound" in categories
    assert "ezafe" in categories

    # Verify positions and descriptions
    for issue in issues:
        assert issue.original in sample
        assert issue.replacement
        assert len(issue.description) > 0


def test_correct_persian_grammar_comprehensive():
    """Verify all grammar rules combined."""
    raw = "بنام خدا حتما گفتگو درباره ی این راه حل انجام خواهد شد."
    fixed = correct_persian_grammar(raw)
    assert "به نام خدا" in fixed
    assert "حتماً" in fixed
    assert "گفت‌وگو" in fixed
    assert "درباره‌ی این" in fixed
    assert "راه‌حل" in fixed


def test_normalizer_integration():
    """Verify fix_grammar integration within normalize_persian and clean_pasted_text."""
    raw = "بنام خدا ، حتما گفتگو را شروع كنيد !"
    res = normalize_persian(raw, fix_grammar=True)
    assert "به نام خدا" in res
    assert "حتماً" in res
    assert "گفت‌وگو" in res
    assert "کنید!" in res

    pasted = "متن بنام خدا و حتما گفتگو\n```\nraw = بنام\n```\nپایان"
    cleaned = clean_pasted_text(pasted, fix_grammar=True)
    assert "به نام خدا" in cleaned
    assert "حتماً گفت‌وگو" in cleaned
    # Inside code block remains untouched
    assert "raw = بنام" in cleaned


def test_cli_grammar_subcommand(capsys):
    """Verify ravan-cli grammar output with inspection and with --fix flag."""
    # Test --fix flag
    code = cli_main(["grammar", "بنام خدا حتما", "--fix"])
    assert code == 0
    captured = capsys.readouterr()
    assert "به نام خدا حتماً" in captured.out

    # Test inspection mode with issues
    code = cli_main(["grammar", "بنام خدا"])
    assert code == 0
    captured = capsys.readouterr()
    assert "Found 1 issue(s):" in captured.out
    assert "[preposition]" in captured.out
    assert "به نام خدا" in captured.out

    # Test inspection mode with clean text
    code = cli_main(["grammar", "به نام خدا همه چیز درست است."])
    assert code == 0
    captured = capsys.readouterr()
    assert "No grammar or preposition issues found." in captured.out

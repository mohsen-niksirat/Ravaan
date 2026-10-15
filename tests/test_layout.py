from ravan.core.layout import LayoutMapper


def test_q_to_zad():
    mapper = LayoutMapper()
    assert mapper.en_to_fa_word("q") == "ض"


def test_salam_roundtrip():
    mapper = LayoutMapper()
    fa = mapper.en_to_fa_word("salam")
    assert fa is not None
    back = mapper.fa_to_en_word(fa)
    assert back == "salam"


def test_convert_auto_en_to_fa():
    mapper = LayoutMapper()
    # o,v,n on EN layout → خ ر د pieces: o→خ ,→و? wait n→د, v→ر
    # "ovn" → "خرد" (without و). Classic "خورد" is o + , + v + n
    assert mapper.convert_word("o,vn") == "خورد"


def test_hjvfd_maps():
    mapper = LayoutMapper()
    # Documented mapping for these keys
    assert mapper.en_to_fa_word("hjvfd") == "اتربی"


def test_special_persian_keys():
    mapper = LayoutMapper()
    # Windows Persian \ is پ, Shift+C is ژ, m is ئ, Shift+H is آ
    assert mapper.en_to_fa_word("\\") == "پ"
    assert mapper.en_to_fa_word("C") == "ژ"
    assert mapper.en_to_fa_word("m") == "ئ"
    assert mapper.en_to_fa_word("H") == "آ"
    assert mapper.en_to_fa_word("?") == "؟"
    assert mapper.en_to_fa_word("T") == "،"
    assert mapper.en_to_fa_word("Y") == "؛"


def test_convert_word_bidirectional_toggle():
    mapper = LayoutMapper()
    # English -> Persian
    fa = mapper.convert_word("o,vn")
    assert fa == "خورد"
    # Persian -> English
    en = mapper.convert_word("خورد")
    assert en == "o,vn"
    # Toggle back
    assert mapper.convert_word(en) == "خورد"


def test_convert_text_sentences():
    mapper = LayoutMapper()
    en_sentence = "sghl hlv,c o,f hsj"
    fa_sentence = mapper.convert_text(en_sentence)
    assert fa_sentence == "سلام امروز خوب است"

    back = mapper.convert_text(fa_sentence)
    assert back == en_sentence

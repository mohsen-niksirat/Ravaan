"""Generate Finglish -> Persian mapping table from Persian word frequencies and phonetic rules."""

from __future__ import annotations

import json
from pathlib import Path

# Consonants and basic phonetic conversions
_FA_TO_EN_RULES: list[tuple[str, list[str]]] = [
    ("خ", ["kh"]),
    ("ش", ["sh"]),
    ("چ", ["ch"]),
    ("ژ", ["zh"]),
    ("ق", ["gh", "q"]),
    ("غ", ["gh"]),
    ("ب", ["b"]),
    ("پ", ["p"]),
    ("ت", ["t"]),
    ("ط", ["t"]),
    ("ث", ["s"]),
    ("س", ["s"]),
    ("ص", ["s"]),
    ("ج", ["j"]),
    ("ح", ["h"]),
    ("ه", ["h", "e"]),
    ("د", ["d"]),
    ("ذ", ["z"]),
    ("ز", ["z"]),
    ("ض", ["z"]),
    ("ظ", ["z"]),
    ("ر", ["r"]),
    ("ف", ["f"]),
    ("ک", ["k", "c"]),
    ("گ", ["g"]),
    ("ل", ["l"]),
    ("م", ["m"]),
    ("ن", ["n"]),
    ("و", ["v", "w", "oo", "u", "o"]),
    ("ی", ["y", "i", "ee"]),
    ("آ", ["aa", "a", "A"]),
    ("ا", ["a", "aa", "A"]),
    ("ع", ["a", "e", "o", ""]),
    ("ء", ["", "'"]),
    ("ئ", ["y", "i"]),
]

_COMMON_MAPPINGS: dict[str, list[str]] = {
    "salam": ["سلام"],
    "salam!": ["سلام!"],
    "slm": ["سلام"],
    "chetori": ["چطوری"],
    "cheturi": ["چطوری"],
    "khubi": ["خوبی"],
    "khoobi": ["خوبی"],
    "mamnoon": ["ممنون"],
    "mamnun": ["ممنون"],
    "merci": ["مرسی"],
    "mersi": ["مرسی"],
    "mercy": ["مرسی"],
    "khodafez": ["خداحافظ"],
    "khodahafez": ["خداحافظ"],
    "sobhkheir": ["صبح‌بخیر"],
    "shabkheir": ["شب‌بخیر"],
    "lotfan": ["لطفا", "لطفاً"],
    "bale": ["بله"],
    "baleh": ["بله"],
    "are": ["آره"],
    "na": ["نه"],
    "kheyr": ["خیر"],
    "man": ["من"],
    "to": ["تو"],
    "shoma": ["شما"],
    "ma": ["ما"],
    "anha": ["آنها"],
    "ishan": ["ایشان"],
    "in": ["این"],
    "an": ["آن"],
    "inja": ["اینجا"],
    "anja": ["آنجا"],
    "koja": ["کجا"],
    "kay": ["کی"],
    "key": ["کی"],
    "chera": ["چرا"],
    "chegone": ["چگونه"],
    "kodam": ["کدام"],
    "chi": ["چی"],
    "che": ["چه"],
    "ki": ["کی"],
    "hame": ["همه"],
    "hich": ["هیچ"],
    "har": ["هر"],
    "yek": ["یک"],
    "do": ["دو"],
    "se": ["سه"],
    "chahar": ["چهار"],
    "panj": ["پنج"],
    "shesh": ["شش"],
    "haft": ["هفت"],
    "hasht": ["هشت"],
    "noh": ["نه"],
    "dah": ["ده"],
    "sad": ["صد"],
    "hezar": ["هزار"],
    "emrooz": ["امروز"],
    "emruz": ["امروز"],
    "dirooz": ["دیروز"],
    "diruz": ["دیروز"],
    "farda": ["فردا"],
    "alan": ["الان"],
    "hala": ["حالا"],
    "bad": ["بعد", "بد"],
    "ghabl": ["قبل"],
    "zood": ["زود"],
    "zud": ["زود"],
    "dir": ["دیر"],
    "hamisheh": ["همیشه"],
    "hamishe": ["همیشه"],
    "hargez": ["هرگز"],
    "gahie": ["گاهی"],
    "gahi": ["گاهی"],
    "hanuz": ["هنوز"],
    "hanooz": ["هنوز"],
    "dobare": ["دوباره"],
    "khane": ["خانه"],
    "khaneh": ["خانه"],
    "otaq": ["اتاق"],
    "otagh": ["اتاق"],
    "dar": ["در"],
    "panjereh": ["پنجره"],
    "panjere": ["پنجره"],
    "miz": ["میز"],
    "sandali": ["صندلی"],
    "ketab": ["کتاب"],
    "daftar": ["دفتر"],
    "qalam": ["قلم"],
    "ghalam": ["قلم"],
    "kaghaz": ["کاغذ"],
    "madrese": ["مدرسه"],
    "madreseh": ["مدرسه"],
    "daneshgah": ["دانشگاه"],
    "ostad": ["استاد"],
    "daneshjoo": ["دانشجو"],
    "daneshju": ["دانشجو"],
    "dars": ["درس"],
    "mashin": ["ماشین"],
    "otobus": ["اتوبوس"],
    "havapeima": ["هواپیما"],
    "havapeyma": ["هواپیما"],
    "qatar": ["قطار"],
    "ghatar": ["قطار"],
    "khiaban": ["خیابان"],
    "khiaban!": ["خیابان"],
    "kooche": ["کوچه"],
    "koocheh": ["کوچه"],
    "shahr": ["شهر"],
    "keshvar": ["کشور"],
    "roosta": ["روستا"],
    "rusta": ["روستا"],
    "zamin": ["زمین"],
    "aseman": ["آسمان"],
    "asman": ["آسمان"],
    "khorshid": ["خورشید"],
    "mah": ["ماه"],
    "setareh": ["ستاره"],
    "setare": ["ستاره"],
    "ab": ["آب"],
    "nan": ["نان"],
    "ghaza": ["غذا"],
    "chai": ["چای"],
    "chay": ["چای"],
    "ghahve": ["قهوه"],
    "shir": ["شیر"],
    "sib": ["سیب"],
    "mive": ["میوه"],
    "miveh": ["میوه"],
    "goosht": ["گوشت"],
    "morgh": ["مرغ"],
    "berenj": ["برنج"],
    "rooz": ["روز"],
    "ruz": ["روز"],
    "shab": ["شب"],
    "sobh": ["صبح"],
    "asr": ["عصر"],
    "hafteh": ["هفته"],
    "hafte": ["هفته"],
    "mahane": ["ماهانه"],
    "sal": ["سال"],
    "bahar": ["بهار"],
    "tabestan": ["تابستان"],
    "paeez": ["پاییز"],
    "paiz": ["پاییز"],
    "zemestan": ["زمستان"],
    "baran": ["باران"],
    "barf": ["برف"],
    "abr": ["ابر"],
    "hava": ["هوا"],
    "garm": ["گرم"],
    "sard": ["سرد"],
    "khob": ["خوب"],
    "khoob": ["خوب"],
    "bozorg": ["بزرگ"],
    "koochik": ["کوچک"],
    "koochek": ["کوچک"],
    "boland": ["بلند"],
    "kootah": ["کوتاه"],
    "kutah": ["کوتاه"],
    "ziba": ["زیبا"],
    "zesht": ["زشت"],
    "asoon": ["آسان"],
    "asan": ["آسان"],
    "sakht": ["سخت"],
    "arzan": ["ارزان"],
    "geran": ["گران"],
    "taze": ["تازه"],
    "tazeh": ["تازه"],
    "kohan": ["کهن"],
    "pir": ["پیر"],
    "javan": ["جوان"],
    "shad": ["شاد"],
    "ghamgin": ["غمگین"],
    "roshan": ["روشن"],
    "tarik": ["تاریک"],
    "tamiz": ["تمیز"],
    "kasif": ["کثیف"],
    "kasif!": ["کثیف"],
    "dorost": ["درست"],
    "ghalat": ["غلط"],
    "rast": ["راست"],
    "dorogh": ["دروغ"],
    "dorough": ["دروغ"],
    "raftan": ["رفتن"],
    "amadan": ["آمدن"],
    "goftan": ["گفتن"],
    "didan": ["دیدن"],
    "shenidan": ["شنیدن"],
    "khordan": ["خوردن"],
    "nooshidan": ["نوشیدن"],
    "khandidan": ["خندیدن"],
    "geryeh": ["گریه"],
    "gerye": ["گریه"],
    "khabidan": ["خوابیدن"],
    "bidar": ["بیدار"],
    "neveshtan": ["نوشتن"],
    "khandan": ["خواندن"],
    "kharidan": ["خریدن"],
    "forookhtan": ["فروختن"],
    "dadan": ["دادن"],
    "gereftan": ["گرفتن"],
    "zadan": ["زدن"],
    "bastan": ["بستن"],
    "baz": ["باز"],
    "kardan": ["کردن"],
    "shodan": ["شدن"],
    "boodan": ["بودن"],
    "budan": ["بودن"],
    "dashtan": ["داشتن"],
    "sakhtan": ["ساختن"],
    "sookhtan": ["سوختن"],
    "oftadan": ["افتادن"],
    "istadan": ["ایستادن"],
    "neshastan": ["نشستن"],
    "dastan": ["داستان"],
    "sher": ["شعر"],
    "ahang": ["آهنگ"],
    "film": ["فیلم"],
    "aks": ["عکس"],
    "bazi": ["بازی", "بعضی"],
    "kar": ["کار"],
    "pool": ["پول"],
    "pul": ["پول"],
    "bank": ["بانک"],
    "bazar": ["بازار"],
    "maghaze": ["مغازه"],
    "kharid": ["خرید"],
    "foroosh": ["فروش"],
    "gheymat": ["قیمت"],
    "hesab": ["حساب"],
    "dast": ["دست"],
    "pa": ["پا"],
    "sar": ["سر"],
    "chashm": ["چشم"],
    "cheshm": ["چشم"],
    "goosh": ["گوش"],
    "gush": ["گوش"],
    "bini": ["بینی"],
    "dahan": ["دهان"],
    "dandan": ["دندان"],
    "moo": ["مو"],
    "mu": ["مو"],
    "del": ["دل"],
    "ghalb": ["قلب"],
    "pedar": ["پدر"],
    "madar": ["مادر"],
    "baradar": ["برادر"],
    "khahar": ["خواهر"],
    "pesar": ["پسر"],
    "dokhtar": ["دختر"],
    "zendegi": ["زندگی"],
    "omid": ["امید"],
    "eshgh": ["عشق"],
    "eshq": ["عشق"],
    "doost": ["دوست"],
    "dust": ["دوست"],
    "doshman": ["دشمن"],
}


def fa_word_to_finglish(word: str) -> list[str]:
    """Produce simple Finglish phonetic variations of a Persian word."""
    results = [""]
    for ch in word:
        mapped = None
        for fa_ch, en_list in _FA_TO_EN_RULES:
            if ch == fa_ch:
                mapped = en_list
                break
        if mapped is None:
            mapped = [ch]
        new_res = []
        for r in results:
            for en in mapped:
                new_res.append(r + en)
        results = new_res[:8]
    return results


def build_finglish_table(words_fa_path: Path, max_words: int = 2500) -> dict[str, list[str]]:
    table: dict[str, list[str]] = {}

    for k, vs in _COMMON_MAPPINGS.items():
        table.setdefault(k.lower(), []).extend(vs)

    if words_fa_path.is_file():
        lines = words_fa_path.read_text(encoding="utf-8").splitlines()
        count = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            fa_w = parts[0].strip()
            if len(fa_w) < 2 or not all(ord(c) > 127 for c in fa_w):
                continue
            for f_var in fa_word_to_finglish(fa_w):
                f_low = f_var.lower()
                if len(f_low) >= 2 and fa_w not in table.setdefault(f_low, []):
                    table[f_low].append(fa_w)
            count += 1
            if count >= max_words:
                break

    for k in list(table.keys()):
        seen = set()
        deduped = []
        for v in table[k]:
            if v not in seen:
                seen.add(v)
                deduped.append(v)
        table[k] = deduped

    return table


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    fa_path = root / "ravan" / "data" / "words_fa.txt"
    out_path = root / "ravan" / "data" / "finglish_dict.json"
    table = build_finglish_table(fa_path, max_words=2200)
    out_path.write_text(json.dumps(table, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(table)} Finglish mappings to {out_path}")


if __name__ == "__main__":
    main()

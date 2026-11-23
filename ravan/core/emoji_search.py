"""Offline bilingual (Persian & English) emoji and symbol quick-search (`:keyword`)."""

from __future__ import annotations

from dataclasses import dataclass

from ravan.core.events import Candidate, CandidateKind
from ravan.core.normalizer import normalize_arabic_chars


@dataclass(frozen=True)
class EmojiEntry:
    symbol: str
    code_en: str
    code_fa: str
    aliases: tuple[str, ...]


# Curated high-frequency emojis & symbols with bilingual Persian/English keywords
EMOJI_CATALOG: tuple[EmojiEntry, ...] = (
    EmojiEntry("✅", "check", "تیک", ("تایید", "درست", "ok", "done", "yes", "tick", "سبز")),
    EmojiEntry("❌", "cross", "ضربدر", ("غلط", "خطا", "رد", "no", "error", "cancel", "fail")),
    EmojiEntry("⚠️", "warn", "هشدار", ("اخطار", "توجه", "warning", "alert", "danger")),
    EmojiEntry("💡", "bulb", "نکته", ("ایده", "چراغ", "لامپ", "idea", "tip", "hint", "light")),
    EmojiEntry("✨", "sparkle", "درخشش", ("ستاره", "هوش", "جادو", "ai", "magic", "stars", "new")),
    EmojiEntry("🔥", "fire", "آتش", ("داغ", "عالی", "آتیش", "hot", "lit", "flame")),
    EmojiEntry("🚀", "rocket", "موشک", ("پرتاب", "سریع", "سرعت", "شروع", "launch", "fast", "boost")),
    EmojiEntry("❤️", "heart", "قلب", ("عشق", "دوست", "مهر", "love", "red_heart")),
    EmojiEntry("👍", "thumbsup", "لایک", ("خوب", "موافق", "عالی", "like", "good", "approve")),
    EmojiEntry("👎", "thumbsdown", "دیسلایک", ("مخالف", "بد", "dislike", "bad")),
    EmojiEntry("🙏", "pray", "ممنون", ("تشکر", "مرسی", "لطفا", "سپاس", "thanks", "thankyou", "please")),
    EmojiEntry("👋", "wave", "سلام", ("خداحافظ", "درود", "دست", "hello", "hi", "bye", "salam")),
    EmojiEntry("🎉", "party", "تبریک", ("جشن", "مبارک", "شادی", "tada", "congrats", "celebrate")),
    EmojiEntry("😊", "smile", "لبخند", ("خوشحال", "شاد", "happy", "blush")),
    EmojiEntry("😂", "joy", "خنده", ("قهقهه", " خندیدن", "lol", "laugh", "funny")),
    EmojiEntry("😎", "cool", "باحال", ("عینک", "خفن", "sunglasses", "awesome")),
    EmojiEntry("🤔", "think", "فکر", ("تفکر", "چرا", "سوال", "thinking", "hmm")),
    EmojiEntry("👀", "eyes", "چشم", ("نگاه", "بررسی", "دیدن", "look", "watch", "review")),
    EmojiEntry("🎯", "target", "هدف", ("دقیق", "نشان", "goal", "bullseye", "focus")),
    EmojiEntry("📌", "pin", "پین", ("سنجاق", "مهم", "یادداشت", "pushpin", "sticky")),
    EmojiEntry("📎", "clip", "گیره", ("پیوست", "ضمیمه", "attach", "paperclip")),
    EmojiEntry("📅", "calendar", "تقویم", ("تاریخ", "روز", "جلسه", "date", "schedule")),
    EmojiEntry("⏰", "clock", "ساعت", ("زمان", "یادآور", "تایمر", "time", "alarm", "timer")),
    EmojiEntry("⏳", "hourglass", "صبر", ("انتظار", "درحال", "شنی", "wait", "loading", "pending")),
    EmojiEntry("🔒", "lock", "قفل", ("امنیت", "امن", "محرمانه", "رمز", "secure", "private", "privacy")),
    EmojiEntry("🔓", "unlock", "باز", ("قفل_باز", "open_lock", "unlocked")),
    EmojiEntry("🔑", "key", "کلید", ("رمز", "دسترسی", "توکن", "token", "password", "auth")),
    EmojiEntry("🛡️", "shield", "سپر", ("محافظت", "امنیت", "دفاع", "security", "protect", "guard")),
    EmojiEntry("💻", "code", "کد", ("لپتاپ", "برنامه", "کامپیوتر", "laptop", "pc", "dev", "coding")),
    EmojiEntry("🐛", "bug", "باگ", ("ایراد", "اشکال", "حشره", "issue", "fix", "debug")),
    EmojiEntry("⚙️", "gear", "تنظیمات", ("چرخدنده", "پیکربندی", "settings", "config", "setup")),
    EmojiEntry("📦", "package", "بسته", ("جعبه", "پکیج", "هاب", "box", "bundle", "release", "hub")),
    EmojiEntry("📄", "doc", "سند", ("فایل", "برگه", "مستند", "file", "page", "document", "text")),
    EmojiEntry("📁", "folder", "پوشه", ("فولدر", "دایرکتوری", "dir", "directory")),
    EmojiEntry("📊", "chart", "نمودار", ("آمار", "گزارش", "داشبورد", "stats", "graph", "analytics")),
    EmojiEntry("✉️", "mail", "ایمیل", ("نامه", "پیام", "رایانامه", "email", "letter", "inbox")),
    EmojiEntry("📞", "phone", "تلفن", ("تماس", "زنگ", "موبایل", "call", "contact", "tel")),
    EmojiEntry("🔗", "link", "لینک", ("پیوند", "آدرس", "سایت", "url", "chain")),
    EmojiEntry("🔍", "search", "جستجو", ("ذره‌بین", "پیدا", "find", "lookup", "magnifier")),
    EmojiEntry("🎤", "mic", "میکروفن", ("صدا", "دیکته", "صوتی", "voice", "audio", "record")),
    EmojiEntry("🌹", "rose", "گل", ("رز", "تقدیم", "flower", "gift")),
    EmojiEntry("⭐", "star", "ستاره", ("امتیاز", "برتر", "ویژه", "favorite", "rate", "gold")),
    EmojiEntry("🏆", "trophy", "جام", ("قهرمان", "برنده", "رتبه", "winner", "award", "champion")),
    EmojiEntry("💰", "money", "پول", ("مالی", "هزینه", "قیمت", "درآمد", "cash", "price", "budget")),
    EmojiEntry("💳", "card", "کارت", ("پرداخت", "بانک", "خرید", "pay", "payment", "credit")),
    EmojiEntry("🏠", "home", "خانه", ("منزل", "صفحه_اصلی", "house")),
    EmojiEntry("🏢", "office", "شرکت", ("اداره", "ساختمان", "دفتر", "company", "work", "building")),
    EmojiEntry("☕", "coffee", "قهوه", ("چای", "استراحت", "نوشیدنی", "tea", "break", "cafe")),
    EmojiEntry("📚", "books", "کتاب", ("مطالعه", "آموزش", "فرهنگ", "book", "study", "learn", "docs")),
    EmojiEntry("✍️", "write", "نوشتن", ("تایپ", "نگارش", "ویرایش", "امضا", "edit", "sign", "author")),
    EmojiEntry("🧠", "brain", "مغز", ("هوش", "حافظه", "یادگیری", "smart", "mind", "memory")),
    EmojiEntry("⚡", "zap", "برق", ("سریع", "فوری", "صاعقه", "انرژی", "bolt", "flash", "instant")),
    # Useful typography & currency symbols
    EmojiEntry("﷼", "rial", "ریال", ("واحد_پول", "irr")),
    EmojiEntry("→", "rarr", "فلش_راست", ("راست", "arrow_right", "right", "next")),
    EmojiEntry("←", "larr", "فلش_چپ", ("چپ", "فلش", "arrow_left", "left", "back", "arrow")),
    EmojiEntry("↔", "harr", "دوطرفه", ("فلش_دوطرفه", "swap", "both")),
    EmojiEntry("•", "bullet", "بولت", ("نقطه", "لیست", "dot", "item")),
    EmojiEntry("✓", "tick", "تیک_ساده", ("check_mark", "checkmark")),
    EmojiEntry("×", "times", "ضرب", ("در", "multiply")),
    EmojiEntry("÷", "div", "تقسیم", ("divide",)),
    EmojiEntry("±", "plusminus", "مثبت_منفی", ("حدود", "تقریبا", "pm")),
    EmojiEntry("∞", "inf", "بینهایت", ("بی‌نهایت", "infinity", "forever")),
    EmojiEntry("™", "tm", "برند", ("trademark",)),
    EmojiEntry("©", "copy", "کپی‌رایت", ("کپی", "copyright")),
)


def _clean_query(raw: str) -> str:
    s = normalize_arabic_chars(raw.strip().lower())
    if s.startswith(":"):
        s = s[1:]
    if s.endswith(":"):
        s = s[:-1]
    return s.replace("\u200c", "").replace(" ", "_")


def search_emoji(query: str, limit: int = 5) -> list[EmojiEntry]:
    """Search emojis and symbols by Persian or English shortcode/alias."""
    q = _clean_query(query)
    if not q:
        return list(EMOJI_CATALOG[:limit])

    exact: list[EmojiEntry] = []
    prefix_matches: list[EmojiEntry] = []
    sub_matches: list[EmojiEntry] = []

    for entry in EMOJI_CATALOG:
        c_en = entry.code_en.lower()
        c_fa = entry.code_fa.replace("\u200c", "")
        aliases_norm = tuple(a.lower().replace("\u200c", "").replace(" ", "_") for a in entry.aliases)

        if q in (c_en, c_fa) or q in aliases_norm:
            exact.append(entry)
        elif c_en.startswith(q) or c_fa.startswith(q) or any(a.startswith(q) for a in aliases_norm):
            prefix_matches.append(entry)
        elif q in c_en or q in c_fa or any(q in a for a in aliases_norm):
            sub_matches.append(entry)

    combined = exact + prefix_matches + sub_matches
    return combined[: max(1, limit)]


def expand_colon_emoji(token: str) -> str | None:
    """Expand an exact `:shortcode:` token (e.g. `:تیک:` or `:rocket:`) into its emoji symbol."""
    if not token or len(token) < 3 or not (token.startswith(":") and token.endswith(":")):
        return None
    q = _clean_query(token)
    if not q:
        return None
    for entry in EMOJI_CATALOG:
        c_en = entry.code_en.lower()
        c_fa = entry.code_fa.replace("\u200c", "")
        aliases_norm = tuple(a.lower().replace("\u200c", "").replace(" ", "_") for a in entry.aliases)
        if q in (c_en, c_fa) or q in aliases_norm:
            return entry.symbol
    return None


def search_emoji_candidates(prefix: str, limit: int = 5) -> list[Candidate]:
    """Return prediction `Candidate` objects for a `:prefix` query."""
    if not prefix.startswith(":") or len(prefix) < 2:
        return []
    entries = search_emoji(prefix, limit=limit)
    return [
        Candidate(
            text=entry.symbol,
            score=2500.0 - idx * 10.0,
            kind=CandidateKind.COMPLETION,
        )
        for idx, entry in enumerate(entries)
    ]

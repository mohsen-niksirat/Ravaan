"""Advanced Paste & offline clipboard format transformer (inspired by PowerToys Advanced Paste)."""

from __future__ import annotations

import csv
import io
import json
import re
from urllib.parse import urlparse

from ravan.core.normalizer import clean_pasted_text, fa_to_en_digits, normalize_persian
from ravan.core.thesaurus import apply_homophone_fixes, strip_harakat

PASTE_MODES: tuple[tuple[str, str, str], ...] = (
    ("clean_fa", "Clean & Standardize Persian", "پاک‌سازی و استانداردسازی فارسی"),
    ("strip_harakat", "Strip Harakat & Tatweel", "حذف اعراب و کشیده"),
    ("tsv_to_markdown", "Table (Excel/TSV/CSV) → Markdown", "تبدیل جدول (اکسل/CSV) به Markdown"),
    ("tsv_to_json", "Table (Excel/TSV/CSV) → JSON", "تبدیل جدول به JSON"),
    ("json_pretty", "Format / Pretty-Print JSON", "مرتب‌سازی و زیباسازی JSON"),
    ("json_minify", "Minify JSON", "فشرده‌سازی JSON"),
    ("url_to_markdown", "URLs → Markdown Links", "تبدیل لینک‌ها به Markdown"),
    ("extract_links", "Extract All URLs", "استخراج تمام لینک‌ها"),
    ("extract_emails", "Extract All Emails", "استخراج تمام ایمیل‌ها"),
    ("extract_numbers", "Extract All Numbers", "استخراج تمام اعداد"),
    ("bullet_list", "Convert Lines to Bullet List", "تبدیل خطوط به لیست بولت‌دار"),
    ("numbered_list", "Convert Lines to Numbered List", "تبدیل خطوط به لیست شماره‌دار"),
)

_URL_RE = re.compile(r"https?://[^\s<>\"')]+")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_NUMBER_RE = re.compile(r"[+-]?\d[\d,٫]*(?:\.\d+)?")


def _parse_tabular_rows(text: str) -> list[list[str]]:
    lines = [ln.strip("\r") for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return []
    delim = "\t" if any("\t" in ln for ln in lines) else ("," if all("," in ln for ln in lines) else None)
    if delim is None:
        return []
    reader = csv.reader(io.StringIO("\n".join(lines)), delimiter=delim)
    rows = [[cell.strip() for cell in row] for row in reader if any(cell.strip() for cell in row)]
    if len(rows) < 2 or max(len(r) for r in rows) < 2:
        return []
    col_count = max(len(r) for r in rows)
    return [r + [""] * (col_count - len(r)) for r in rows]


def tsv_to_markdown_table(text: str) -> str:
    """Convert TSV or CSV tabular clipboard text into a GitHub-Flavored Markdown table."""
    rows = _parse_tabular_rows(text)
    if not rows:
        return text
    col_count = len(rows[0])
    widths = [max(3, *(len(r[c].replace("|", "\\|")) for r in rows)) for c in range(col_count)]

    def _fmt_row(row: list[str]) -> str:
        cells = [row[c].replace("|", "\\|").ljust(widths[c]) for c in range(col_count)]
        return "| " + " | ".join(cells) + " |"

    header = _fmt_row(rows[0])
    sep = "| " + " | ".join("-" * widths[c] for c in range(col_count)) + " |"
    body = [_fmt_row(r) for r in rows[1:]]
    return "\n".join([header, sep, *body])


def tsv_to_json_array(text: str) -> str:
    """Convert TSV or CSV tabular clipboard text into a JSON array of objects."""
    rows = _parse_tabular_rows(text)
    if not rows:
        return text
    headers = [h or f"col_{idx + 1}" for idx, h in enumerate(rows[0])]
    records: list[dict[str, str | int | float]] = []
    for row in rows[1:]:
        obj: dict[str, str | int | float] = {}
        for h, val in zip(headers, row, strict=False):
            en_val = fa_to_en_digits(val)
            if en_val.isdigit():
                obj[h] = int(en_val)
            else:
                try:
                    obj[h] = float(en_val)
                except ValueError:
                    obj[h] = val
        records.append(obj)
    return json.dumps(records, ensure_ascii=False, indent=2)


def urls_to_markdown(text: str) -> str:
    """Convert raw URLs or `Title - https://...` lines into Markdown links."""
    out_lines: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            out_lines.append("")
            continue
        # Pattern: "Title - https://example.com" or "Title: https://example.com"
        m = re.match(r"^([^:]+?)\s*[-–—:|]\s*(https?://\S+)$", s)
        if m and not m.group(1).strip().startswith("http"):
            title = m.group(1).strip()
            url = m.group(2).strip()
            out_lines.append(f"[{title}]({url})")
            continue

        def _repl_url(um: re.Match[str]) -> str:
            u = um.group(0)
            parsed = urlparse(u)
            host = (parsed.netloc or u).removeprefix("www.")
            path = parsed.path.strip("/")
            label = f"{host}/{path}" if path and len(path) <= 24 else host
            return f"[{label}]({u})"

        out_lines.append(_URL_RE.sub(_repl_url, line))
    return "\n".join(out_lines)


def detect_best_paste_modes(text: str) -> list[str]:
    """Recommend the most useful paste transformation modes for `text`."""
    if not text or not text.strip():
        return ["clean_fa"]
    s = text.strip()
    modes: list[str] = []

    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
        try:
            json.loads(s)
            modes.extend(["json_pretty", "json_minify"])
        except Exception:
            pass

    if _parse_tabular_rows(s):
        modes.extend(["tsv_to_markdown", "tsv_to_json"])

    if _URL_RE.search(s):
        modes.extend(["url_to_markdown", "extract_links"])

    if _EMAIL_RE.search(s):
        modes.append("extract_emails")

    if any("\u064b" <= c <= "\u065f" or c == "\u0640" for c in s):
        modes.append("strip_harakat")

    if "clean_fa" not in modes:
        modes.insert(0, "clean_fa")
    return modes


def transform_clipboard_content(text: str, mode: str = "clean_fa") -> str:
    """Transform clipboard text according to `mode` completely offline."""
    if not text:
        return ""
    m = (mode or "clean_fa").strip().lower()

    if m == "clean_fa":
        no_html = _HTML_TAG_RE.sub(" ", text) if ("<" in text and ">" in text and "</" in text) else text
        cleaned = clean_pasted_text(no_html, digit_mode="auto")
        norm = normalize_persian(cleaned, digits="keep", fix_zwnj=True, fix_spacing=True, fix_grammar=True)
        return apply_homophone_fixes(norm)

    if m == "strip_harakat":
        return strip_harakat(text)

    if m == "tsv_to_markdown":
        return tsv_to_markdown_table(text)

    if m == "tsv_to_json":
        return tsv_to_json_array(text)

    if m in ("json_pretty", "json_minify"):
        try:
            parsed = json.loads(text.strip())
            if m == "json_pretty":
                return json.dumps(parsed, ensure_ascii=False, indent=2)
            return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            return text

    if m == "url_to_markdown":
        return urls_to_markdown(text)

    if m == "extract_links":
        links = dict.fromkeys(_URL_RE.findall(text))
        return "\n".join(links)

    if m == "extract_emails":
        emails = dict.fromkeys(_EMAIL_RE.findall(text))
        return "\n".join(emails)

    if m == "extract_numbers":
        nums = _NUMBER_RE.findall(fa_to_en_digits(text))
        return "\n".join(n.replace(",", "").replace("٫", ".") for n in nums)

    if m == "bullet_list":
        lines = [re.sub(r"^[\s•\-\*\d\.،]+", "", ln).strip() for ln in text.splitlines()]
        return "\n".join(f"• {ln}" for ln in lines if ln)

    if m == "numbered_list":
        lines = [re.sub(r"^[\s•\-\*\d\.،]+", "", ln).strip() for ln in text.splitlines()]
        clean_lines = [ln for ln in lines if ln]
        return "\n".join(f"{idx + 1}. {ln}" for idx, ln in enumerate(clean_lines))

    return text

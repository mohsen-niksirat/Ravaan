"""False-positive rate benchmark and CI quality gate.

Evaluates Ravaan autocorrect against a realistic corpus of formal Persian,
chat/colloquial Persian, mixed English/Persian, and code snippets.

Hard target: False Positive Rate (FPR) < 0.1%.
Fails CI (exit code 1) if exceeded.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ravan.core.dict import Dictionary  # noqa: E402
from ravan.core.predictor import DictPredictor, is_arabic_persian  # noqa: E402


def extract_tokens(text: str) -> list[str]:
    """Tokenize sentence into distinct typing tokens as encountered at word boundaries."""
    # Split on whitespace first
    raw_parts = text.split()
    tokens = []
    for part in raw_parts:
        part = part.strip()
        if not part:
            continue
        # Strip outer punctuation quotes / brackets
        cleaned = re.sub(r"^[«\"'(\[{<]+", "", part)
        cleaned = re.sub(r"[»\"')\]}>,;:!?،؛؟.]+$", "", cleaned)
        if cleaned:
            tokens.append(cleaned)
    return tokens


def run_benchmark(corpus_path: Path | None = None, fail_fast: bool = False) -> tuple[int, int, list[dict]]:
    if corpus_path is None:
        corpus_path = repo_root / "tests" / "data" / "false_positive_corpus.json"

    data = json.loads(corpus_path.read_text(encoding="utf-8"))
    samples = data.get("samples", [])

    en_dict = Dictionary.english()
    fa_dict = Dictionary.persian()
    predictor = DictPredictor(english=en_dict, persian=fa_dict, autocorrect_mode="safe")

    total_tokens = 0
    false_positives = 0
    details: list[dict] = []

    for sample in samples:
        category = sample.get("category", "unknown")
        text = sample.get("text", "")
        tokens = extract_tokens(text)

        for tok in tokens:
            total_tokens += 1
            is_fa = any(is_arabic_persian(c) for c in tok)
            lang = "fa" if is_fa else "en"

            cand = predictor.correct(tok, lang=lang)
            if cand is not None and cand.text != tok:
                false_positives += 1
                details.append({
                    "category": category,
                    "original": tok,
                    "corrected": cand.text,
                    "lang": lang,
                })
                if fail_fast:
                    return total_tokens, false_positives, details

    return total_tokens, false_positives, details


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("=" * 65)
    print("      Ravaan Autocorrect False-Positive Rate Benchmark      ")
    print("=" * 65)

    total_tokens, false_positives, details = run_benchmark()
    fpr = (false_positives / total_tokens * 100.0) if total_tokens > 0 else 0.0

    print(f"Total Valid Tokens Evaluated: {total_tokens:,}")
    print(f"False Positives Detected:     {false_positives}")
    print(f"False Positive Rate (FPR):    {fpr:.3f}%")
    print("Target Threshold:             < 0.100%")
    print("=" * 65)

    if details:
        print("\nFalse Positive Details:")
        for d in details:
            print(f"  [{d['category']}] '{d['original']}' -> '{d['corrected']}' (lang: {d['lang']})")

    if fpr >= 0.100 or false_positives > 0:
        if fpr >= 0.100:
            print(f"\n[FAIL] False-positive rate {fpr:.3f}% exceeds target limit (< 0.1%)!")
            return 1
        else:
            print("\n[WARN] Minor false positive detected within 0.1% tolerance.")
            return 0

    print("\n[PASS] False-positive gate passed: 0.000% error rate on test corpus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

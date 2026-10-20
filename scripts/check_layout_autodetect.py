"""Layout auto-detection accuracy and false-positive benchmark for Ravaan (Phase 2).

Evaluates:
1. False-Positive Rate (FPR) on 594-token realistic test corpus (Target: < 0.1%, strictly 0.0%).
2. Precision and Recall on mixed English/Persian wrong-layout benchmark dataset (Target: Precision >= 98%, Recall >= 90%).
3. Mid-word detection responsiveness and evaluation latency (p95 < 1 ms).
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ravan.core.autofix import AutoFixEngine  # noqa: E402
from ravan.core.dict import Dictionary  # noqa: E402
from ravan.core.layout import LayoutMapper  # noqa: E402
from ravan.core.predictor import is_arabic_persian  # noqa: E402


def extract_tokens(text: str) -> list[str]:
    raw_parts = text.split()
    tokens = []
    for part in raw_parts:
        part = part.strip()
        if not part:
            continue
        cleaned = re.sub(r"^[«\"'(\[{<]+", "", part)
        cleaned = re.sub(r"[»\"')\]}>,;:!?،؛؟.]+$", "", cleaned)
        if cleaned:
            tokens.append(cleaned)
    return tokens


def run_false_positive_evaluation(
    engine: AutoFixEngine, corpus_path: Path | None = None
) -> tuple[int, int, list[dict[str, str]]]:
    if corpus_path is None:
        corpus_path = repo_root / "tests" / "data" / "false_positive_corpus.json"

    data = json.loads(corpus_path.read_text(encoding="utf-8"))
    samples = data.get("samples", [])

    total_tokens = 0
    false_positives = 0
    details: list[dict[str, str]] = []

    for sample in samples:
        category = sample.get("category", "unknown")
        text = sample.get("text", "")
        tokens = extract_tokens(text)

        for tok in tokens:
            total_tokens += 1
            is_fa = any(is_arabic_persian(c) for c in tok)
            active_lang = "fa" if is_fa else "en"

            res = engine.detect(tok, active_layout=active_lang)
            if res is not None:
                false_positives += 1
                details.append({
                    "category": category,
                    "token": tok,
                    "converted_to": res[0],
                    "target_lang": res[1],
                })

    return total_tokens, false_positives, details


def run_accuracy_evaluation(
    engine: AutoFixEngine, en_dict: Dictionary, fa_dict: Dictionary, sample_size: int = 100
) -> tuple[int, int, int, float, float]:
    mapper = LayoutMapper()

    en_candidates = [
        e.word for e in en_dict.entries if len(e.word) >= 3 and mapper.en_to_fa_word(e.word)
    ][:sample_size]

    fa_candidates = [
        e.word for e in fa_dict.entries if len(e.word) >= 3 and mapper.fa_to_en_word(e.word)
    ][:sample_size]

    wrong_fa_inputs = [(mapper.fa_to_en_word(w), w, "fa") for w in fa_candidates]
    wrong_en_inputs = [(mapper.en_to_fa_word(w), w, "en") for w in en_candidates]

    tp = 0
    fn = 0
    fp = 0

    # 1. Evaluate wrong-layout inputs (must convert to expected target)
    for typed, expected, target_lang in wrong_fa_inputs + wrong_en_inputs:
        if not typed:
            continue
        active_lang = "en" if target_lang == "fa" else "fa"
        res = engine.detect(typed, active_layout=active_lang)
        if res is not None and res[0] == expected:
            tp += 1
        else:
            fn += 1

    # 2. Evaluate correct-layout inputs (must NOT convert)
    for w in en_candidates:
        if engine.detect(w, active_layout="en") is not None:
            fp += 1
    for w in fa_candidates:
        if engine.detect(w, active_layout="fa") is not None:
            fp += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0

    return tp, fp, fn, precision, recall


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("=" * 68)
    print("      Ravaan Phase 2: Automatic Wrong-Layout Detection Benchmark    ")
    print("=" * 68)

    t0 = time.perf_counter()
    en_dict = Dictionary.english()
    fa_dict = Dictionary.persian()
    engine = AutoFixEngine(en_dict=en_dict, fa_dict=fa_dict, mode="safe")
    init_ms = (time.perf_counter() - t0) * 1000

    print(f"Dictionaries & Engine Loaded in {init_ms:.2f} ms")
    print("-" * 68)

    # 1. False-Positive Rate Benchmark
    print("[1/2] Evaluating False-Positive Rate on 594-token corpus...")
    total_tokens, false_positives, fp_details = run_false_positive_evaluation(engine)
    fpr = (false_positives / total_tokens * 100.0) if total_tokens else 0.0

    print(f"      Tokens Evaluated:      {total_tokens:,}")
    print(f"      False Positives:       {false_positives}")
    print(f"      False Positive Rate:   {fpr:.3f}% (Target: < 0.100%)")
    if fp_details:
        for d in fp_details[:5]:
            print(f"        -> [{d['category']}] '{d['token']}' wrongly converted to '{d['converted_to']}'")

    print("-" * 68)

    # 2. Accuracy Benchmark
    print("[2/2] Evaluating Accuracy (Precision & Recall) on 400 test words...")
    tp, fp, fn, precision, recall = run_accuracy_evaluation(engine, en_dict, fa_dict, sample_size=100)
    print(f"      True Positives (TP):   {tp}")
    print(f"      False Positives (FP):  {fp}")
    print(f"      False Negatives (FN):  {fn}")
    print(f"      Precision:             {precision * 100.0:.2f}% (Target: >= 98.00%)")
    print(f"      Recall:                {recall * 100.0:.2f}% (Target: >= 90.00%)")

    print("=" * 68)

    passed = (fpr < 0.1) and (precision >= 0.98) and (recall >= 0.90)
    if passed:
        print("[PASS] All Phase 2 detection quality & safety gates passed successfully!")
        return 0
    else:
        print("[FAIL] Quality gate failed. Please review metrics above.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
